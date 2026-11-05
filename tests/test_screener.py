"""The proposal screener: the law in code, the quote guard, the memo check, the workflow."""
import csv
from pathlib import Path

import pytest

from src.screener.law import PROHIBITED, classify
from src.screener.pipeline import check_memo, screen_one, template_memo
from src.screener.readers import OfflineReader, facts_from_evidence, verify_quotes

SAMPLE = Path(__file__).parents[1] / "data" / "proposals_sample.csv"
ROWS = list(csv.DictReader(SAMPLE.open(encoding="utf-8")))


# ---------- the law, in code ----------
@pytest.mark.parametrize("key", sorted(PROHIBITED))
def test_every_art5_practice_is_prohibited(key):
    a = classify({"prohibited": [key]})
    assert a.tier == "prohibited" and a.verdict == "Do not proceed"


def test_prohibited_outranks_everything_else():
    a = classify({"prohibited": ["social_scoring"], "annex_iii": ["5a"], "interacts_with_people": True})
    assert a.tier == "prohibited"


def test_fraud_detection_is_carved_out_of_credit_scoring():
    assert classify({"annex_iii": ["5b"]}).tier == "high_risk"
    assert classify({"annex_iii": ["5b"], "fraud_detection_only": True}).tier == "minimal"


def test_art6_3_derogation_holds_unless_the_system_profiles():
    assert classify({"annex_iii": ["4b"], "art6_3_claim": ["preparatory"]}).tier == "minimal"
    assert classify({"annex_iii": ["4b"], "art6_3_claim": ["preparatory"], "profiling": True}).tier == "high_risk"


def test_deployer_of_credit_scoring_owes_a_fundamental_rights_assessment():
    a = classify({"annex_iii": ["5b"], "role": ["deployer"]})
    assert "Art 27" in {o.article for o in a.obligations}
    assert "Art 27" not in {o.article for o in classify({"annex_iii": ["4a"], "role": ["deployer"]}).obligations}


def test_transparency_duties_follow_the_role():
    assert {o.article for o in classify({"generates_synthetic_content": True, "role": ["provider"]}).obligations} >= {"Art 50(2)"}
    assert classify({"generates_synthetic_content": True, "role": ["deployer"]}).tier == "minimal"


# ---------- the quote guard ----------
def test_facts_without_a_real_quote_are_dropped():
    text = "We will use a chatbot on our website."
    kept, rejected = verify_quotes(text, [
        {"fact": "interacts_with_people", "value": True, "quote": "We will use a chatbot"},
        {"fact": "prohibited", "value": "social_scoring", "quote": "We score every resident"},   # invented
    ])
    assert [e["fact"] for e in kept] == ["interacts_with_people"]
    assert facts_from_evidence(kept) == {"interacts_with_people": True}
    assert len(rejected) == 1


def test_a_hallucinating_reader_cannot_change_the_verdict():
    class Liar:
        name = "liar"

        def read(self, text):
            return {"evidence": [{"fact": "prohibited", "value": "social_scoring", "quote": "scores every citizen"}],
                    "unknowns": []}
    s = screen_one({"id": "X", "title": "Stock forecast", "proposal": "We forecast weekly demand from past sales."}, Liar())
    assert s.assessment.tier == "minimal"
    assert any("quotes not found" in r for r in s.review_reasons)


# ---------- the memo check ----------
def test_memo_may_only_cite_articles_the_classification_used():
    a = classify({"interacts_with_people": True, "role": ["deployer"]})
    assert check_memo(template_memo("Chatbot", a), a) == []
    assert any("Art 5" in p for p in check_memo(f"{a.verdict}. This breaches Art 5(1)(c).", a))
    assert any("verdict" in p for p in check_memo("Fine to go ahead under Art 50(1).", a))


# ---------- the workflow on the labelled sample ----------
@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["id"])
def test_offline_reader_matches_the_labels(row):
    assert screen_one(row, OfflineReader()).assessment.tier == row["expected_tier"]


def test_every_kept_fact_is_backed_by_a_quote_in_the_proposal():
    for row in ROWS:
        s = screen_one(row, OfflineReader())
        for e in s.evidence:
            assert " ".join(e["quote"].lower().split()) in " ".join(row["proposal"].lower().split())


def test_hard_cases_go_to_human_review():
    by_id = {r["id"]: screen_one(r, OfflineReader()) for r in ROWS}
    assert by_id["P05"].needs_review          # claims Art 6(3) while profiling workers
    assert by_id["P14"].needs_review          # 'significant harm' is a judgement call
    assert not by_id["P11"].needs_review      # stock forecasting is plainly minimal


def test_cli_writes_the_workbook(tmp_path):
    from scripts.screen_proposals import main
    assert main([str(SAMPLE), "--offline", "--out", str(tmp_path)]) == 0
    import openpyxl
    wb = openpyxl.load_workbook(tmp_path / "screening.xlsx")
    assert {"Summary", "Review queue", "Obligations", "Evidence", "Evaluation", "About"} <= set(wb.sheetnames)
    assert wb["Summary"].max_row == len(ROWS) + 1
