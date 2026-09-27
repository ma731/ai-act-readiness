"""A stand-in for Tarifa Salud (S1), built on Spanish data only.

People: INE's Encuesta Europea de Salud en España 2020 (EESE), 22,072 adults with their health
questionnaire answers and how much health care they used. Adults 18 to 64 are kept: the ages a
private health insurer sells individual cover to.

Money: the survey records use, not cost. Each person's use is priced with the Basque public
health service's 2024 tariff (data/tariffs_osakidetza_2024.yaml), the prices it bills to
insurers and other third parties. That gives each person an annual cost in euros.

Inputs to the price are what an application questionnaire asks. Sex and country of birth are
not inputs: sex because Directive 2004/113 forbids it in premiums, country of birth because
it is not a rating factor. They are kept aside only to test what the price does to those
groups.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import TweedieRegressor

ROOT = Path(__file__).parents[1]
RAW = ROOT / "data" / "raw" / "eese" / "STATA" / "EESEadulto_2020.dta"
TARIFFS = ROOT / "data" / "tariffs_osakidetza_2024.yaml"

# Doctor-diagnosed conditions (EESE G25c: "le ha dicho un médico").
CONDITIONS = {
    "1": "hypertension", "2": "heart_attack", "3": "coronary_disease", "4": "other_heart",
    "6": "osteoarthritis", "8": "chronic_low_back_pain", "10": "asthma", "11": "copd",
    "12": "diabetes", "15": "high_cholesterol", "20": "depression", "21": "chronic_anxiety",
    "23": "stroke", "26": "cancer", "29": "kidney_disease",
}
HEALTH = {"1": "very_good", "2": "good", "3": "fair", "4": "bad", "5": "very_bad"}
SMOKING = {"1": "daily", "2": "occasional", "3": "former", "4": "never"}
BMI = {"1": "underweight", "2": "normal", "3": "overweight", "4": "obese", "9": "not_measured"}
CCAA = {
    "01": "Andalucia", "02": "Aragon", "03": "Asturias", "04": "Baleares", "05": "Canarias",
    "06": "Cantabria", "07": "Castilla y Leon", "08": "Castilla-La Mancha", "09": "Cataluna",
    "10": "C. Valenciana", "11": "Extremadura", "12": "Galicia", "13": "Madrid",
    "14": "Murcia", "15": "Navarra", "16": "Pais Vasco", "17": "La Rioja", "18": "Ceuta",
    "19": "Melilla",
}
AGE_BANDS = [18, 25, 35, 45, 55, 65]
WEEKS_PER_4_WEEKS = 13        # visit counts cover the last four weeks; 52 / 4 = 13

DECLINE_SHARE = 0.02
REFER_SHARE = 0.08
SEED = 20260927


def _num(s: pd.Series, missing_from: int) -> pd.Series:
    """Survey counts, with its 'don't know / no answer' codes (98, 99, 998...) as missing."""
    x = pd.to_numeric(s, errors="coerce")
    return x.where(x < missing_from)


def _yes(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.strip() == "1").astype(int)


def tariffs() -> dict[str, float]:
    spec = yaml.safe_load(TARIFFS.read_text(encoding="utf-8"))
    return {k: float(v["eur"]) for k, v in spec["prices"].items()}


def annual_cost(df: pd.DataFrame, t: dict[str, float] | None = None) -> pd.DataFrame:
    """Price one year of each person's care at the Osakidetza 2024 tariff.

    Covered: GP and specialist visits, emergencies, hospital nights, day hospital, CT, MRI,
    ultrasound, X-ray and lab tests. Not covered, on purpose:
      - prescriptions: standard Spanish private health policies do not pay for them
      - dental: sold as a separate product
      - physiotherapy and psychology: the survey records yes/no, not how many sessions
      - childbirth: the survey's hospital questions exclude it, and Directive 2004/113
        Art 5(3) forbids maternity costs from changing premiums anyway
    """
    t = t or tariffs()
    gp = _num(df.N49, 98).fillna(0) * WEEKS_PER_4_WEEKS * t["gp_visit"]
    spec = _num(df.N51, 98).fillna(0) * WEEKS_PER_4_WEEKS * t["specialist_visit"]
    hospital_er = df.O83.astype(str).str.strip().isin(["1", "3"])
    er_price = np.where(hospital_er, t["emergency_hospital"], t["emergency_primary_care"])
    er = _num(df.O79, 998).fillna(0) * er_price
    nights = _num(df.O68, 998).fillna(0)
    admissions = _num(df.O67, 98).fillna(0)
    inpatient = nights * t["hospital_night"] + np.where(
        (admissions > 0) & (nights == 0), admissions * t["admission_without_night"], 0)
    day_hosp = _num(df.O76, 998).fillna(0) * t["day_hospital_session"]
    tests = (_yes(df.N60_1) * t["x_ray"] + _yes(df.N60_2) * t["ct_scan"]
             + _yes(df.N60_3) * t["ultrasound"] + _yes(df.N60_4) * t["mri_scan"]
             + _yes(df.N59) * (t["lab_profile"] + t["lab_order_handling"]))
    parts = pd.DataFrame({"gp": gp, "specialist": spec, "emergency": er,
                          "inpatient": inpatient, "day_hospital": day_hosp, "tests": tests})
    parts["cost"] = parts.sum(axis=1)
    # A count the respondent could not give makes the whole year unknown, not zero.
    unknown = pd.Series(False, index=df.index)
    for col, code in {"N49": 98, "N51": 98, "O67": 98, "O68": 998, "O76": 998,
                      "O79": 998}.items():
        unknown |= pd.to_numeric(df[col], errors="coerce").ge(code)
    parts.loc[unknown, "cost"] = np.nan
    return parts


def load_cohort(path: Path = RAW) -> pd.DataFrame:
    df = pd.read_stata(path, convert_categoricals=False)
    df["age"] = pd.to_numeric(df.EDADa)
    df = df[df.age.between(18, 64)].copy()

    out = pd.DataFrame(index=df.index)
    out["age"] = df.age.astype(int)
    out["age_band"] = pd.cut(out.age, AGE_BANDS, right=False,
                             labels=["18-24", "25-34", "35-44", "45-54", "55-64"]).astype(str)
    out["region"] = df.CCAA.astype(str).str.zfill(2).map(CCAA)
    out["self_rated_health"] = df.G21.astype(str).str.strip().map(HEALTH)
    out["smoker"] = df.V121.astype(str).str.strip().map(SMOKING)
    out["bmi"] = df.IMC.astype(str).str.strip().map(BMI)
    for code, name in CONDITIONS.items():
        out[name] = _yes(df[f"G25c_{code}"])
    costs = annual_cost(df)
    out = out.join(costs)
    out["weight"] = pd.to_numeric(df.FACTORADULTO)
    out["sex"] = df.SEXOa.astype(str).str.strip().map({"1": "Male", "2": "Female"})
    out["born"] = df.E1_1.astype(str).str.strip().map({"1": "Born in Spain",
                                                      "2": "Born abroad"})
    out["private_cover"] = ((_yes(df.O84_3) + _yes(df.O84_4) + _yes(df.O84_5)) > 0).astype(int)
    for code, name in {"R106": "unmet_waiting_list", "R107": "unmet_transport",
                       "R108_1": "unmet_cost"}.items():
        v = df[code].astype(str).str.strip()
        out[name] = np.where(v == "1", 1.0, np.where(v.isin(["2", "3"]), 0.0, np.nan))
    out["social_class"] = df.CLASE_PR.astype(str).str.strip().where(
        lambda c: c.isin(["1", "2", "3", "4", "5", "6"]))
    out["stratum"] = df.CCAA.astype(str)
    out["household"] = df.IDENTHOGAR.astype(str)
    keep = out[RATING_FACTORS + ["cost", "born", "sex"]].notna().all(axis=1)
    return out[keep].reset_index(drop=True)


RATING_FACTORS = ["age_band", "region", "self_rated_health", "smoker", "bmi",
                  *CONDITIONS.values()]


def design(df: pd.DataFrame, factors: list[str] = RATING_FACTORS,
           columns: pd.Index | None = None) -> pd.DataFrame:
    cats = [f for f in factors if not pd.api.types.is_numeric_dtype(df[f])]
    x = pd.get_dummies(df[factors], columns=cats, drop_first=False, dtype=float)
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0.0)
    return x


def fit_glm(train: pd.DataFrame, factors: list[str] = RATING_FACTORS):
    x = design(train, factors)
    # Poisson with log link. Its fitted average matches the observed average for every level
    # of every factor it uses (the balance property), so any gap left between a group's price
    # and its cost comes from what the model does not see. Tweedie 1.6 ranked slightly better
    # but broke that property: given sex, it priced women at 1.43x men against 1.12x in cost.
    m = TweedieRegressor(power=1.0, link="log", alpha=1e-4, max_iter=5000)
    m.fit(x, train.cost, sample_weight=train.weight)
    return m, x.columns


def fit_gbm(train: pd.DataFrame, factors: list[str] = RATING_FACTORS):
    x = design(train, factors)
    m = HistGradientBoostingRegressor(loss="poisson", max_iter=300, learning_rate=0.05,
                                      max_leaf_nodes=15, min_samples_leaf=80,
                                      random_state=SEED)
    m.fit(x, train.cost, sample_weight=train.weight)
    return m, x.columns


def predict(model, columns, df: pd.DataFrame, factors: list[str] = RATING_FACTORS) -> np.ndarray:
    return model.predict(design(df, factors, columns))


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    cw = np.cumsum(weights[order])
    return float(values[order][np.searchsorted(cw, q * cw[-1])])


def routing_thresholds(pred_train: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    decline = weighted_quantile(pred_train, w, 1 - DECLINE_SHARE)
    refer = weighted_quantile(pred_train, w, 1 - DECLINE_SHARE - REFER_SHARE)
    return refer, decline


def route(pred: np.ndarray, refer: float, decline: float) -> np.ndarray:
    return np.where(pred >= decline, "decline", np.where(pred >= refer, "refer", "accept"))


def gini(actual: np.ndarray, pred: np.ndarray, w: np.ndarray) -> float:
    """Normalised weighted Gini: how well the ranking orders actual cost (1 = perfect)."""
    def raw(order_by):
        o = np.argsort(order_by)
        a, ww = actual[o] * w[o], w[o]
        cum_a = np.cumsum(a) / a.sum()
        cum_w = np.cumsum(ww) / ww.sum()
        return float(np.sum(np.diff(np.r_[0, cum_w]) * (np.r_[0, cum_a][:-1] + cum_a)) - 1)
    return raw(-pred) / raw(-actual) if raw(-actual) else float("nan")
