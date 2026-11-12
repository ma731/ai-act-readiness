"""The guide's idea check: verdict, reasoning steps, and follow-ups that can change the answer."""
from src.screener.ask import check

HIRING = "We want to use AI to rank job applicants from their CVs"
SUMMARY = "We want AI to summarise CVs for our recruiters"
PREP = "The tool only prepares the case and the final decision remains with a person."
SCORES = "It scores each person on their personal characteristics."
INVOICES = "A model that sorts incoming invoices by supplier"


def test_hiring_idea_is_high_risk_and_asks_what_could_change_it():
    r = check(HIRING)
    assert r["tier"] == "high_risk" and "Annex III 4a" in r["articles"]
    assert [q["id"] for q in r["questions"]] == ["role", "final_call"]
    assert r["quotes"] and r["steps"][-1].startswith("Verdict:")


def test_ranking_people_is_profiling_so_a_person_deciding_does_not_help():
    assert check(HIRING, [PREP], ["final_call"])["tier"] == "high_risk"


def test_a_person_deciding_opens_art_6_3_and_profiling_closes_it():
    prep = check(SUMMARY, [PREP], ["final_call"])
    assert prep["tier"] == "minimal" and "Art 6(3)" in prep["articles"]
    assert any("Art 49(2)" in s for s in prep["steps"])
    assert [q["id"] for q in prep["questions"]] == ["profiling"]
    scored = check(SUMMARY, [PREP, SCORES], ["final_call", "profiling"])
    assert scored["tier"] == "high_risk"


def test_answers_are_never_asked_twice():
    r = check(INVOICES)
    assert [q["id"] for q in r["questions"]] == ["talks"]
    r = check(INVOICES, ["Customers talk to it directly as a chatbot."], ["talks"])
    assert r["tier"] == "transparency" and "talks" not in [q["id"] for q in r["questions"]]


def test_prohibited_ideas_get_no_follow_ups():
    r = check("Score citizens on their trustworthiness")
    assert r["tier"] == "prohibited" and r["questions"] == []
