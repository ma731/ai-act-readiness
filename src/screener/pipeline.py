"""The screening workflow for a batch of proposals.

For each proposal:
  1. READ       a reader agent extracts facts, each with a quote from the proposal
  2. VERIFY     code drops any fact whose quote is not in the proposal
  3. CLASSIFY   code applies the AI Act (law.classify): tier, articles, obligations
  4. CHALLENGE  a second reader looks for missed facts; code re-classifies if any are found
  5. EXPLAIN    a memo is written; code checks it cites only articles the classification used
  6. ESCALATE   code routes uncertain or disputed cases to a human-review queue

Deliberately a workflow, not an autonomous agent: a legal classification must be
predictable and repeatable, so the model reads and explains, and code decides.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .law import VERDICT, Assessment, classify
from .readers import OfflineReader, facts_from_evidence, verify_quotes


@dataclass
class Screening:
    id: str
    company: str
    title: str
    proposal: str
    reader: str
    facts: dict
    evidence: list[dict]
    assessment: Assessment
    memo: str
    review_reasons: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    challenge_changed_tier: bool = False

    @property
    def needs_review(self) -> bool:
        return bool(self.review_reasons)


ARTICLE_RE = re.compile(r"(Art(?:icle)?\.? ?\d+(?:\(\d+\))?(?:\([a-z]\))?|Annex (?:I{1,3}|III) ?\d?[a-d]?)")


def template_memo(title: str, a: Assessment) -> str:
    lines = [f"{a.verdict}. {title} is classified as {a.tier.replace('_', '-')}."]
    lines += a.basis[:3]
    duties = [o for o in a.obligations if o.article != "Art 4"]
    if duties:
        lines.append(f"{len(duties)} obligations, starting with: "
                     + "; ".join(f"{o.duty} ({o.article})" for o in duties[:3]) + ".")
    if a.next_deadline:
        lines.append(f"Next deadline: {a.next_deadline:%d %b %Y}.")
    return " ".join(lines)


def check_memo(memo: str, a: Assessment) -> list[str]:
    """The memo may only cite articles the classification used, and must state the verdict."""
    allowed = {x.lower().replace("article", "art").replace(".", "") for x in a.articles + [o.article for o in a.obligations]}
    allowed_nums = {re.sub(r"\D.*$", "", x.split()[-1]) for x in allowed if x.startswith("art")}
    problems = []
    for m in ARTICLE_RE.findall(memo or ""):
        norm = m.lower().replace("article", "art").replace(".", "").strip()
        num = re.sub(r"\D.*$", "", norm.split()[-1]) if norm.startswith("art") else None
        if norm not in allowed and (num is None or num not in allowed_nums):
            problems.append(f"cites {m}, which the classification did not use")
    if a.verdict.lower() not in (memo or "").lower():
        problems.append("does not state the verdict")
    return problems


def screen_one(row: dict, reader=None) -> Screening:
    reader = reader or OfflineReader()
    text = row["proposal"]
    trace = []

    # 1-2. read and verify
    out = reader.read(text)
    kept, rejected = verify_quotes(text, out.get("evidence", []))
    trace.append(f"read by {getattr(reader, 'name', 'reader')}: {len(kept)} facts with verified quotes"
                 + (f", {len(rejected)} dropped (quote not in the proposal)" if rejected else ""))
    review = []
    if rejected:
        review.append(f"{len(rejected)} extracted fact(s) had quotes not found in the proposal")

    # 3. classify
    facts = facts_from_evidence(kept)
    a = classify(facts)
    trace.append(f"classified: {a.tier} ({', '.join(a.articles) or 'no articles'})")

    # 4. challenge (Claude reader only; the offline reader has no second opinion)
    changed = False
    if hasattr(reader, "challenge"):
        extra = reader.challenge(text, kept)
        add, bad = verify_quotes(text, extra.get("evidence", []))
        new = [e for e in add if (e["fact"], str(e["value"])) not in {(k["fact"], str(k["value"])) for k in kept}]
        if new:
            kept += new
            facts = facts_from_evidence(kept)
            a2 = classify(facts)
            changed = a2.tier != a.tier
            trace.append(f"challenger added {len(new)} fact(s): {a.tier} -> {a2.tier}")
            if changed:
                review.append(f"the second reader changed the tier from {a.tier} to {a2.tier}")
            a = a2
        else:
            trace.append("challenger found nothing missed")
        out.setdefault("unknowns", []).extend(extra.get("unknowns", []))

    # 5. explain, then check the explanation
    memo = template_memo(row.get("title") or row["id"], a)
    if hasattr(reader, "client"):
        drafted = _claude_memo(reader, row, a)
        problems = check_memo(drafted, a)
        if problems:
            trace.append("memo check failed (" + "; ".join(problems) + "): used the template memo")
        else:
            memo = drafted
            trace.append("memo written by the model and checked")
    else:
        trace.append("memo from the template")

    # 6. escalate
    if out.get("unknowns"):
        review.append("open questions: " + "; ".join(dict.fromkeys(out["unknowns"])))
    if any("Art 6(3)" in b for b in a.basis):
        review.append("relies on or rejects an Art 6(3) derogation claim")
    if "Art 5(1)(b)" in a.articles or "Art 5(1)(a)" in a.articles:
        review.append("Art 5(1)(a)/(b) needs a 'significant harm' judgement a person should confirm")
    if facts.get("annex_i_safety_component"):
        review.append("Annex I route: check the product law and its conformity procedure")
    if not facts.get("role") and a.tier in ("high_risk", "transparency"):
        review.append("who builds and who uses the system is not stated, and it decides whose duties apply")

    return Screening(id=row["id"], company=row.get("company", ""), title=row.get("title", ""), proposal=text,
                     reader=out.get("reader", ""), facts=facts, evidence=kept, assessment=a, memo=memo,
                     review_reasons=review, trace=trace, challenge_changed_tier=changed)


def _claude_memo(reader, row: dict, a: Assessment) -> str:
    system = ("Write a plain-English screening memo (80-120 words) for a business reader. Start with the verdict "
              f"exactly as given. Cite ONLY these articles: {', '.join(a.articles + sorted({o.article for o in a.obligations}))}. "
              "No legal advice disclaimers, no headings.")
    user = (f"Proposal: {row['proposal']}\nVerdict: {a.verdict}\nTier: {a.tier}\nBasis: {' '.join(a.basis)}\n"
            f"Obligations: {'; '.join(f'{o.article}: {o.duty}' for o in a.obligations)}")
    resp = reader.client.beta.messages.create(
        model=reader.model, max_tokens=4000, system=system, messages=[{"role": "user", "content": user}],
        output_config={"effort": "low"}, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    if resp.stop_reason == "refusal":
        return ""
    return next((b.text for b in resp.content if b.type == "text"), "")


def screen_all(rows: list[dict], reader=None) -> list[Screening]:
    return [screen_one(r, reader) for r in rows]


def to_dict(s: Screening) -> dict:
    a = s.assessment
    return {"id": s.id, "company": s.company, "title": s.title, "tier": a.tier, "verdict": a.verdict,
            "articles": a.articles, "basis": a.basis, "flags": a.flags, "other_law": a.other_law,
            "obligations": [asdict(o) | {"applies_from": o.applies_from.isoformat(), "in_force": o.in_force}
                            for o in a.obligations],
            "next_deadline": a.next_deadline.isoformat() if a.next_deadline else None,
            "memo": s.memo, "needs_review": s.needs_review, "review_reasons": s.review_reasons,
            "reader": s.reader, "facts": s.facts, "evidence": s.evidence, "trace": s.trace,
            "challenge_changed_tier": s.challenge_changed_tier}


__all__ = ["screen_one", "screen_all", "to_dict", "check_memo", "template_memo", "VERDICT"]
