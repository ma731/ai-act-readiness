"""Classify one AI system under the EU AI Act and list what it owes.

Covers the parts of Regulation (EU) 2024/1689 an insurer's inventory touches, as amended by
the Digital Omnibus on AI (in force 27 July 2026). Every conclusion carries the article it
rests on, so a reviewer can check the reasoning instead of trusting it.

This is decision support for a compliance review, not legal advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

LEGAL_BASIS_DATE = date(2026, 9, 27)

APPLIES = {
    "art5": date(2025, 2, 2),
    "art4": date(2025, 2, 2),
    "art50": date(2026, 8, 2),
    # Art 50(2) marking: systems already on the market before 2 Aug 2026 get until 2 Dec 2026.
    "art50_2_existing": date(2026, 12, 2),
    # Omnibus moved stand-alone Annex III high-risk from 2 Aug 2026.
    "annex_iii": date(2027, 12, 2),
}

TIER_ORDER = ["prohibited", "high_risk", "transparency", "minimal"]

BIOMETRIC_INPUTS = {"voice_acoustics", "face", "physiological"}
LIFE_AND_HEALTH = {"life", "health"}
PRICING_FUNCTIONS = {"pricing", "risk_assessment"}
ART6_3_CONDITIONS = {
    "narrow_procedural": "Art 6(3)(a) narrow procedural task",
    "improves_human_result": "Art 6(3)(b) improves a completed human activity",
    "detects_patterns": "Art 6(3)(c) detects deviations, does not replace human assessment",
    "preparatory": "Art 6(3)(d) preparatory task",
}


@dataclass
class Obligation:
    article: str
    duty: str
    holder: str
    applies_from: date

    @property
    def in_force(self) -> bool:
        return self.applies_from <= LEGAL_BASIS_DATE


@dataclass
class Classification:
    system_id: str
    tier: str
    basis: list[str] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    other_law: list[str] = field(default_factory=list)
    fria_required: bool = False
    legacy_art111: bool = False


def _worst(tiers: list[str]) -> str:
    return min(tiers, key=TIER_ORDER.index) if tiers else "minimal"


def _high_risk_duties(roles: set[str], fria: bool) -> list[Obligation]:
    d = APPLIES["annex_iii"]
    out = []
    if "provider" in roles:
        out += [
            Obligation("Art 9", "Risk management system across the lifecycle", "provider", d),
            Obligation("Art 10", "Data governance: relevant, representative, bias examined",
                       "provider", d),
            Obligation("Art 11", "Technical documentation (Annex IV)", "provider", d),
            Obligation("Art 12", "Automatic event logging", "provider", d),
            Obligation("Art 13", "Instructions for use for deployers", "provider", d),
            Obligation("Art 14", "Designed for effective human oversight", "provider", d),
            Obligation("Art 15", "Accuracy, robustness, cybersecurity declared and met",
                       "provider", d),
            Obligation("Art 17", "Quality management system", "provider", d),
            Obligation("Art 43", "Conformity assessment before putting into service",
                       "provider", d),
            Obligation("Art 47-48", "EU declaration of conformity and CE marking", "provider", d),
            Obligation("Art 49(1)", "Register in the EU database", "provider", d),
            Obligation("Art 72-73", "Post-market monitoring and serious incident reporting",
                       "provider", d),
        ]
    if "deployer" in roles:
        out += [
            Obligation("Art 26(1)", "Use according to the instructions for use", "deployer", d),
            Obligation("Art 26(2)", "Human oversight by competent, trained, empowered staff",
                       "deployer", d),
            Obligation("Art 26(4)", "Input data relevant and representative, where controlled",
                       "deployer", d),
            Obligation("Art 26(5)", "Monitor operation, report risks and serious incidents",
                       "deployer", d),
            Obligation("Art 26(6)", "Keep logs at least six months", "deployer", d),
            Obligation("Art 26(11)", "Tell people a high-risk system is used in decisions about "
                       "them", "deployer", d),
            Obligation("Art 86", "Explain the system's role in a decision on request",
                       "deployer", d),
        ]
        if fria:
            out.append(Obligation("Art 27", "Fundamental rights impact assessment before first "
                                  "use, notified to the market surveillance authority",
                                  "deployer", d))
    return out


def classify(system: dict) -> Classification:
    sid = system["id"]
    roles = set(system.get("role", []))
    tiers: list[str] = []
    c = Classification(system_id=sid, tier="minimal")

    # ---- Art 5 prohibited practices, and Annex III 1(c) emotion recognition ----------- #
    emo = system.get("emotion_recognition")
    annex_iii_hit: str | None = None
    if emo:
        biometric = emo.get("input") in BIOMETRIC_INPUTS
        subjects = set(emo.get("subjects", []))
        if not biometric:
            c.basis.append("Infers emotion from text, not biometric data, so it is not an "
                           "'emotion recognition system' under Art 3(39).")
            c.flags.append("Keep the input text-only: adding voice or face analysis changes "
                           "the classification.")
        else:
            if "employees" in subjects and not emo.get("medical_or_safety"):
                tiers.append("prohibited")
                c.basis.append("Infers emotions of workers from biometric data: prohibited by "
                               "Art 5(1)(f) since 2 Feb 2025.")
                c.obligations.append(Obligation(
                    "Art 5(1)(f)", "Do not use on employees; remove that capability",
                    "deployer", APPLIES["art5"]))
            if subjects - {"employees"}:
                annex_iii_hit = "1(c)"
                c.basis.append("Emotion recognition on customers is listed high-risk in "
                               "Annex III 1(c).")
                if "deployer" in roles:
                    c.obligations.append(Obligation(
                        "Art 50(3)", "Inform people exposed to emotion recognition",
                        "deployer", APPLIES["art50"]))

    # ---- Annex III 5(c) and its limits ---------------------------------------------- #
    line = system.get("insurance_line")
    funcs = set(system.get("function", []))
    if line and funcs & PRICING_FUNCTIONS and system.get("affects_natural_persons", True):
        if line in LIFE_AND_HEALTH:
            annex_iii_hit = annex_iii_hit or "5(c)"
            c.basis.append(f"Risk assessment or pricing of natural persons in {line} insurance: "
                           "Annex III 5(c).")
        else:
            c.basis.append(f"Pricing in {line} insurance is not listed: Annex III 5(c) covers "
                           "life and health only.")
    if "claims_fraud" in funcs:
        c.basis.append("Claims fraud detection is not listed in Annex III. The fraud carve-out "
                       "in 5(b) concerns credit scoring and is not needed here.")

    # ---- Art 6(3) derogation, blocked by profiling ---------------------------------- #
    if annex_iii_hit:
        claimed = [ART6_3_CONDITIONS[k] for k in system.get("art6_3_conditions", [])
                   if k in ART6_3_CONDITIONS]
        if claimed and system.get("profiling"):
            c.basis.append(f"Derogation claimed ({'; '.join(claimed)}) but the system profiles "
                           "natural persons, so Art 6(3) keeps it high-risk.")
            claimed = []
        elif system.get("profiling"):
            c.basis.append("Profiles natural persons: Art 6(3) derogation unavailable.")
        if claimed:
            c.basis.append(f"Not high-risk under {'; '.join(claimed)}.")
            c.obligations += [
                Obligation("Art 6(4)", "Document the not-high-risk assessment before market",
                           "provider", APPLIES["annex_iii"]),
                Obligation("Art 49(2)", "Register in the EU database (reduced information)",
                           "provider", APPLIES["annex_iii"]),
            ]
        else:
            tiers.append("high_risk")
            c.fria_required = annex_iii_hit in {"5(b)", "5(c)"} and "deployer" in roles
            c.obligations += _high_risk_duties(roles, c.fria_required)
            on_market = system.get("placed_on_market")
            if on_market is not None and on_market < APPLIES["annex_iii"]:
                c.legacy_art111 = True
                c.flags.append(
                    "Already in service: under Art 111(2) the high-risk duties bite only once "
                    "its design changes significantly. Confirm the post-Omnibus cut-off in "
                    "Regulation (EU) 2026/1744 before relying on this"
                    + ("; a scheduled re-rating that changes factors or model form is likely "
                       "such a change." if system.get("rerated_annually") else "."))
            if annex_iii_hit == "1(c)":
                c.flags.append("Biometric system: Art 43(1) conformity route depends on "
                               "harmonised standards; a notified body may be required.")

    # ---- Art 50 transparency -------------------------------------------------------- #
    if system.get("interacts_with_people"):
        tiers.append("transparency")
        holder = "provider" if "provider" in roles else "deployer"
        c.basis.append("Interacts directly with people: Art 50(1) disclosure at first contact "
                       "(Art 50(5)).")
        c.obligations.append(Obligation(
            "Art 50(1)", "Tell users they are talking to an AI, clearly, at first interaction",
            holder, APPLIES["art50"]))
        if holder == "deployer":
            c.flags.append("Art 50(1) binds the provider; as deployer, verify the vendor's "
                           "disclosure is switched on.")
    if system.get("generates_synthetic_content") and "provider" in roles:
        tiers.append("transparency")
        on_market = system.get("placed_on_market")
        existing = on_market is not None and on_market < APPLIES["art50"]
        c.obligations.append(Obligation(
            "Art 50(2)", "Mark generated text or audio as AI-made, machine-readably",
            "provider", APPLIES["art50_2_existing"] if existing else APPLIES["art50"]))
        c.flags.append("A system built on a third-party model is still the provider of that "
                       "system; check whether the model vendor's marking reaches your output.")

    # ---- Everyone -------------------------------------------------------------------- #
    c.obligations.append(Obligation(
        "Art 4", "Support AI literacy of staff who operate or use it (as softened by the Omnibus)",
        "provider" if "provider" in roles else "deployer", APPLIES["art4"]))

    feeds = system.get("feeds", [])
    if feeds:
        c.flags.append(f"Its output becomes input to {', '.join(feeds)}: that path must be in "
                       "the receiving system's data governance, logs and instructions for use.")

    # ---- Adjacent law an AI Act review should not miss ------------------------------- #
    if system.get("uses_health_data"):
        c.other_law.append("GDPR Art 9: health data is special category; needs an Art 9(2) "
                           "basis. Art 35 DPIA (the FRIA may reuse it, AI Act Art 27(4)).")
    if system.get("automated_decision"):
        c.other_law.append("GDPR Art 22: solely automated decisions with significant effect "
                           "need a lawful basis, human intervention and contest rights.")
    if line and funcs & PRICING_FUNCTIONS:
        c.other_law.append("Directive 2004/113 Art 5 (Test-Achats, C-236/09): sex must not "
                           "change premiums or benefits; pregnancy and maternity costs must "
                           "not either.")

    c.tier = _worst(tiers)
    return c


def classify_all(systems: list[dict]) -> list[Classification]:
    return [classify(s) for s in systems]
