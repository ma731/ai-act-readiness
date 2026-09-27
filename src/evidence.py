"""Evidence for the Tarifa Salud FRIA and gap assessment: what the price does to people.

The fairness question for a price is not "do groups pay the same?" (they should not, if
their risk differs) but "does each group pay for its own cost?". So the headline metric is
relative price-to-cost: a group's predicted cost over its actual cost, divided by the same
ratio for everyone. 1.0 is a fair share; 1.3 means the group pays 30% more per euro of care
it uses than the book as a whole. Dividing by the book's ratio stops a model that is a few
percent off overall from making every group look over- or undercharged.

Every person gets an out-of-sample price from 5-fold cross-fitting, so the whole cohort is
evidence rather than a small hold-out.

Intervals come from a bootstrap that resamples people within each region (the survey is
stratified by region). The public file does not include the census sections the sample
was drawn from, so the clustering inside a region cannot be reproduced and the intervals
are somewhat narrower than a full design-based estimate would give.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict

from src import pricing as P

N_BOOT = 400
N_FOLDS = 5
TOLERANCE = (0.8, 1.25)   # price-to-cost band; see docs/decisions/0002
GROUPINGS = {"born": "Country of birth", "sex": "Sex"}
UNMET = {"unmet_waiting_list": "Went without care because of waiting lists",
         "unmet_transport": "Went without care because of transport",
         "unmet_cost": "Went without medical care because of cost"}
BASE_LEVELS = {"age_band": "35-44", "region": "Madrid", "self_rated_health": "good",
               "smoker": "never", "bmi": "normal"}


def _ratio(num: np.ndarray, den: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(num * w) / np.sum(den * w))


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


def group_table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    tot_w = df.weight.sum()
    book = _ratio(df.pred.values, df.cost.values, df.weight.values)
    avg_pred = np.average(df.pred, weights=df.weight)
    avg_cost = np.average(df.cost, weights=df.weight)
    rows = []
    for g, d in df.groupby(by):
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


def _resample(df: pd.DataFrame, rng) -> pd.DataFrame:
    idx = [rng.choice(ix, len(ix)) for ix in df.groupby("stratum").indices.values()]
    return df.iloc[np.concatenate(idx)]


def bootstrap(df: pd.DataFrame, by: str, n_boot: int = N_BOOT, seed: int = P.SEED) -> dict:
    rng = np.random.default_rng(seed)
    metrics = ["price_to_cost", "decline_rate", "refer_rate"]
    draws = {m: [] for m in metrics}
    for _ in range(n_boot):
        t = group_table(_resample(df, rng), by)
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


def groups_with_ci(df: pd.DataFrame, by: str) -> list[dict]:
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
    return rows


def unmet_need(df: pd.DataFrame, by: str = "born", n_boot: int = N_BOOT,
               seed: int = P.SEED) -> list[dict]:
    """Share who went without care they needed, by group. Tells lower use apart from
    lower need: if a group uses less care but also goes without more often, low use is
    not low need."""
    rng = np.random.default_rng(seed)

    def rates(d):
        out = {}
        for g, x in d.groupby(by):
            w = x.weight.to_numpy()
            for col in UNMET:
                v = x[col].to_numpy()
                ok = ~np.isnan(v)
                out[(g, col)] = np.average(v[ok], weights=w[ok])
        return pd.Series(out)

    point = rates(df)
    boot = pd.concat([rates(_resample(df, rng)) for _ in range(n_boot)], axis=1)
    lo, hi = boot.quantile(0.025, axis=1), boot.quantile(0.975, axis=1)
    return [{"group": g, "measure": col, "label": UNMET[col], "rate": point[(g, col)],
             "ci": [lo[(g, col)], hi[(g, col)]]} for (g, col) in point.index]


def sex_counterfactual(df: pd.DataFrame, unisex_pred: np.ndarray) -> dict:
    """What the unisex rule costs and protects: the same GLM with sex as a factor."""
    with_sex, _ = cross_fit(df, P.fit_glm, P.RATING_FACTORS + ["sex"])
    f = (df.sex == "Female").values
    w = df.weight.values

    def fm(x):
        return float(np.average(x[f], weights=w[f]) / np.average(x[~f], weights=w[~f]))

    proba = cross_val_predict(LogisticRegression(max_iter=3000), P.design(df), f,
                              cv=N_FOLDS, method="predict_proba")[:, 1]
    return {
        "female_to_male_premium_unisex": fm(unisex_pred),
        "female_to_male_premium_if_sex_were_used": fm(with_sex),
        "female_to_male_actual_cost": fm(df.cost.values),
        "sex_recoverable_from_rating_factors_auc": float(roc_auc_score(f, proba,
                                                                       sample_weight=w)),
    }


CLASS_LABELS = {"1": "1 Managers of large firms, professionals",
                "2": "2 Managers of small firms, associate professionals",
                "3": "3 Intermediate occupations, self-employed",
                "4": "4 Supervisors, skilled technical workers",
                "5": "5 Skilled primary sector, semi-skilled workers",
                "6": "6 Unskilled workers"}


def health_by_class(df: pd.DataFrame) -> list[dict]:
    """Share rating their health fair or worse, by the household's social class (INE's
    occupational scale), age-standardised to the cohort's age mix, since lower classes
    are older on average."""
    d = df[df.social_class.notna()].assign(
        poor=df.self_rated_health.isin(["fair", "bad", "very_bad"]).astype(float))
    ages = d.groupby("age_band").weight.sum() / d.weight.sum()
    out = []
    for c, x in d.groupby("social_class"):
        by_age = x.groupby("age_band").apply(lambda a: np.average(a.poor, weights=a.weight))
        out.append({"social_class": CLASS_LABELS[c], "n": len(x),
                    "fair_or_worse_age_standardised": float((by_age * ages).sum())})
    return out


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
    df = P.load_cohort().copy()
    df["pred"], df["route"] = cross_fit(df)
    gbm_pred, _ = cross_fit(df, P.fit_gbm)
    w = df.weight.values
    full, cols = P.fit_glm(df)
    parts = ["gp", "specialist", "emergency", "inpatient", "day_hospital", "tests"]

    private = df[df.private_cover == 1]
    n_cond = df[list(P.CONDITIONS.values())].sum(axis=1)
    age_profile = [{"age_band": a, "n": len(d),
                    "mean_cost_eur": float(np.average(d.cost, weights=d.weight)),
                    "mean_conditions": float(np.average(n_cond[d.index], weights=d.weight)),
                    "fair_or_worse_health": float(np.average(
                        d.self_rated_health.isin(["fair", "bad", "very_bad"]),
                        weights=d.weight))}
                   for a, d in df.groupby("age_band")]
    return {
        "data": {
            "source": "INE, Encuesta Europea de Salud en España 2020 (fieldwork 15 Jul 2019 "
                      "to 24 Jul 2020)",
            "prices": "Osakidetza, Tarifas 2024 (data/tariffs_osakidetza_2024.yaml)",
            "cohort": "adults 18-64 with complete questionnaire and use answers",
            "people": len(df),
            "represents_millions": float(df.weight.sum()) / 1e6,
            "born_abroad": int((df.born == "Born abroad").sum()),
            "with_private_cover": len(private),
            "mean_annual_cost_eur": float(np.average(df.cost, weights=w)),
            "median_annual_cost_eur": float(df.cost.median()),
            "share_with_no_care": float(np.average(df.cost == 0, weights=w)),
            "cost_breakdown_eur": {p: float(np.average(df[p], weights=w)) for p in parts},
            "age_profile": age_profile,
        },
        "model": {
            "primary": "Poisson GLM (log link), survey-weighted",
            "validation": f"{N_FOLDS}-fold cross-fitting",
            "gini_glm": P.gini(df.cost.values, df.pred.values, w),
            "gini_gbm_challenger": P.gini(df.cost.values, gbm_pred, w),
            "book_price_to_cost": _ratio(df.pred.values, df.cost.values, w),
            "decline_share_target": P.DECLINE_SHARE, "refer_share_target": P.REFER_SHARE,
            "base_levels": BASE_LEVELS,
            "relativities": relativities(full, cols),
        },
        "tolerance_price_to_cost": list(TOLERANCE),
        "groups": {by: groups_with_ci(df, by) for by in GROUPINGS},
        "private_cover_only": {"people": len(private),
                               "born": groups_with_ci(private, "born")},
        "unmet_need": unmet_need(df),
        "self_rated_health_by_class": health_by_class(df),
        "sex_counterfactual": sex_counterfactual(df, df.pred.values),
        "bootstrap": {"replicates": N_BOOT,
                      "design": "people resampled within region (CCAA)"},
    }
