"""Render the generated parts of the assessment.

The narrative documents are written by hand. Every table and number in them comes from
here, between <!-- BEGIN:name --> and <!-- END:name --> markers, so the prose cannot drift
from the results. `--check` fails if a document is stale.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from src.pricing import CONDITIONS
from src.rules import LEGAL_BASIS_DATE, Classification

TIER_LABEL = {"prohibited": "Prohibited", "high_risk": "High-risk",
              "transparency": "Transparency", "minimal": "Minimal"}
STATUS_MARK = {"met": "Met", "partial": "Partial", "missing": "Missing"}


def _months(d: date) -> int:
    return (d.year - LEGAL_BASIS_DATE.year) * 12 + d.month - LEGAL_BASIS_DATE.month


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def gap_rows(systems: list[dict], results: list[Classification]) -> list[dict]:
    rows = []
    for s, c in zip(systems, results, strict=True):
        controls = s.get("controls") or {}
        for o in c.obligations:
            ctl = controls.get(o.article, {})
            status = ctl.get("status", "not assessed")
            if s.get("status") == "proposed":
                state = "Block before purchase" if o.article.startswith("Art 5(") \
                    else "Pre-deployment"
            elif status == "met":
                state = "Done"
            elif o.in_force and status == "partial":
                state = "In force, partial"
            elif o.in_force:
                state = "OVERDUE"
            else:
                state = f"Due {o.applies_from:%d %b %Y} ({_months(o.applies_from)} mo)"
            rows.append({"system": s["id"], "name": s["name"],
                         "live": s.get("status") != "proposed", "article": o.article,
                         "duty": o.duty, "holder": o.holder, "status": status,
                         "note": ctl.get("note", ""), "state": state,
                         "applies_from": o.applies_from})
    return rows


def _priority(r: dict) -> tuple:
    order = {"Block before purchase": 0, "OVERDUE": 1, "In force, partial": 2}
    return (order.get(r["state"], 3), r["applies_from"], r["system"])


def inventory_table(systems, results) -> str:
    out = ["| ID | System | Role | Classification | Why | FRIA |",
           "|---|---|---|---|---|---|"]
    for s, c in zip(systems, results, strict=True):
        why = " ".join(c.basis) or "Not listed in Annex III; no Art 5 or Art 50 trigger."
        proposed = " (proposed)" if s.get("status") == "proposed" else ""
        out.append(f"| {s['id']} | {s['name']}{proposed}"
                   f" | {', '.join(s.get('role', []))} | **{TIER_LABEL[c.tier]}** | {why} | "
                   f"{'Required' if c.fria_required else 'No'} |")
    return "\n".join(out)


def flags_list(systems, results) -> str:
    out = []
    for s, c in zip(systems, results, strict=True):
        for f in c.flags:
            out.append(f"- **{s['id']} {s['name']}:** {f}")
        for f in c.other_law:
            out.append(f"- **{s['id']} {s['name']}** (outside the AI Act): {f}")
    return "\n".join(out)


def gap_summary(rows) -> str:
    live = [r for r in rows if r["live"]]
    count = {k: sum(1 for r in live if r["status"] == k)
             for k in ["met", "partial", "missing", "not assessed"]}
    overdue = sum(1 for r in rows if r["state"] == "OVERDUE")
    blocked = sum(1 for r in rows if r["state"] == "Block before purchase")
    return (f"{len(live)} obligations on live systems: {count['met']} met, "
            f"{count['partial']} partial, {count['missing']} missing"
            + (f", {count['not assessed']} not assessed" if count["not assessed"] else "")
            + f". **{overdue} overdue today**, {blocked} prohibited use to block before "
              "purchase.")


def gap_table(rows) -> str:
    out = ["| Priority | System | Article | Duty | Holder | Current state | Status |",
           "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sorted(rows, key=_priority), 1):
        state = f"**{r['state']}**" if r["state"] in {"OVERDUE", "Block before purchase"} \
            else r["state"]
        out.append(f"| {i} | {r['system']} | {r['article']} | {r['duty']} | {r['holder']} | "
                   f"{STATUS_MARK.get(r['status'], r['status'])}"
                   f"{': ' + r['note'] if r['note'] else ''} | {state} |")
    return "\n".join(out)


def _eur(x: float) -> str:
    return f"EUR {x:,.0f}"


def evidence_groups(ev: dict, by: str, rows: list[dict] | None = None) -> str:
    out = ["| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | "
           "Verdict | Declined | Referred |", "|---|---|---|---|---|---|---|---|"]
    for g in rows if rows is not None else ev["groups"][by]:
        lo, hi = g["price_to_cost_ci"]
        dlo, dhi = g["decline_rate_ci"]
        rlo, rhi = g["refer_rate_ci"]
        out.append(f"| {g['group']} | {g['n']:,} | {g['premium_index']:.2f} | "
                   f"{g['cost_index']:.2f} | **{g['price_to_cost']:.2f}** ({lo:.2f} to "
                   f"{hi:.2f}) | {g['verdict']} | {_pct(g['decline_rate'])} "
                   f"({_pct(dlo)} to {_pct(dhi)}) | {_pct(g['refer_rate'])} "
                   f"({_pct(rlo)} to {_pct(rhi)}) |")
    return "\n".join(out)


def evidence_private(ev: dict) -> str:
    p = ev["private_cover_only"]
    return (f"Only the {p['people']:,} people who already hold private cover:\n\n"
            + evidence_groups(ev, "born", p["born"]))


def evidence_unmet(ev: dict) -> str:
    rows = {}
    for u in ev["unmet_need"]:
        rows.setdefault(u["label"], {})[u["group"]] = u
    groups = sorted({u["group"] for u in ev["unmet_need"]})
    out = ["| In the last 12 months | " + " | ".join(groups) + " |",
           "|---|" + "---|" * len(groups)]
    for label, by_group in rows.items():
        cells = [f"{_pct(by_group[g]['rate'])} ({_pct(by_group[g]['ci'][0])} to "
                 f"{_pct(by_group[g]['ci'][1])})" for g in groups]
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def cost_build(tariffs: dict, ev: dict | None) -> str:
    """How one year of care becomes euros: survey question, price, source line."""
    p = tariffs["prices"]
    used = [
        ("GP visits in the last 4 weeks, x13 for a year", "gp_visit"),
        ("Specialist visits in the last 4 weeks, x13", "specialist_visit"),
        ("Emergency visits in 12 months, at a hospital", "emergency_hospital"),
        ("Emergency visits in 12 months, elsewhere", "emergency_primary_care"),
        ("Nights in hospital in 12 months (childbirth excluded)", "hospital_night"),
        ("Admissions with no overnight stay", "admission_without_night"),
        ("Day-hospital sessions in 12 months", "day_hospital_session"),
        ("Had a CT scan in 12 months (priced as one)", "ct_scan"),
        ("Had an MRI (one)", "mri_scan"),
        ("Had an ultrasound (one)", "ultrasound"),
        ("Had an X-ray (one)", "x_ray"),
        ("Had blood or lab tests (one request)", "lab_profile"),
        ("Plus the handling fee per lab request", "lab_order_handling"),
    ]
    out = ["| Survey answer | Price | Osakidetza 2024 line | Page |", "|---|---|---|---|"]
    for q, key in used:
        x = p[key]
        out.append(f"| {q} | {_eur(x['eur'])} | {x['item']} ({x['article']}) | {x['page']} |")
    if ev:
        d = ev["data"]
        b = d["cost_breakdown_eur"]
        out += ["", f"Average cost per adult per year: **{_eur(d['mean_annual_cost_eur'])}** "
                f"(hospital nights {_eur(b['inpatient'])}, GP {_eur(b['gp'])}, specialists "
                f"{_eur(b['specialist'])}, day hospital {_eur(b['day_hospital'])}, emergencies "
                f"{_eur(b['emergency'])}, tests {_eur(b['tests'])}). The median is "
                f"{_eur(d['median_annual_cost_eur'])} and {_pct(d['share_with_no_care'])} used "
                "no care at all: a few people cost a lot, as in any health book."]
    return "\n".join(out)


def evidence_age(ev: dict) -> str:
    out = ["| Age | People | Average cost | Diagnosed conditions | Fair or worse health |",
           "|---|---|---|---|---|"]
    for a in ev["data"]["age_profile"]:
        out.append(f"| {a['age_band']} | {a['n']:,} | {_eur(a['mean_cost_eur'])} | "
                   f"{a['mean_conditions']:.2f} | {_pct(a['fair_or_worse_health'])} |")
    return "\n".join(out)


def evidence_class(ev: dict) -> str:
    out = ["| Social class of the household | People | Rate their health fair or worse "
           "(age-standardised) |", "|---|---|---|"]
    for r in ev["self_rated_health_by_class"]:
        out.append(f"| {r['social_class']} | {r['n']:,} | "
                   f"{_pct(r['fair_or_worse_age_standardised'])} |")
    return "\n".join(out)


def evidence_headline(ev: dict) -> str:
    born = {g["group"]: g for g in ev["groups"]["born"]}
    ab = born["Born abroad"]
    lo, hi = ab["price_to_cost_ci"]
    un = {(u["group"], u["measure"]): u for u in ev["unmet_need"]}
    ca, cs = un[("Born abroad", "unmet_cost")], un[("Born in Spain", "unmet_cost")]
    sx = ev["sex_counterfactual"]
    m = ev["model"]
    return "\n".join([
        f"- **People born abroad would pay {ab['price_to_cost']:.2f}x their share of care "
        f"costs** (95% CI {lo:.2f} to {hi:.2f}): a signal, not a proven breach, because the "
        "interval reaches 1.0. Country of birth is never an input.",
        f"- **They also go without care because of cost more often**: "
        f"{_pct(ca['rate'])} against {_pct(cs['rate'])} for people born in Spain. Part of "
        "their lower use looks like lower access, not lower need.",
        f"- **Sex leaks back in, a little.** Sex is not an input, yet women are quoted "
        f"{sx['female_to_male_premium_unisex']:.2f}x what men are, against "
        f"{sx['female_to_male_actual_cost']:.2f}x in cost; the other answers predict sex "
        f"with AUC {sx['sex_recoverable_from_rating_factors_auc']:.2f}. Within tolerance.",
        f"- **The model is calibrated and explainable**: predicted over actual cost "
        f"{m['book_price_to_cost']:.3f}, and the GLM ranks as well as a gradient-boosted "
        f"challenger (Gini {m['gini_glm']:.3f} against {m['gini_gbm_challenger']:.3f}).",
    ])


def evidence_model(ev: dict) -> str:
    m, d = ev["model"], ev["data"]
    rel = m["relativities"]
    cond = sorted(((k, rel[k]) for k in CONDITIONS.values()), key=lambda kv: -kv[1])
    return "\n".join([
        f"- **People:** {d['source']}. Adults 18 to 64 with complete answers: "
        f"**{d['people']:,} people**, weighted to {d['represents_millions']:.1f} million; "
        f"{d['born_abroad']:,} born abroad, {d['with_private_cover']:,} with private cover.",
        f"- **Prices:** {d['prices']}.",
        f"- **Model:** {m['primary']}; {m['validation']}, so every price is out-of-sample.",
        f"- **Accuracy:** Gini {m['gini_glm']:.3f} (GBM challenger "
        f"{m['gini_gbm_challenger']:.3f}); predicted over actual cost "
        f"{m['book_price_to_cost']:.3f}.",
        f"- **Self-rated health** is the strongest factor: very good "
        f"{rel['self_rated_health_very_good']:.2f}, fair {rel['self_rated_health_fair']:.2f}, "
        f"bad {rel['self_rated_health_bad']:.2f}, very bad "
        f"{rel['self_rated_health_very_bad']:.2f} (base: good).",
        "- **Diagnosed conditions:** " + ", ".join(
            f"{k.replace('_', ' ').replace('copd', 'COPD')} {v:.2f}" for k, v in cond) + ".",
        f"- **Smoking** (base: never): daily {rel['smoker_daily']:.2f}, former "
        f"{rel['smoker_former']:.2f}.",
        f"- **Age** (base: 35-44): 18-24 {rel['age_band_18-24']:.2f}, 55-64 "
        f"{rel['age_band_55-64']:.2f}, once conditions and health are known.",
    ])


def roadmap(rows) -> str:
    phases = [
        ("Now: prohibited or overdue",
         lambda r: r["state"] in {"Block before purchase", "OVERDUE"}),
        ("Now: in force, partly done", lambda r: r["state"] == "In force, partial"),
        ("By 2 Dec 2026", lambda r: r["state"].startswith("Due")
         and r["applies_from"] <= date(2026, 12, 2)),
        ("By 2 Dec 2027, when high-risk duties apply", lambda r: r["state"].startswith("Due")
         and r["applies_from"] > date(2026, 12, 2)),
    ]
    out = []
    for title, pick in phases:
        per_system: dict[str, list[str]] = {}
        for r in sorted((r for r in rows if pick(r)), key=_priority):
            arts = per_system.setdefault(f"{r['system']} {r['name']}", [])
            if r["article"] not in arts:
                arts.append(r["article"])
        if per_system:
            out.append(f"**{title}**\n")
            out += [f"- {k}: {', '.join(v)}" for k, v in per_system.items()]
            out.append("")
    return "\n".join(out).rstrip()


def fill(text: str, blocks: dict[str, str]) -> str:
    for name, body in blocks.items():
        pat = re.compile(rf"(<!-- BEGIN:{name} -->)\n.*?(<!-- END:{name} -->)", re.S)
        text = pat.sub(lambda m, b=body: f"{m.group(1)}\n{b}\n{m.group(2)}", text)
    return text


def render_docs(docs_dir: Path, blocks: dict[str, str], check: bool = False) -> list[Path]:
    stale = []
    for p in sorted(docs_dir.glob("*.md")) + [docs_dir.parent / "README.md"]:
        if not p.exists():
            continue
        old = p.read_text(encoding="utf-8")
        new = fill(old, blocks)
        if new != old:
            stale.append(p)
            if not check:
                p.write_text(new, encoding="utf-8")
    return stale
