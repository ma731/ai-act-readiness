"""Live EU cases, reading rules, generated stress test. No network."""
from src.screener import generate, pstw
from src.screener.pipeline import screen_one, to_dict
from src.screener.readers import OfflineReader

HEAD = ("PSTW ID,Name,Website,Description,Geographical coverage (country),Responsible organisation,"
        "Responsible organisation category,Functions of Government (COFOG level I), Status,Start Year,"
        "Primary Technology,Date updated\n")
CSV = HEAD + (
    "PSTW-1,Benefit risk scan,https://a.example,Social assistance eligibility is checked by a model that "
    "scores each applicant.,Belgium,City A,Local Government,Social protection,Implemented,2022,"
    "Artificial Intelligence,26/05/2026\n"
    "PSTW-2,Tree map,https://b.example,Satellite images are used to map tree cover in parks.,Italy,City B,"
    "Local Government,Environmental protection,Pilot,2023,Artificial Intelligence,01/02/2026\n"
    "PSTW-3,Chain ledger,https://c.example,A ledger for land titles.,Spain,Agency C,Central-Government,"
    "Economic affairs,Implemented,2021,Blockchain,01/02/2026\n"
    "PSTW-4,UK chatbot,https://d.example,A chatbot answers tax questions.,United Kingdom,Dept D,"
    "Central-Government,General public services,Implemented,2021,Artificial Intelligence,01/02/2026\n"
)


def test_rows_keep_eu_ai_cases_only_with_dates_and_links():
    rows = pstw.to_rows(CSV)
    assert [r["id"] for r in rows] == ["PSTW-1", "PSTW-2"]          # no blockchain, no UK
    assert rows[0]["updated"] == "2026-05-26" and rows[0]["url"] == "https://a.example"
    assert rows[0]["status"] == "Implemented" and rows[0]["lang"] == "en"


def test_benefit_risk_scoring_is_high_risk_and_tree_maps_are_not():
    rows = {r["id"]: r for r in pstw.to_rows(CSV)}
    assert screen_one(rows["PSTW-1"], OfflineReader()).assessment.tier == "high_risk"
    assert screen_one(rows["PSTW-2"], OfflineReader()).assessment.tier == "minimal"


def test_text_sentences_are_not_criminal_sentencing():
    row = {"id": "s", "title": "Search", "proposal": "Links can also be made between phrases or sentences."}
    assert "Annex III 8a" not in screen_one(row, OfflineReader()).assessment.articles


def test_dutch_reader_flags_benefit_risk_scoring_but_not_parking_wardens():
    nl = OfflineReader("nl")
    a = {"id": "a", "title": "Risicoscan bijstand", "proposal": "Model geeft een risicoscore per aanvraag voor bijstand."}
    b = {"id": "b", "title": "Parkeercontrole", "proposal": "Camera herkent kentekens. Een buitengewoon opsporingsambtenaar controleert."}
    assert screen_one(a, nl).assessment.tier == "high_risk"
    assert "Annex III 6" not in screen_one(b, nl).assessment.articles


def test_hotspot_maps_are_not_person_based_crime_prediction():
    row = {"id": "h", "title": "Hotspots", "proposal": "Op basis daarvan voorspellen we waar kleine criminaliteit kan plaatsvinden."}
    assert screen_one(row, OfflineReader("nl")).assessment.tier != "prohibited"


def test_update_only_rescreens_what_changed():
    rows = pstw.to_rows(CSV)
    cache, n = pstw.update(rows, {}, OfflineReader(), screen_one, to_dict)
    assert n == 2
    cache, n = pstw.update(rows, cache, OfflineReader(), screen_one, to_dict)
    assert n == 0                                                     # same reader, same edit date
    rows[0]["updated"] = "2026-06-30"
    cache, n = pstw.update(rows, cache, OfflineReader(), screen_one, to_dict)
    assert n == 1
    cache, n = pstw.update(rows[:1], cache, OfflineReader(), screen_one, to_dict)
    assert set(cache) == {"PSTW-1"}                                   # withdrawn cases drop out


def test_summary_counts_cases_in_use():
    cache, _ = pstw.update(pstw.to_rows(CSV), {}, OfflineReader(), screen_one, to_dict)
    s = pstw.summarise(list(cache.values()))
    assert s["cases"] == 2 and s["in_use"] == 2 and s["high_risk_or_prohibited"] == 1 and s["countries"] == 2


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
