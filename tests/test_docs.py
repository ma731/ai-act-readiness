"""Hand-written text that quotes numbers is held to the results here."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
EV = ROOT / "results" / "pricing_evidence.json"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def es(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


needs_results = pytest.mark.skipif(not EV.exists(), reason="run the assessment first")


@needs_results
def test_spanish_summary_numbers_match_results():
    ev = json.loads(EV.read_text(encoding="utf-8"))
    born = {g["group"]: g for g in ev["groups"]["born"]}["Born abroad"]
    lo, hi = born["price_to_cost_ci"]
    un = {(u["group"], u["measure"]): u["rate"] for u in ev["unmet_need"]}
    sx = ev["sex_counterfactual"]
    cls = ev["self_rated_health_by_class"]
    d = ev["data"]
    expected = [
        f"**{es(born['price_to_cost'])} veces**", f"{es(lo)} a {es(hi)}",
        f"**{es(100 * un[('Born abroad', 'unmet_cost')], 1)} %**",
        f"**{es(100 * un[('Born in Spain', 'unmet_cost')], 1)} %**",
        f"{es(sx['female_to_male_premium_unisex'])} veces",
        f"{es(sx['female_to_male_actual_cost'])} veces",
        f"**{es(100 * cls[0]['fair_or_worse_age_standardised'], 1)} %**",
        f"**{es(100 * cls[-1]['fair_or_worse_age_standardised'], 1)} %**",
        f"{d['people']:,}".replace(",", "."),
    ]
    text = read("docs/resumen_ejecutivo.md")
    missing = [e for e in expected if e not in text]
    assert not missing, f"resumen_ejecutivo.md is stale: {missing}"


@needs_results
def test_adr_numbers_match_results():
    ev = json.loads(EV.read_text(encoding="utf-8"))
    d, m = ev["data"], ev["model"]
    adr1 = read("docs/decisions/0001-spanish-data-and-prices.md")
    for n in [d["people"], d["with_private_cover"], ev["private_cover_only"]["born"][0]["n"]]:
        assert f"{n:,}" in adr1, n
    assert f"{m['gini_glm']:.3f}" in read("docs/decisions/0004-poisson-glm.md")


def test_no_em_dashes_in_docs():
    for p in [*ROOT.glob("docs/**/*.md"), ROOT / "README.md"]:
        assert "—" not in p.read_text(encoding="utf-8"), p


def test_no_us_data_left_in_docs():
    for p in [*ROOT.glob("docs/**/*.md"), ROOT / "README.md"]:
        text = p.read_text(encoding="utf-8")
        if p.name == "0001-spanish-data-and-prices.md":
            continue                                   # explains why MEPS was dropped
        assert "MEPS" not in text and "Hispanic" not in text, p
