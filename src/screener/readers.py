"""The reader agents: turn a free-text proposal into facts, each backed by a quote.

Two readers share one output shape:
  * OfflineReader: keyword rules. Free, deterministic, runs in CI and on the static site.
    It is a baseline, tuned on the sample proposals, and says so.
  * ClaudeReader: Claude with a strict JSON schema. The real reader.

Whatever reads the proposal, `verify_quotes` then drops any fact whose quote is not
actually in the proposal text. A reader cannot add a fact the proposal does not contain.
"""
from __future__ import annotations

import json
import os
import re

from .law import ANNEX_III, ART6_3, FACT_KEYS, PROHIBITED

MODEL = os.getenv("SCREENER_MODEL", "claude-opus-5-5")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def verify_quotes(text: str, evidence: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep only evidence whose quote appears in the text. Returns (kept, rejected)."""
    body = _norm(text)
    kept, rejected = [], []
    for e in evidence:
        q = _norm(e.get("quote", ""))
        (kept if q and q in body else rejected).append(e)
    return kept, rejected


def facts_from_evidence(evidence: list[dict]) -> dict:
    """Build the facts dict only from verified evidence."""
    facts: dict = {}
    for e in evidence:
        key, value = e.get("fact"), e.get("value")
        if key not in FACT_KEYS:
            continue
        if FACT_KEYS[key] is list:
            vals = value if isinstance(value, list) else [value]
            facts.setdefault(key, [])
            facts[key] += [v for v in vals if v not in facts[key]]
        else:
            facts[key] = bool(value)
    return facts


# --------------------------------------------------------------------------------------- #
# Offline reader: keyword rules
# --------------------------------------------------------------------------------------- #
# (fact, value, pattern): a pattern matches inside one sentence; its sentence is the quote.
RULES: list[tuple[str, object, str]] = [
    ("prohibited", "emotion_recognition_work_education",
     r"(emotion|stress|mood|frustrat|sentiment|fatigue).{0,80}(employee|staff|worker|cashier|agent|student|pupil|class)|"
     r"(employee|staff|worker|cashier|agent|student|pupil|class).{0,80}(emotion|stress|mood|frustrat|sentiment)"),
    ("prohibited", "social_scoring", r"(trust|citizen|social|reliability)\w* score|score (residents|citizens)|rate (residents|citizens)"),
    ("prohibited", "facial_scraping", r"scrap\w+.{0,80}(face|photo|image)|(face|photo|image)\w*.{0,80}scrap"),
    ("prohibited", "crime_prediction_profiling", r"predict\w*.{0,60}(crime|offen|reoffend)"),
    ("prohibited", "exploits_vulnerabilities", r"(child|kids|elderly|minors)\w*.{0,120}(persua|pressure|nudge|urg|purchase)|(persua|nudge|pressure).{0,120}(child|kids|minors)"),
    ("prohibited", "biometric_categorisation_sensitive", r"(infer|deduce|detect)\w*.{0,60}(ethnic|race|religio|political|sexual orientation|union)"),
    ("prohibited", "realtime_rbi_law_enforcement", r"real.time.{0,60}(facial recognition|biometric).{0,80}(police|law enforcement)"),
    ("annex_iii", "4a", r"\b(cvs?|résumé|resume|candidates?|recruit\w*|hiring|shortlist\w*|job applicants?)\b"),
    ("annex_iii", "4b", r"(allocat\w+ (tasks|shifts)|task allocation|performance (monitor|scor|rank)|productivity (track|scor|monitor)|promotion|dismiss)"),
    ("annex_iii", "5b", r"(credit\s?worth|credit scor|loan|lending|credit limit)"),
    ("fraud_detection_only", True, r"(fraud|suspicious transaction)"),
    ("annex_iii", "5c", r"(life|health) insurance.{0,80}(pric|premium|underwrit|risk)|(pric|premium|underwrit).{0,80}(life|health) insurance"),
    ("annex_iii", "5d", r"emergency (call|service)|112 call|triage"),
    ("annex_iii", "5a", r"(benefit|subsid|social assistance).{0,80}(eligib|entitle)"),
    ("annex_iii", "3a", r"admission|applicants? to (the )?(university|school|programme)"),
    ("annex_iii", "3b", r"grad(e|ing) (essays|exams|assignments)|evaluat\w+ learning"),
    ("annex_iii", "3d", r"proctor|cheating|exam (monitor|surveil)"),
    ("annex_iii", "2", r"(water|gas|electric|heating|traffic)\w*.{0,100}(valve|pressure|shut.?off|safety)|"
                       r"(valve|pressure|shut.?off)\w*.{0,100}(water|gas|electric|heating) (network|grid|supply)|safety (valve|shut)"),
    ("annex_iii", "1a", r"(facial recognition|face recognition).{0,80}(identif|crowd|public)"),
    ("annex_iii", "1c", r"(emotion|stress|mood|sentiment).{0,60}(voice|face|facial|camera|webcam)|(voice|face|facial|camera|webcam).{0,60}(emotion|stress|mood)"),
    ("annex_iii", "7", r"(asylum|visa|border control|migrant)"),
    ("annex_iii", "8a", r"(judge|court|sentenc)"),
    ("annex_iii", "8b", r"(voter|election|electoral)"),
    ("annex_i_safety_component", True, r"(medical device|braking|machinery|lift safety|toy safety|insulin pump)"),
    ("interacts_with_people", True, r"(chatbot|virtual assistant|voice assistant|talks? (to|with) (customers|users|children)|conversational)"),
    ("generates_synthetic_content", True, r"generat\w+ (images|videos|audio|text|copy|visuals|ad creatives)"),
    ("deepfake", True, r"(deepfake|deep fake|synthetic video of|digital twin of (our|the) (ceo|presenter))"),
    ("emotion_or_biometric_categorisation", True, r"(emotion|mood|stress).{0,60}(voice|face|camera|webcam)"),
    ("profiling", True, r"(profil|score each|scores each|rank\w* (candidates|workers|employees|applicants|residents)|personal characteristics|behaviour data|behavior data)"),
    ("uses_personal_data", True, r"(customer|employee|patient|applicant|citizen|resident|student|personal) (data|records|history|photos)|(cv|cvs|transaction history|call recordings|exam footage)"),
    ("uses_special_category_data", True, r"(health|medical|biometric|face|facial|religio|ethnic)"),
    ("automated_decision", True, r"automatic\w* (approve|reject|decline|decide|allocat|flag)|without (a )?human (review|check)|no human"),
    ("role", "provider", r"(we will build|we are building|in-house|our own model|we develop|developed by us|we will train)"),
    ("role", "deployer", r"(off-the-shelf|vendor|licen[cs]e[sd]? (a|the)|buy (a|the)|third-party tool|we will use|we use|deploy|in-house)"),
    ("art6_3_claim", "preparatory", r"(only prepares|just prepares|preparatory|recommendation only|final decision (stays|remains) with)"),
]


class OfflineReader:
    name = "offline keyword reader"

    def read(self, text: str) -> dict:
        evidence = []
        for sent in sentences(text):
            low = sent.lower()
            for fact, value, pattern in RULES:
                if re.search(pattern, low):
                    evidence.append({"fact": fact, "value": value, "quote": sent})
        # Fraud only counts as a carve-out when the proposal is about fraud and not lending.
        if any(e["fact"] == "fraud_detection_only" for e in evidence) and \
                any(e["value"] == "5b" for e in evidence if e["fact"] == "annex_iii"):
            lending = [s for s in sentences(text) if re.search(r"(approve|decid|grant|limit)\w*.{0,40}(loan|credit)", s.lower())]
            if lending:
                evidence = [e for e in evidence if e["fact"] != "fraud_detection_only"]
        return {"evidence": evidence, "unknowns": [], "reader": self.name}


# --------------------------------------------------------------------------------------- #
# Claude reader: strict JSON schema, quotes required
# --------------------------------------------------------------------------------------- #
FACT_GUIDE = (
    "Facts you may assert (fact -> value):\n"
    f"- prohibited -> one of {sorted(PROHIBITED)}\n"
    f"- annex_iii -> one of {sorted(ANNEX_III)}  ({'; '.join(f'{k}: {v}' for k, v in ANNEX_III.items())})\n"
    "- role -> provider (they build it) or deployer (they use someone else's)\n"
    f"- art6_3_claim -> one of {sorted(ART6_3)} (only if the proposal itself claims it)\n"
    "- annex_i_safety_component, fraud_detection_only, profiling, affects_natural_persons, interacts_with_people, "
    "generates_synthetic_content, deepfake, emotion_or_biometric_categorisation, uses_personal_data, "
    "uses_special_category_data, automated_decision -> true\n"
)

SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {"type": "array", "items": {
            "type": "object",
            "properties": {"fact": {"type": "string"}, "value": {"type": "string"},
                           "quote": {"type": "string"}},
            "required": ["fact", "value", "quote"], "additionalProperties": False}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["evidence", "unknowns"], "additionalProperties": False,
}

READ_PROMPT = (
    "You read proposals for AI use cases and extract facts that matter under the EU AI Act. "
    "Assert a fact only if a sentence of the proposal supports it, and copy that sentence "
    "(or a contiguous part of it) exactly into `quote`. Do not paraphrase quotes. Do not decide "
    "the risk tier: other code does that. List in `unknowns` the facts that matter but the "
    "proposal does not settle (for example who builds the system, or whether a human reviews "
    "each decision). For boolean facts use the value \"true\".\n\n" + FACT_GUIDE
)

CHALLENGE_PROMPT = (
    "You are a sceptical second reviewer of an AI Act screening. Another reader extracted the "
    "facts below from the proposal. Find facts it MISSED that would change the classification "
    "(a prohibited practice, an Annex III area, an Annex I safety component, a transparency "
    "trigger, profiling). Only add a fact if you can quote the proposal exactly. If nothing "
    "was missed, return an empty evidence list.\n\n" + FACT_GUIDE
)


def _bool_or_str(value: str):
    return True if str(value).lower() == "true" else value


class ClaudeReader:
    """Claude via the Anthropic SDK. Needs ANTHROPIC_API_KEY (or an `ant auth login` profile)."""

    def __init__(self, model: str = MODEL):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.name = f"Claude ({model})"

    def _ask(self, system: str, user: str, effort: str = "low") -> dict:
        resp = self.client.beta.messages.create(
            model=self.model, max_tokens=8000, system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            return {"evidence": [], "unknowns": ["The model declined to read this proposal; review by hand."]}
        text = next(b.text for b in resp.content if b.type == "text")
        out = json.loads(text)
        for e in out["evidence"]:
            e["value"] = _bool_or_str(e["value"])
        return out

    def read(self, text: str) -> dict:
        out = self._ask(READ_PROMPT, f"PROPOSAL:\n{text}")
        out["reader"] = self.name
        return out

    def challenge(self, text: str, evidence: list[dict]) -> dict:
        found = json.dumps([{k: e[k] for k in ("fact", "value")} for e in evidence])
        return self._ask(CHALLENGE_PROMPT, f"PROPOSAL:\n{text}\n\nFACTS ALREADY FOUND:\n{found}", effort="medium")


def make_reader(prefer_model: bool = True):
    """Claude when credentials are available, else the offline reader."""
    if prefer_model and (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        try:
            return ClaudeReader()
        except Exception:  # noqa: BLE001 - a missing SDK must not stop a screening
            pass
    return OfflineReader()
