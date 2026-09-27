"""The cost arithmetic, on hand-made survey rows, so a wrong price or multiplier fails here."""
import numpy as np
import pandas as pd

from src.pricing import annual_cost, tariffs

T = tariffs()
BLANK = {"N48": "3", "N49": np.nan, "N51": np.nan, "O79": np.nan, "O83": "", "O67": np.nan,
         "O68": np.nan, "O76": np.nan, "N59": "2", "N60_1": "2", "N60_2": "2", "N60_3": "2",
         "N60_4": "2"}


def cost(**answers) -> pd.Series:
    return annual_cost(pd.DataFrame([{**BLANK, **answers}]), T).iloc[0]


def test_no_care_costs_nothing():
    assert cost()["cost"] == 0


def test_four_week_visits_are_scaled_to_a_year():
    c = cost(N48="1", N49=2, N51=1)
    assert c["gp"] == 2 * 13 * 65
    assert c["specialist"] == 1 * 13 * 119


def test_emergency_price_depends_on_where():
    assert cost(O79=2, O83="1")["emergency"] == 2 * 257     # public hospital
    assert cost(O79=2, O83="3")["emergency"] == 2 * 257     # private hospital
    assert cost(O79=2, O83="2")["emergency"] == 2 * 88      # non-hospital service


def test_hospital_nights_and_same_day_admissions():
    assert cost(O67=1, O68=4)["inpatient"] == 4 * 1278
    assert cost(O67=2, O68=0)["inpatient"] == 2 * 346


def test_tests_are_priced_once_each():
    c = cost(N59="1", N60_2="1", N60_4="1")
    assert c["tests"] == (34 + 5) + 182 + 151


def test_dont_know_codes_make_the_year_unknown_not_zero():
    assert np.isnan(cost(O68=998)["cost"])
    assert np.isnan(cost(N48="1", N49=98)["cost"])


def test_tariff_file_matches_the_prices_used_here():
    assert (T["gp_visit"], T["specialist_visit"], T["hospital_night"]) == (65, 119, 1278)


def test_readme_worked_example():
    # README: 2 GP visits in 4 weeks, 1 hospital emergency, 3 nights in hospital.
    c = cost(N48="1", N49=2, O79=1, O83="1", O67=1, O68=3)
    assert c["cost"] == 1690 + 257 + 3834 == 5781
