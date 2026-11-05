"""Classify a proposed AI use case under the EU AI Act, from facts, for any sector.

src/rules.py goes deep on one insurer's inventory. This module goes wide: every Art 5
prohibited practice, every Annex III area, the Annex I product route, Art 50 transparency,
the Art 6(3) derogation and the GDPR links a review should not miss. It reuses the
obligation lists and application dates in src/rules.py, so both agree.

The conclusion is computed here, in code, from facts. The agents only read proposals and
explain results; they never decide the tier. Decision support, not legal advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.rules import APPLIES, LEGAL_BASIS_DATE, TIER_ORDER, Obligation, _high_risk_duties

# Art 5(1): practices banned since 2 Feb 2025.
PROHIBITED = {
    "subliminal_manipulation": ("Art 5(1)(a)", "Subliminal, manipulative or deceptive techniques that distort behaviour and cause significant harm"),
    "exploits_vulnerabilities": ("Art 5(1)(b)", "Exploits vulnerabilities due to age, disability or social or economic situation, causing significant harm"),
    "social_scoring": ("Art 5(1)(c)", "Social scoring that leads to detrimental or unjustified treatment"),
    "crime_prediction_profiling": ("Art 5(1)(d)", "Predicts the risk of a person committing a crime based solely on profiling or personality traits"),
    "facial_scraping": ("Art 5(1)(e)", "Builds facial recognition databases by untargeted scraping of images from the internet or CCTV"),
    "emotion_recognition_work_education": ("Art 5(1)(f)", "Infers emotions of people at work or in education (except for medical or safety reasons)"),
    "biometric_categorisation_sensitive": ("Art 5(1)(g)", "Biometric categorisation that infers race, political opinions, union membership, religion or sexual orientation"),
    "realtime_rbi_law_enforcement": ("Art 5(1)(h)", "Real-time remote biometric identification in public spaces for law enforcement (narrow exceptions)"),
}

# Annex III: high-risk areas (stand-alone systems).
ANNEX_III = {
    "1a": "Remote biometric identification (not 1:1 verification)",
    "1b": "Biometric categorisation by sensitive or protected attributes",
    "1c": "Emotion recognition",
    "2": "Safety component in critical infrastructure (digital, road traffic, water, gas, heating, electricity)",
    "3a": "Education: access or admission",
    "3b": "Education: evaluating learning outcomes",
    "3c": "Education: assessing the level of education a person will receive",
    "3d": "Education: monitoring prohibited behaviour during tests",
    "4a": "Employment: recruitment and selection (job ads targeting, screening, evaluating candidates)",
    "4b": "Employment: decisions on terms, promotion, termination, task allocation from behaviour or traits, or performance monitoring",
    "5a": "Public assistance benefits and services: eligibility (by public authorities)",
    "5b": "Creditworthiness or credit score of natural persons (except fraud detection)",
    "5c": "Risk assessment and pricing in life and health insurance",
    "5d": "Emergency calls: evaluation, dispatch and triage",
    "6": "Law enforcement uses (evidence reliability, risk of offending, profiling in investigations)",
    "7": "Migration, asylum and border control",
    "8a": "Administration of justice: assisting judicial authorities",
    "8b": "Democratic processes: influencing elections or voting behaviour",
}

ART6_3 = {
    "narrow_procedural": "Art 6(3)(a) narrow procedural task",
    "improves_human_result": "Art 6(3)(b) improves the result of a completed human activity",
    "detects_patterns": "Art 6(3)(c) detects patterns without replacing human assessment",
    "preparatory": "Art 6(3)(d) preparatory task",
}

# Annex I (products) keeps the original 2 Aug 2027 date here; the Digital Omnibus may move it.
ANNEX_I_DATE = date(2027, 8, 2)

VERDICT = {
    "prohibited": "Do not proceed",
    "high_risk": "Proceed only with high-risk controls",
    "transparency": "Proceed, with transparency duties",
    "minimal": "Proceed",
}

# Every boolean / list fact the readers may set. Anything else is ignored.
FACT_KEYS = {
    "role": list, "prohibited": list, "annex_iii": list, "annex_i_safety_component": bool,
    "fraud_detection_only": bool, "art6_3_claim": list, "profiling": bool,
    "affects_natural_persons": bool, "interacts_with_people": bool,
    "generates_synthetic_content": bool, "deepfake": bool,
    "emotion_or_biometric_categorisation": bool, "uses_personal_data": bool,
    "uses_special_category_data": bool, "automated_decision": bool,
}


@dataclass
class Assessment:
    tier: str
    verdict: str
    basis: list[str] = field(default_factory=list)
    articles: list[str] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    other_law: list[str] = field(default_factory=list)

    @property
    def next_deadline(self) -> date | None:
        future = [o.applies_from for o in self.obligations if o.applies_from > LEGAL_BASIS_DATE]
        return min(future) if future else None

    @property
    def overdue(self) -> list[Obligation]:
        return [o for o in self.obligations if o.in_force and o.article != "Art 4"]


def _art(a: Assessment, article: str) -> None:
    if article not in a.articles:
        a.articles.append(article)


def classify(facts: dict) -> Assessment:
    roles = set(facts.get("role") or []) or {"provider", "deployer"}
    tiers: list[str] = []
    a = Assessment(tier="minimal", verdict=VERDICT["minimal"])
    if not facts.get("role"):
        a.flags.append("Role not stated: assumed both provider (you build it) and deployer (you use it).")

    # ---- Art 5 ------------------------------------------------------------------------ #
    for key in facts.get("prohibited") or []:
        if key in PROHIBITED:
            art, text = PROHIBITED[key]
            tiers.append("prohibited")
            a.basis.append(f"{text}: prohibited by {art} since 2 Feb 2025.")
            _art(a, art)
            a.obligations.append(Obligation(art, "Do not place on the market or use; redesign or stop",
                                            "provider" if "provider" in roles else "deployer", APPLIES["art5"]))

    # ---- Annex III, with the 5(b) fraud carve-out and the Art 6(3) derogation ---------- #
    hits = [c for c in facts.get("annex_iii") or [] if c in ANNEX_III]
    if "5b" in hits and facts.get("fraud_detection_only"):
        hits.remove("5b")
        a.basis.append("Fraud detection is carved out of Annex III 5(b): not high-risk on that ground.")
        _art(a, "Annex III 5(b)")
    if hits:
        for c in hits:
            a.basis.append(f"Annex III {c}: {ANNEX_III[c]}.")
            _art(a, f"Annex III {c}")
        claimed = [ART6_3[k] for k in facts.get("art6_3_claim") or [] if k in ART6_3]
        if claimed and facts.get("profiling"):
            a.basis.append(f"Derogation claimed ({'; '.join(claimed)}), but the system profiles people, "
                           "so Art 6(3) keeps it high-risk.")
            _art(a, "Art 6(3)")
            claimed = []
        if claimed:
            a.basis.append(f"Not high-risk under {'; '.join(claimed)}, if documented before use.")
            _art(a, "Art 6(3)")
            a.obligations += [Obligation("Art 6(4)", "Document the not-high-risk assessment", "provider", APPLIES["annex_iii"]),
                              Obligation("Art 49(2)", "Register in the EU database (reduced information)", "provider", APPLIES["annex_iii"])]
            a.flags.append("Relies on the Art 6(3) derogation: a regulator can challenge it; keep the reasoning on file.")
        else:
            tiers.append("high_risk")
            fria = any(c in {"5a", "5b", "5c"} for c in hits) or facts.get("public_body")
            a.obligations += _high_risk_duties(roles, bool(fria) and "deployer" in roles)
            if "provider" in roles:
                _art(a, "Art 9-15")
            if "deployer" in roles:
                _art(a, "Art 26")
            if fria and "deployer" in roles:
                _art(a, "Art 27")
            if any(c.startswith("1") for c in hits):
                a.flags.append("Biometric system: the conformity route may require a notified body (Art 43(1)).")

    # ---- Annex I: AI as a safety component of a regulated product ---------------------- #
    if facts.get("annex_i_safety_component"):
        tiers.append("high_risk")
        a.basis.append("Safety component of a product covered by EU harmonisation law in Annex I, "
                       "needing third-party conformity assessment: high-risk under Art 6(1).")
        _art(a, "Art 6(1)")
        a.obligations += [Obligation(o.article, o.duty, o.holder, ANNEX_I_DATE)
                          for o in _high_risk_duties(roles & {"provider"} or {"provider"}, False)]
        a.flags.append("Annex I date shown as 2 Aug 2027 (original text); check whether the Digital Omnibus moved it.")

    # ---- Art 50 transparency ------------------------------------------------------------- #
    if facts.get("interacts_with_people"):
        tiers.append("transparency")
        a.basis.append("Interacts directly with people: they must be told it is an AI (Art 50(1)).")
        _art(a, "Art 50(1)")
        a.obligations.append(Obligation("Art 50(1)", "Tell people they are interacting with an AI, at first contact",
                                        "provider" if "provider" in roles else "deployer", APPLIES["art50"]))
    if facts.get("generates_synthetic_content") and "provider" in roles:
        tiers.append("transparency")
        a.basis.append("Generates synthetic content: outputs must be marked as AI-generated, machine-readably (Art 50(2)).")
        _art(a, "Art 50(2)")
        a.obligations.append(Obligation("Art 50(2)", "Mark generated content as AI-made, machine-readably", "provider", APPLIES["art50"]))
    if facts.get("emotion_or_biometric_categorisation") and "deployer" in roles:
        tiers.append("transparency")
        _art(a, "Art 50(3)")
        a.obligations.append(Obligation("Art 50(3)", "Inform people exposed to emotion recognition or biometric categorisation",
                                        "deployer", APPLIES["art50"]))
    if facts.get("deepfake"):
        tiers.append("transparency")
        a.basis.append("Produces deep fakes of real people or events: disclose that the content is artificial (Art 50(4)).")
        _art(a, "Art 50(4)")
        a.obligations.append(Obligation("Art 50(4)", "Disclose that the image, audio or video is artificially generated",
                                        "deployer", APPLIES["art50"]))

    # ---- Everyone ------------------------------------------------------------------------ #
    a.obligations.append(Obligation("Art 4", "AI literacy of the staff who operate or use it",
                                    "provider" if "provider" in roles else "deployer", APPLIES["art4"]))

    # ---- Adjacent law ---------------------------------------------------------------------- #
    if facts.get("uses_special_category_data"):
        a.other_law.append("GDPR Art 9: special category data (health, biometrics, beliefs...) needs an Art 9(2) basis.")
    if facts.get("uses_personal_data") and ("high_risk" in tiers or facts.get("profiling")):
        a.other_law.append("GDPR Art 35: a data protection impact assessment is likely required.")
    if facts.get("automated_decision"):
        a.other_law.append("GDPR Art 22: solely automated decisions with significant effects need a lawful basis, "
                           "human intervention and a right to contest.")

    a.tier = min(tiers, key=TIER_ORDER.index) if tiers else "minimal"
    a.verdict = VERDICT[a.tier]
    if a.tier == "minimal":
        a.basis.append("No prohibited practice, no Annex I or III ground and no transparency trigger found: "
                       "minimal risk, voluntary codes only.")
    return a
