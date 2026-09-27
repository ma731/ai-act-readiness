from datetime import date
from pathlib import Path

import yaml

from src.rules import classify

INVENTORY = yaml.safe_load(
    (Path(__file__).parents[1] / "inventory" / "cierzo_systems.yaml").read_text(encoding="utf-8"))
BY_ID = {s["id"]: s for s in INVENTORY["systems"]}


def articles(c):
    return {o.article for o in c.obligations}


def test_health_pricing_is_high_risk_and_needs_a_fria():
    c = classify(BY_ID["S1"])
    assert c.tier == "high_risk"
    assert c.fria_required
    assert {"Art 9", "Art 10", "Art 27", "Art 86"} <= articles(c)


def test_profiling_defeats_the_article_6_3_claim():
    # S1's owner claims the preparatory-task derogation. Profiling overrides it.
    c = classify(BY_ID["S1"])
    assert any("keeps it high-risk" in b for b in c.basis)
    assert "Art 6(4)" not in articles(c)


def test_derogation_holds_without_profiling_but_still_registers():
    s = {**BY_ID["S1"], "profiling": False}
    c = classify(s)
    assert c.tier == "minimal"
    assert {"Art 6(4)", "Art 49(2)"} <= articles(c)


def test_home_pricing_is_not_high_risk():
    c = classify(BY_ID["S6"])
    assert c.tier == "minimal"
    assert any("life and health only" in b for b in c.basis)
    assert any("Test-Achats" in x for x in c.other_law)   # unisex rule still applies


def test_claims_fraud_is_not_listed():
    c = classify(BY_ID["S3"])
    assert c.tier == "minimal"
    assert not c.fria_required


def test_voice_emotion_on_agents_is_prohibited_and_on_customers_high_risk():
    c = classify(BY_ID["S4"])
    assert c.tier == "prohibited"
    assert "Art 5(1)(f)" in articles(c)
    assert "Art 50(3)" in articles(c)
    assert any("Annex III 1(c)" in b for b in c.basis)


def test_text_sentiment_is_not_emotion_recognition():
    s = {**BY_ID["S4"], "emotion_recognition": {"subjects": ["employees", "customers"],
                                                  "input": "text"}}
    c = classify(s)
    assert c.tier == "minimal"
    assert "Art 5(1)(f)" not in articles(c)


def test_life_underwriting_as_deployer_gets_deployer_duties_only():
    c = classify(BY_ID["S5"])
    assert c.tier == "high_risk"
    assert c.fria_required
    holders = {o.holder for o in c.obligations}
    assert holders == {"deployer"}
    assert "Art 26(2)" in articles(c)


def test_chatbot_disclosure_is_already_in_force():
    c = classify(BY_ID["S2"])
    assert c.tier == "transparency"
    art50_1 = next(o for o in c.obligations if o.article == "Art 50(1)")
    assert art50_1.in_force


def test_marking_grace_period_for_systems_already_on_the_market():
    c = classify(BY_ID["S2"])
    art50_2 = next(o for o in c.obligations if o.article == "Art 50(2)")
    assert art50_2.applies_from == date(2026, 12, 2)
    fresh = classify({**BY_ID["S2"], "placed_on_market": date(2026, 9, 1)})
    assert next(o for o in fresh.obligations
                if o.article == "Art 50(2)").applies_from == date(2026, 8, 2)


def test_chatbot_feeding_the_pricing_model_is_flagged():
    c = classify(BY_ID["S2"])
    assert any("S1" in f for f in c.flags)


def test_high_risk_deadline_is_the_omnibus_date():
    c = classify(BY_ID["S1"])
    assert next(o for o in c.obligations if o.article == "Art 9").applies_from == \
        date(2027, 12, 2)


def test_systems_already_in_service_are_flagged_as_legacy():
    c = classify(BY_ID["S1"])
    assert c.legacy_art111
    assert any("Art 111(2)" in f and "re-rating" in f for f in c.flags)
    assert not classify({**BY_ID["S1"], "placed_on_market": date(2028, 1, 1)}).legacy_art111
