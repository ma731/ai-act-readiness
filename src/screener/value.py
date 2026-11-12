"""What is at stake: the fine ceiling from Art 99, and what compliance costs by the Commission's own estimate.

Fines are the law. Costs are the estimates in the study behind the Commission's impact
assessment (CEPS, ICF and Wavestone, "Study to support an impact assessment of regulatory
requirements for AI in Europe", Final Report D5, April 2021, p. 12). They were made for the
2021 draft, per "AI unit" of EUR 170,000 development cost, so they are an order of
magnitude, not a quote.
"""
from __future__ import annotations

SOURCE = ("European Commission, Study to support an impact assessment of regulatory requirements for AI "
          "in Europe, Final Report D5 (CEPS, ICF, Wavestone), April 2021, p. 12")

FINES = {
    "prohibited": ("Art 99(3)", 35_000_000, 7),
    "high_risk": ("Art 99(4)", 15_000_000, 3),
    "transparency": ("Art 99(4)", 15_000_000, 3),
}


def _eur(n: int) -> str:
    return f"EUR {n / 1e6:g}M" if n >= 1_000_000 else f"EUR {n:,}"


def at_stake(tier: str, roles: list[str] | None = None, turnover: float | None = None) -> dict:
    roles = roles or []
    out: dict = {"tier": tier, "fine": None, "costs": [], "source": SOURCE}
    if tier in FINES:
        art, cap, pct = FINES[tier]
        line = f"Up to {_eur(cap)} or {pct}% of worldwide annual turnover, whichever is higher ({art}); for SMEs, whichever is lower (Art 99(6))."
        out["fine"] = {"article": art, "cap_eur": cap, "pct": pct, "text": line}
        if turnover:
            out["fine"]["max_eur"] = max(cap, turnover * pct / 100)
    if tier == "prohibited":
        out["costs"].append("No compliance route: the practice has to be redesigned or dropped.")
    elif tier == "high_risk":
        if "deployer" in roles and "provider" not in roles:
            out["costs"].append("As a deployer, most cost sits with the vendor; budget for oversight staff, "
                                "logs and, for public bodies and some financial uses, an Art 27 impact assessment.")
        else:
            out["costs"] += [
                "About EUR 29,000 a year per system to meet the requirements (data, records, information, "
                "oversight, robustness), on EUR 170,000 of development.",
                "About EUR 16,800 to 23,000 if a notified body has to examine it.",
                "About EUR 193,000 to 330,000 once, plus EUR 71,400 a year, to set up a quality management "
                "system if there is none.",
            ]
    elif tier == "transparency":
        out["costs"].append("Low: a clear notice that people are dealing with an AI, and labels on generated content.")
    else:
        out["costs"].append("No AI Act cost beyond staff AI literacy (Art 4).")
    return out
