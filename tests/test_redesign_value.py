"""Redesign options, what is at stake, and the supply-chain pack against its hand labels."""
import csv
from pathlib import Path

from src.screener.pipeline import screen_one
from src.screener.redesign import options
from src.screener.value import at_stake

ROOT = Path(__file__).parents[1]
VOICE = "We will use a tool that detects stress in our call-centre agents' voices to coach them."
HIRING = "We use AI to rank job applicants from their CVs."
SUMMARY = "We want AI to summarise CVs for our recruiters."
BENEFITS = ("An AI that decides which benefit applicants are eligible for social assistance "
            "and scores each applicant.")


def facts(text):
    return screen_one({"id": "x", "proposal": text}).facts


def test_voice_emotion_at_work_becomes_allowed_on_text():
    best = options(facts(VOICE))[0]
    assert best["levers"] == ["text_not_biometrics"] and best["to"] == "minimal"
    assert "Art 3(39)" in best["why"]


def test_a_person_deciding_lowers_hiring_and_profiling_must_go_too():
    assert options(facts(SUMMARY))[0]["levers"] == ["person_decides"]
    assert set(options(facts(HIRING))[0]["levers"]) == {"person_decides", "no_profiling"}
    assert set(options(facts(BENEFITS))[0]["levers"]) == {"person_decides", "no_profiling"}


def test_nothing_to_redesign_when_already_minimal():
    assert options(facts("A model forecasts weekly demand per store from sales history.")) == []


def test_fines_follow_article_99_and_costs_cite_the_study():
    p = at_stake("prohibited")
    assert p["fine"]["cap_eur"] == 35_000_000 and p["fine"]["pct"] == 7
    h = at_stake("high_risk", ["provider"], turnover=1_000_000_000)
    assert h["fine"]["max_eur"] == 30_000_000                    # 3% of 1bn beats 15M
    assert any("29,000" in c for c in h["costs"]) and "Final Report D5" in h["source"]
    assert at_stake("minimal")["fine"] is None


def test_supply_chain_pack_matches_hand_labels_except_the_known_miss():
    path = ROOT / "data" / "supply_chain_ideas.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    tier = {r["id"]: screen_one({"id": r["id"], "proposal": r["proposal"]}).assessment.tier
            for r in rows}
    misses = {r["id"] for r in rows if tier[r["id"]] != r["expected_tier"]}
    assert misses == {"SC12"}     # B2B credit: a keyword rule cannot tell a company from a person


def test_driver_fatigue_is_not_emotion_recognition():
    text = "Truck cameras detect driver fatigue from eye closure to prevent accidents."
    assert screen_one({"id": "f", "proposal": text}).assessment.tier != "prohibited"   # Recital 18
