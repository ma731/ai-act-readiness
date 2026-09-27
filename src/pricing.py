"""A stand-in for Tarifa Salud (S1), fitted on real US survey data.

No public Spanish dataset links a health questionnaire to what each person later costs, so
this uses MEPS 2022 (AHRQ): 22,431 people with their diagnosed conditions and their actual
health spending that year. The cohort is adults 18-64 with private cover, the population a
private health insurer prices. US regions stand in for Spanish provinces.

Inputs are what an application questionnaire asks. Sex and ethnicity are not inputs: sex
because Directive 2004/113 forbids it in premiums, ethnicity because nobody would ask it.
They are kept aside only to test what the model does to those groups.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import TweedieRegressor
from sklearn.model_selection import GroupShuffleSplit

RAW = Path(__file__).parents[1] / "data" / "raw" / "h243.dta"

CONDITIONS = {
    "HIBPDX": "high_blood_pressure", "CHDDX": "coronary_heart_disease", "STRKDX": "stroke",
    "EMPHDX": "emphysema", "CHOLDX": "high_cholesterol", "CANCERDX": "cancer",
    "DIABDX_M18": "diabetes", "ARTHDX": "arthritis", "ASTHDX": "asthma",
}
RACE = {1: "Hispanic", 2: "White", 3: "Black", 4: "Asian", 5: "Other or multiple"}
SEX = {1: "Male", 2: "Female"}
REGION = {1: "Northeast", 2: "Midwest", 3: "South", 4: "West"}
HEALTH = {1: "excellent", 2: "very_good", 3: "good", 4: "fair", 5: "poor"}
AGE_BANDS = [18, 25, 35, 45, 55, 65]

# Share of applications each route takes, set on the training book.
DECLINE_SHARE = 0.02
REFER_SHARE = 0.08
SEED = 20260927


def load_cohort(path: Path = RAW) -> pd.DataFrame:
    cols = ["DUPERSID", "AGE22X", "SEX", "RACETHX", "REGION22", "RTHLTH53", "OFTSMK53",
            "INSCOV22", "TOTEXP22", "PERWT22F", "VARSTR", "VARPSU", *CONDITIONS]
    df = pd.read_stata(path, columns=cols, convert_categoricals=False)
    df = df[(df.AGE22X.between(18, 64)) & (df.INSCOV22 == 1) & (df.PERWT22F > 0)
            & (df.REGION22 > 0)].copy()

    out = pd.DataFrame(index=df.index)
    out["age"] = df.AGE22X.astype(int)
    out["age_band"] = pd.cut(out.age, AGE_BANDS, right=False,
                             labels=["18-24", "25-34", "35-44", "45-54", "55-64"]).astype(str)
    out["region"] = df.REGION22.map(REGION)
    out["self_rated_health"] = df.RTHLTH53.map(HEALTH)
    out["smoker"] = df.OFTSMK53.map({1: "yes", 2: "yes", 3: "no"})
    for code, name in CONDITIONS.items():
        out[name] = (df[code] == 1).astype(int)
    out["cost"] = df.TOTEXP22.astype(float)
    out["weight"] = df.PERWT22F.astype(float)
    out["sex"] = df.SEX.map(SEX)
    out["ethnicity"] = df.RACETHX.map(RACE)
    out["household"] = df.DUPERSID.astype(str).str[:-3]
    out["stratum"] = df.VARSTR.astype(int)
    out["psu"] = df.VARPSU.astype(int)
    # An applicant cannot skip the questionnaire. In the survey, skipping the round 5
    # questions tracks hospitalisation or death, and was worth a 3.2x cost relativity:
    # a leak, not a rating factor.
    answered = out.self_rated_health.notna() & out.smoker.notna()
    return out[answered].reset_index(drop=True)


RATING_FACTORS = ["age_band", "region", "self_rated_health", "smoker", *CONDITIONS.values()]


def design(df: pd.DataFrame, factors: list[str] = RATING_FACTORS,
           columns: pd.Index | None = None) -> pd.DataFrame:
    cats = [f for f in factors if not pd.api.types.is_numeric_dtype(df[f])]
    x = pd.get_dummies(df[factors], columns=cats,
                       drop_first=False, dtype=float)
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0.0)
    return x


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Households stay on one side: relatives share habits and insurers.
    gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=SEED)
    tr, te = next(gss.split(df, groups=df.household))
    return df.iloc[tr].reset_index(drop=True), df.iloc[te].reset_index(drop=True)


def fit_glm(train: pd.DataFrame, factors: list[str] = RATING_FACTORS):
    x = design(train, factors)
    # Tweedie with log link: the standard pure-premium GLM (many zeros, long right tail).
    m = TweedieRegressor(power=1.6, link="log", alpha=1e-3, max_iter=3000)
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
