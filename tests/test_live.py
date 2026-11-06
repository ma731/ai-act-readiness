"""Live register, Dutch reading rules, generated stress test. No network."""
from src.screener import generate, register
from src.screener.pipeline import screen_one, to_dict
from src.screener.readers import OfflineReader

CSV = (
    "name,organization,description_short,goal,methods_and_models,human_intervention,risks,provider,"
    "publication_category,status,category,publication_dt,algorithm_id\n"
    'Risicoscan bijstand,Gemeente A,Een risicoscan bij aanvragen voor bijstand.,Controle op rechtmatigheid,'
    'Model geeft een risicoscore per aanvraag,De medewerker beslist,,Leverancier X,Hoog-risico AI-systeem,'
    "In gebruik,Sociale zekerheid,2026-11-01 08:00:00+00:00,a1\n"
    "Parkeercontrole,Gemeente B,Scanauto leest kentekens.,Handhaving parkeren,"
    "Camera herkent kentekens,Een buitengewoon opsporingsambtenaar controleert,,,Overige algoritmes,"
    "In gebruik,Verkeer,2026-10-01 08:00:00+00:00,b2\n"
)


def test_register_rows_carry_the_declared_category_and_a_link():
    rows = register.to_rows(CSV)
    assert [r["declared"] for r in rows] == ["high_risk", "other"]
    assert rows[0]["url"].endswith("/a1") and rows[0]["lang"] == "nl"
    assert "Leverancier: Leverancier X." in rows[0]["proposal"]


def test_dutch_reader_flags_benefit_risk_scoring_but_not_parking_wardens():
    rows = {r["id"]: r for r in register.to_rows(CSV)}
    nl = OfflineReader("nl")
    assert screen_one(rows["a1"], nl).assessment.tier == "high_risk"           # 5(a) with profiling
    parking = screen_one(rows["b2"], nl)
    assert parking.assessment.tier == "minimal"                               # a BOA is not law enforcement under Annex III 6
    assert "Annex III 6" not in parking.assessment.articles


def test_hotspot_maps_are_not_person_based_crime_prediction():
    row = {"id": "h", "title": "Hotspots", "proposal": "Op basis daarvan voorspellen we waar kleine criminaliteit kan plaatsvinden."}
    assert screen_one(row, OfflineReader("nl")).assessment.tier != "prohibited"


def test_update_only_rescreens_what_changed():
    rows = register.to_rows(CSV)
    cache, n = register.update(rows, {}, OfflineReader("nl"), screen_one, to_dict)
    assert n == 2
    cache, n = register.update(rows, cache, OfflineReader("nl"), screen_one, to_dict)
    assert n == 0                                                             # same reader, same publication date
    rows[0]["published"] = "2026-11-05"
    cache, n = register.update(rows, cache, OfflineReader("nl"), screen_one, to_dict)
    assert n == 1
    cache, n = register.update(rows[:1], cache, OfflineReader("nl"), screen_one, to_dict)
    assert set(cache) == {"a1"}                                               # withdrawn entries drop out


def test_comparison_counts_agreement_with_declarations():
    rows = register.to_rows(CSV)
    cache, _ = register.update(rows, {}, OfflineReader("nl"), screen_one, to_dict)
    c = register.compare(list(cache.values()))
    assert c["declared_high_risk"] == 1 and c["agree_on_declared"] == 1 and c["recall_on_declared"] == 1.0


def test_generated_set_is_deterministic_and_balanced():
    a, b = generate.generate(), generate.generate()
    assert a == b
    assert {r["style"] for r in a} == {"plain", "disguised"}
    assert {r["expected_tier"] for r in a} == set(generate.TIERS)
    assert len({r["id"] for r in a}) == len(a)


def test_generated_labels_are_written_by_hand_not_by_the_classifier():
    ad = [r for r in generate.generate() if r["scenario"] == "ad_generation"]
    assert {r["role"]: r["expected_tier"] for r in ad} == {"provider": "transparency", "deployer": "minimal"}


def test_evaluation_counts_the_dangerous_misses():
    rows = generate.generate()
    ev = generate.evaluate(rows, [screen_one(r, OfflineReader()) for r in rows])
    assert ev["n"] == len(rows)
    assert ev["by_style"]["plain"]["accuracy"] > ev["by_style"]["disguised"]["accuracy"]
    assert ev["under_called_severe"] == sum(1 for m in ev["misses"]
                                            if m["expected"] in ("prohibited", "high_risk")
                                            and generate.TIERS.index(m["got"]) > generate.TIERS.index(m["expected"]))
