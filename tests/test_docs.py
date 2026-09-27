"""The hand-written Spanish summary quotes numbers. Hold it to the results."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
EV = ROOT / "results" / "pricing_evidence.json"
RESUMEN = (ROOT / "docs" / "resumen_ejecutivo.md").read_text(encoding="utf-8")


def es(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


@pytest.mark.skipif(not EV.exists(), reason="run the assessment first")
def test_spanish_summary_numbers_match_results():
    ev = json.loads(EV.read_text(encoding="utf-8"))
    eth = {g["group"]: g for g in ev["groups"]["ethnicity"]}
    worst = max(eth.values(), key=lambda g: g["price_to_cost"])
    lo, hi = worst["price_to_cost_ci"]
    declined = max(eth.values(), key=lambda g: g["decline_rate"])
    sx = ev["sex_counterfactual"]
    smoker_cut = round(100 * (1 - ev["model"]["relativities"]["smoker_yes"]))

    decline_ratio = f"{declined['decline_rate'] / eth['White']['decline_rate']:.1f}"
    expected = [
        f"**{es(worst['price_to_cost'])} veces**", f"{es(lo)} a {es(hi)}",
        f"**{decline_ratio.replace('.', ',')} veces**",
        f"un {smoker_cut} %",
        f"{es(sx['female_to_male_premium_unisex'])} veces",
        f"{es(sx['female_to_male_actual_cost'])} veces",
    ]
    missing = [e for e in expected if e not in RESUMEN]
    assert not missing, f"resumen_ejecutivo.md is stale: {missing}"


def test_no_em_dashes_in_docs():
    for p in [*ROOT.glob("docs/**/*.md"), ROOT / "README.md"]:
        if p.exists():
            assert "—" not in p.read_text(encoding="utf-8"), p
