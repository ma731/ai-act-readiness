"""Evidence for the Tarifa Salud FRIA and gap assessment: what the price does to people.

The fairness question for a price is not "do groups pay the same?" (they should not, if
their risk differs) but "does each group pay for its own cost?". So the headline metric is
relative price-to-cost: a group's predicted cost over its actual cost, divided by the same
ratio for everyone. 1.0 is a fair share; 1.5 means the group pays 50% more per euro of
claims than the book as a whole. Dividing by the book's ratio keeps a model that is a few
percent low overall from making every group look undercharged.

Every person gets an out-of-sample price from 5-fold cross-fitting (households kept
within a fold), so the whole cohort is evidence rather than a 30% hold-out.

Intervals come from a survey-design bootstrap: MEPS is a clustered sample, so PSUs are
resampled within strata, not people. Predictions are held fixed, so the intervals cover
sampling noise, not refitting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from src import pricing as P

N_BOOT = 400
TOLERANCE = (0.8, 1.25)   # price-to-cost band; see docs/decisions/0002


def _ratio(num: np.ndarray, den: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(num * w) / np.sum(den * w))


N_FOLDS = 5


def cross_fit(df: pd.DataFrame, fitter=P.fit_glm, factors: list[str] = P.RATING_FACTORS):
    """Out-of-fold predictions and routes for every person."""
    pred = np.zeros(len(df))
    routes = np.empty(len(df), dtype=object)
    folds = GroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=P.SEED)
    for trn, val in folds.split(df, groups=df.household):
        tr, va = df.iloc[trn], df.iloc[val]
        m, cols = fitter(tr, factors)
        pred[val] = P.predict(m, cols, va, factors)
        refer, decline = P.routing_thresholds(P.predict(m, cols, tr, factors),
                                              tr.weight.values)
        routes[val] = P.route(pred[val], refer, decline)
    return pred, routes


def group_table(te: pd.DataFrame, by: str) -> pd.DataFrame:
    tot_w = te.weight.sum()
    book = _ratio(te.pred.values, te.cost.values, te.weight.values)
    avg_pred = np.average(te.pred, weights=te.weight)
    avg_cost = np.average(te.cost, weights=te.weight)
    rows = []
    for g, d in te.groupby(by):
        w = d.weight.values
        rows.append({
            "group": g, "n": len(d), "population_share": w.sum() / tot_w,
            "premium_index": np.average(d.pred, weights=w) / avg_pred,
            "cost_index": np.average(d.cost, weights=w) / avg_cost,
            "price_to_cost": _ratio(d.pred.values, d.cost.values, w) / book,
            "decline_rate": np.average(d.route == "decline", weights=w),
            "refer_rate": np.average(d.route == "refer", weights=w),
        })
    return pd.DataFrame(rows).set_index("group")


def bootstrap(te: pd.DataFrame, by: str, n_boot: int = N_BOOT, seed: int = P.SEED) -> dict:
    rng = np.random.default_rng(seed)
    clusters = te.groupby(["stratum", "psu"]).indices
    by_stratum: dict[int, list[np.ndarray]] = {}
    for (s, _), idx in clusters.items():
        by_stratum.setdefault(s, []).append(idx)
    metrics = ["price_to_cost", "decline_rate", "refer_rate"]
    draws = {m: [] for m in metrics}
    for _ in range(n_boot):
        parts = []
        for psus in by_stratum.values():
            pick = rng.integers(0, len(psus), len(psus))
            parts.extend(psus[i] for i in pick)
        t = group_table(te.iloc[np.concatenate(parts)], by)
        for m in metrics:
            draws[m].append(t[m])
    return {m: pd.concat(v, axis=1).quantile([0.025, 0.975], axis=1).T
            for m, v in draws.items()}


def verdict(lo: float, hi: float, band: tuple[float, float] = TOLERANCE) -> str:
    if lo > band[1]:
        return "overcharged"
    if hi < band[0]:
        return "undercharged"
    if hi < band[1] and lo > band[0]:
        return "within tolerance"
    return "inconclusive"


def sex_counterfactual(df: pd.DataFrame, unisex_pred: np.ndarray) -> dict:
    """What the unisex rule costs and protects: the same GLM with sex as a factor."""
    with_sex, _ = cross_fit(df, P.fit_glm, P.RATING_FACTORS + ["sex"])
    tr, te = P.split(df)
    f = (df.sex == "Female").values
    w = df.weight.values

    def fm(x):
        return float(np.average(x[f], weights=w[f]) / np.average(x[~f], weights=w[~f]))

    x_tr = P.design(tr)
    clf = LogisticRegression(max_iter=3000).fit(x_tr, tr.sex == "Female")
    auc = roc_auc_score(te.sex == "Female",
                        clf.predict_proba(P.design(te, columns=x_tr.columns))[:, 1],
                        sample_weight=te.weight.values)
    return {
        "female_to_male_premium_unisex": fm(unisex_pred),
        "female_to_male_premium_if_sex_were_used": fm(with_sex),
        "female_to_male_actual_cost": fm(df.cost.values),
        "sex_recoverable_from_rating_factors_auc": float(auc),
    }


BASE_LEVELS = {"age_band": "35-44", "region": "South", "self_rated_health": "good",
               "smoker": "no"}


def relativities(model, cols) -> dict:
    """GLM factors as multipliers against a stated base level, the way a rate filing shows
    them. Binary conditions are against not having the condition."""
    raw = dict(zip(cols, np.exp(model.coef_), strict=True))
    out = {}
    for col, v in raw.items():
        factor = next((f for f in BASE_LEVELS if col.startswith(f + "_")), None)
        out[col] = v / raw[f"{factor}_{BASE_LEVELS[factor]}"] if factor else v
    return out


def run() -> dict:
    df = P.load_cohort()
    df = df.copy()
    df["pred"], df["route"] = cross_fit(df)
    gbm_pred, _ = cross_fit(df, P.fit_gbm)
    w = df.weight.values

    groups = {}
    for by in ["ethnicity", "sex"]:
        t = group_table(df, by)
        ci = bootstrap(df, by)
        rows = []
        for g, r in t.iterrows():
            lo, hi = ci["price_to_cost"].loc[g]
            rows.append({
                "group": g, "n": int(r.n), "population_share": r.population_share,
                "premium_index": r.premium_index, "cost_index": r.cost_index,
                "price_to_cost": r.price_to_cost, "price_to_cost_ci": [lo, hi],
                "verdict": verdict(lo, hi),
                "decline_rate": r.decline_rate,
                "decline_rate_ci": list(ci["decline_rate"].loc[g]),
                "refer_rate": r.refer_rate, "refer_rate_ci": list(ci["refer_rate"].loc[g]),
            })
        groups[by] = rows

    full, cols = P.fit_glm(df)
    return {
        "data": {
            "source": "MEPS HC-243, 2022 Full Year Consolidated (AHRQ)",
            "cohort": "adults 18-64 with any private cover, questionnaire answered",
            "people": len(df),
            "represents_millions": float(df.weight.sum()) / 1e6,
        },
        "model": {
            "primary": "Tweedie GLM (power 1.6, log link), survey-weighted",
            "validation": f"{N_FOLDS}-fold cross-fitting, households kept within a fold",
            "gini_glm": P.gini(df.cost.values, df.pred.values, w),
            "gini_gbm_challenger": P.gini(df.cost.values, gbm_pred, w),
            "book_price_to_cost": _ratio(df.pred.values, df.cost.values, w),
            "decline_share_target": P.DECLINE_SHARE, "refer_share_target": P.REFER_SHARE,
            "base_levels": BASE_LEVELS,
            "relativities": relativities(full, cols),
        },
        "tolerance_price_to_cost": list(TOLERANCE),
        "groups": groups,
        "sex_counterfactual": sex_counterfactual(df, df.pred.values),
        "bootstrap": {"replicates": N_BOOT, "design": "PSUs resampled within strata"},
    }
