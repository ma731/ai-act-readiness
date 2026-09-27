"""Render the generated parts of the assessment.

The narrative documents are written by hand. Every table and number in them comes from
here, between <!-- BEGIN:name --> and <!-- END:name --> markers, so the prose cannot drift
from the results. `--check` fails if a document is stale.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from src.pricing import CONDITIONS
from src.rules import LEGAL_BASIS_DATE, Classification

TIER_LABEL = {"prohibited": "Prohibited", "high_risk": "High-risk",
              "transparency": "Transparency", "minimal": "Minimal"}
STATUS_MARK = {"met": "Met", "partial": "Partial", "missing": "Missing"}


def _months(d: date) -> int:
    return (d.year - LEGAL_BASIS_DATE.year) * 12 + d.month - LEGAL_BASIS_DATE.month


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def gap_rows(systems: list[dict], results: list[Classification]) -> list[dict]:
    rows = []
    for s, c in zip(systems, results, strict=True):
        controls = s.get("controls") or {}
        for o in c.obligations:
            ctl = controls.get(o.article, {})
            status = ctl.get("status", "not assessed")
            if s.get("status") == "proposed":
                state = "Block before purchase" if o.article.startswith("Art 5(") \
                    else "Pre-deployment"
            elif status == "met":
                state = "Done"
            elif o.in_force and status == "partial":
                state = "In force, partial"
            elif o.in_force:
                state = "OVERDUE"
            else:
                state = f"Due {o.applies_from:%d %b %Y} ({_months(o.applies_from)} mo)"
            rows.append({"system": s["id"], "name": s["name"],
                         "live": s.get("status") != "proposed", "article": o.article,
                         "duty": o.duty, "holder": o.holder, "status": status,
                         "note": ctl.get("note", ""), "state": state,
                         "applies_from": o.applies_from})
    return rows


def _priority(r: dict) -> tuple:
    order = {"Block before purchase": 0, "OVERDUE": 1, "In force, partial": 2}
    return (order.get(r["state"], 3), r["applies_from"], r["system"])


def inventory_table(systems, results) -> str:
    out = ["| ID | System | Role | Classification | Why | FRIA |",
           "|---|---|---|---|---|---|"]
    for s, c in zip(systems, results, strict=True):
        why = " ".join(c.basis) or "Not listed in Annex III; no Art 5 or Art 50 trigger."
        proposed = " (proposed)" if s.get("status") == "proposed" else ""
        out.append(f"| {s['id']} | {s['name']}{proposed}"
                   f" | {', '.join(s.get('role', []))} | **{TIER_LABEL[c.tier]}** | {why} | "
                   f"{'Required' if c.fria_required else 'No'} |")
    return "\n".join(out)


def flags_list(systems, results) -> str:
    out = []
    for s, c in zip(systems, results, strict=True):
        for f in c.flags:
            out.append(f"- **{s['id']} {s['name']}:** {f}")
        for f in c.other_law:
            out.append(f"- **{s['id']} {s['name']}** (outside the AI Act): {f}")
    return "\n".join(out)


def gap_summary(rows) -> str:
    live = [r for r in rows if r["live"]]
    count = {k: sum(1 for r in live if r["status"] == k)
             for k in ["met", "partial", "missing", "not assessed"]}
    overdue = sum(1 for r in rows if r["state"] == "OVERDUE")
    blocked = sum(1 for r in rows if r["state"] == "Block before purchase")
    return (f"{len(live)} obligations on live systems: {count['met']} met, "
            f"{count['partial']} partial, {count['missing']} missing"
            + (f", {count['not assessed']} not assessed" if count["not assessed"] else "")
            + f". **{overdue} overdue today**, {blocked} prohibited use to block before "
              "purchase.")


def gap_table(rows) -> str:
    out = ["| Priority | System | Article | Duty | Holder | Current state | Status |",
           "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sorted(rows, key=_priority), 1):
        state = f"**{r['state']}**" if r["state"] in {"OVERDUE", "Block before purchase"} \
            else r["state"]
        out.append(f"| {i} | {r['system']} | {r['article']} | {r['duty']} | {r['holder']} | "
                   f"{STATUS_MARK.get(r['status'], r['status'])}"
                   f"{': ' + r['note'] if r['note'] else ''} | {state} |")
    return "\n".join(out)


def evidence_groups(ev: dict, by: str) -> str:
    out = ["| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | "
           "Verdict | Declined | Referred |", "|---|---|---|---|---|---|---|---|"]
    for g in ev["groups"][by]:
        lo, hi = g["price_to_cost_ci"]
        dlo, dhi = g["decline_rate_ci"]
        out.append(f"| {g['group']} | {g['n']:,} | {g['premium_index']:.2f} | "
                   f"{g['cost_index']:.2f} | **{g['price_to_cost']:.2f}** ({lo:.2f} to "
                   f"{hi:.2f}) | {g['verdict']} | {_pct(g['decline_rate'])} "
                   f"({_pct(dlo)} to {_pct(dhi)}) | {_pct(g['refer_rate'])} |")
    return "\n".join(out)


def evidence_headline(ev: dict) -> str:
    eth = {g["group"]: g for g in ev["groups"]["ethnicity"]}
    worst = max(eth.values(), key=lambda g: g["price_to_cost"])
    most_declined = max(eth.values(), key=lambda g: g["decline_rate"])
    ref = eth["White"]
    lo, hi = worst["price_to_cost_ci"]
    sx = ev["sex_counterfactual"]
    rel = ev["model"]["relativities"]
    return "\n".join([
        f"- **{worst['group']} applicants pay {worst['price_to_cost']:.2f}x their share of "
        f"claims** (95% CI {lo:.2f} to {hi:.2f}), {worst['population_share'] * 100:.0f}% of "
        "the book. Ethnicity is never an input.",
        f"- **Applicants in the '{most_declined['group']}' ethnic group are declined "
        f"{most_declined['decline_rate'] / ref['decline_rate']:.1f}x as often** as White "
        f"applicants ({_pct(most_declined['decline_rate'])} against "
        f"{_pct(ref['decline_rate'])}).",
        f"- **Smokers are priced {100 * (1 - rel['smoker_yes']):.0f}% below non-smokers**, "
        "because the target is one year of spending.",
        f"- **The unisex rule holds.** Women pay {sx['female_to_male_premium_unisex']:.2f}x "
        f"what men pay against {sx['female_to_male_actual_cost']:.2f}x the cost; the other "
        f"answers barely reveal sex (AUC {sx['sex_recoverable_from_rating_factors_auc']:.2f}).",
    ])


def evidence_model(ev: dict) -> str:
    m, d, sx = ev["model"], ev["data"], ev["sex_counterfactual"]
    rel = m["relativities"]
    cond = sorted(((k, rel[k]) for k in CONDITIONS.values()), key=lambda kv: -kv[1])
    lines = [
        f"- Data: {d['source']}; {d['cohort']}; **{d['people']:,} people** weighted to "
        f"{d['represents_millions']:.1f} million.",
        f"- Model: {m['primary']}; {m['validation']}.",
        f"- Ranking power: Gini **{m['gini_glm']:.3f}** for the GLM against "
        f"{m['gini_gbm_challenger']:.3f} for a gradient-boosted challenger, so the "
        "explainable model is also the better one.",
        f"- Book level: predicted over actual cost {m['book_price_to_cost']:.3f}.",
        f"- Smokers: relativity **{rel['smoker_yes']:.2f}** against non-smokers.",
        f"- Self-rated health: excellent {rel['self_rated_health_excellent']:.2f}, "
        f"poor {rel['self_rated_health_poor']:.2f} (base: good).",
        "- Conditions: " + ", ".join(f"{k.replace('_', ' ')} {v:.2f}" for k, v in cond) + ".",
        f"- Sex is not an input. Women pay **{sx['female_to_male_premium_unisex']:.2f}x** "
        f"what men pay and cost {sx['female_to_male_actual_cost']:.2f}x as much. With sex "
        f"as a factor the ratio would be {sx['female_to_male_premium_if_sex_were_used']:.2f}x. "
        f"Sex is only weakly recoverable from the other answers (AUC "
        f"{sx['sex_recoverable_from_rating_factors_auc']:.2f}).",
    ]
    return "\n".join(lines)


def roadmap(rows) -> str:
    phases = [
        ("Now: prohibited or overdue",
         lambda r: r["state"] in {"Block before purchase", "OVERDUE"}),
        ("Now: in force, partly done", lambda r: r["state"] == "In force, partial"),
        ("By 2 Dec 2026", lambda r: r["state"].startswith("Due")
         and r["applies_from"] <= date(2026, 12, 2)),
        ("By 2 Dec 2027, when high-risk duties apply", lambda r: r["state"].startswith("Due")
         and r["applies_from"] > date(2026, 12, 2)),
    ]
    out = []
    for title, pick in phases:
        per_system: dict[str, list[str]] = {}
        for r in sorted((r for r in rows if pick(r)), key=_priority):
            arts = per_system.setdefault(f"{r['system']} {r['name']}", [])
            if r["article"] not in arts:
                arts.append(r["article"])
        if per_system:
            out.append(f"**{title}**\n")
            out += [f"- {k}: {', '.join(v)}" for k, v in per_system.items()]
            out.append("")
    return "\n".join(out).rstrip()


def fill(text: str, blocks: dict[str, str]) -> str:
    for name, body in blocks.items():
        pat = re.compile(rf"(<!-- BEGIN:{name} -->)\n.*?(<!-- END:{name} -->)", re.S)
        text = pat.sub(lambda m, b=body: f"{m.group(1)}\n{b}\n{m.group(2)}", text)
    return text


def render_docs(docs_dir: Path, blocks: dict[str, str], check: bool = False) -> list[Path]:
    stale = []
    for p in sorted(docs_dir.glob("*.md")) + [docs_dir.parent / "README.md"]:
        if not p.exists():
            continue
        old = p.read_text(encoding="utf-8")
        new = fill(old, blocks)
        if new != old:
            stale.append(p)
            if not check:
                p.write_text(new, encoding="utf-8")
    return stale
