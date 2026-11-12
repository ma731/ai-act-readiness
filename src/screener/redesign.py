"""What would make it allowed: the smallest design change that drops an idea a tier.

Each lever is a real design choice a team can make, tied to the article that makes it work.
We apply one lever at a time (then pairs, for the prohibited cases that land on high-risk),
re-run the same classify() and keep only changes that lower the tier. The law is never
loosened here: a lever only removes a fact the team can design out, or adds one the law
itself recognises (the Art 6(3) preparatory-task route).
"""
from __future__ import annotations

from itertools import combinations

from src.rules import TIER_ORDER

from .law import classify

# id, change in plain words, why it works, how to apply it to the facts
LEVERS = [
    ("text_not_biometrics",
     "Read sentiment from text, such as transcripts or emails, not from voices or faces.",
     "Emotion recognition in the AI Act means inferring emotions from biometric data (Art 3(39)), so text "
     "sentiment leaves Art 5(1)(f) and Annex III 1(c).",
     {"drop_prohibited": ["emotion_recognition_work_education"], "drop_annex": ["1c"],
      "unset": ["emotion_or_biometric_categorisation"]}),
    ("cases_not_people",
     "Score transactions, cases or places, not people's trustworthiness or personality.",
     "Social scoring (Art 5(1)(c)) and person-based crime prediction (Art 5(1)(d)) are about rating people.",
     {"drop_prohibited": ["social_scoring", "crime_prediction_profiling"], "unset": ["profiling"]}),
    ("licensed_images",
     "Build the face set from consented, licensed images instead of scraping the web or CCTV.",
     "Art 5(1)(e) bans untargeted scraping, not facial recognition as such.",
     {"drop_prohibited": ["facial_scraping"]}),
    ("no_sensitive_traits",
     "Do not infer sensitive traits such as ethnicity, religion or political views.",
     "Art 5(1)(g) bans biometric categorisation into those groups.",
     {"drop_prohibited": ["biometric_categorisation_sensitive"]}),
    ("no_pressure",
     "Remove persuasion aimed at children or other vulnerable groups.",
     "Art 5(1)(b) bans exploiting age or vulnerability to distort behaviour.",
     {"drop_prohibited": ["exploits_vulnerabilities"]}),
    ("person_decides",
     "Let the tool prepare the case and have a person make the final decision.",
     "A preparatory task is not high-risk under Art 6(3)(d), as long as it does not profile people. "
     "It must still be documented and registered (Art 6(4), 49(2)).",
     {"add_claim": "preparatory", "unset": ["automated_decision"]}),
    ("no_profiling",
     "Assess cases or documents, not individual people's characteristics.",
     "Profiling people blocks the Art 6(3) exception; without it the exception can apply.",
     {"unset": ["profiling"]}),
]


def _apply(facts: dict, how: dict) -> dict:
    f = {k: (list(v) if isinstance(v, list) else v) for k, v in facts.items()}
    for p in how.get("drop_prohibited", []):
        if p in (f.get("prohibited") or []):
            f["prohibited"].remove(p)
    for a in how.get("drop_annex", []):
        if a in (f.get("annex_iii") or []):
            f["annex_iii"].remove(a)
    for k in how.get("unset", []):
        f.pop(k, None)
    if how.get("add_claim"):
        f["art6_3_claim"] = sorted({*(f.get("art6_3_claim") or []), how["add_claim"]})
    return f


def _relevant(facts: dict, how: dict) -> bool:
    if any(p in (facts.get("prohibited") or []) for p in how.get("drop_prohibited", [])):
        return True
    if how.get("add_claim"):
        return bool(facts.get("annex_iii")) and how["add_claim"] not in (facts.get("art6_3_claim") or [])
    if "drop_prohibited" not in how and how.get("unset") == ["profiling"]:
        return bool(facts.get("profiling") and facts.get("annex_iii"))
    return False


def options(facts: dict, limit: int = 3) -> list[dict]:
    """Design changes that lower the tier, best first. Empty when nothing a team controls helps."""
    base = classify(facts).tier
    if base == "minimal":
        return []
    levers = [lv for lv in LEVERS if _relevant(facts, lv[3])]
    found = []
    for n in (1, 2):
        for combo in combinations(levers, n):
            f = facts
            for lv in combo:
                f = _apply(f, lv[3])
            a = classify(f)
            if TIER_ORDER.index(a.tier) <= TIER_ORDER.index(base):
                continue
            ids = {lv[0] for lv in combo}
            found.append({"id": "+".join(sorted(ids)), "levers": sorted(ids), "to": a.tier,
                          "change": " ".join(lv[1] for lv in combo), "why": " ".join(lv[2] for lv in combo),
                          "articles": a.articles})
        if found:
            break
    found.sort(key=lambda x: (-TIER_ORDER.index(x["to"]), len(x["levers"])))
    return found[:limit]
