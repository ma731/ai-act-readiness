"""Build the GitHub Pages site into site/ from the committed results and documents.

    python -m scripts.build_site

Nothing on the site is typed by hand twice: numbers come from results/*.json and the
rules engine, and the long documents are the repo's own markdown, rendered.
"""
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

import markdown
import yaml

from src import report
from src.rules import LEGAL_BASIS_DATE, classify_all

ROOT = Path(__file__).parents[1]
OUT = ROOT / "site"
REPO = "https://github.com/ma731/ai-act-readiness"
WORDS = {0: "No", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
TIER = {"prohibited": "Prohibited", "high_risk": "High-risk",
        "transparency": "Transparency", "minimal": "Minimal"}
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
         "&family=IBM+Plex+Mono:wght@400;500;600&display=swap")
DOCS = [
    ("docs/01_classification.md", "Classification", "Which systems the Act catches, and why"),
    ("docs/02_fria_tarifa_salud.md", "Fundamental rights impact assessment",
     "Article 27, with the evidence behind every risk"),
    ("docs/03_gap_assessment.md", "Gap assessment and roadmap",
     "Every obligation, its status and its deadline"),
    ("docs/resumen_ejecutivo.md", "Resumen ejecutivo", "The whole assessment on one page"),
    ("docs/decisions/0001-spanish-data-and-prices.md", "ADR 0001: Spanish data and prices",
     "Why these sources, and every assumption"),
    ("docs/decisions/0002-tolerance-band.md", "ADR 0002: The tolerance band",
     "What counts as over- or undercharged"),
    ("docs/decisions/0003-legacy-systems.md", "ADR 0003: Legacy systems",
     "Why the plan does not rely on Article 111(2)"),
    ("docs/decisions/0004-poisson-glm.md", "ADR 0004: A Poisson GLM",
     "The model choice a sense check forced"),
]

e = html.escape


PRODUCT = "Veredicto"
ICONS = {
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 16v-4"/><path d="M12 16V8"/><path d="M17 16v-7"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8"/>',
    "back": '<path d="M19 12H5M12 19l-7-7 7-7"/>',
}
APP_NAV = [
    ("Screening", [("proposals.html", "Proposal intake", "inbox")]),
    ("Cierzo assessment", [("inventory.html", "AI inventory", "grid"),
                           ("evidence.html", "Fairness evidence", "chart"),
                           ("roadmap.html", "Obligations", "calendar"),
                           ("documents.html", "Documents", "file")]),
]
NAV = [(h, label) for _, items in APP_NAV for h, label, _ in items]


def icon(name: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def head(title: str, description: str, up: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta name="color-scheme" content="light dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{up}style.css">
</head>"""


# ---------------------------------------------------------------- page shell ---------- #
def page(path: str, title: str, body: str, description: str, counts: dict | None = None) -> str:
    """The app: sidebar, top bar, content."""
    up = "../" * path.count("/")
    here = "documents.html" if path.startswith("docs/") else path
    counts = counts or {}
    groups, crumb = [], ""
    for label, items in APP_NAV:
        links = []
        for href, name, ic in items:
            cur = ' aria-current="page"' if href == here else ""
            if cur:
                crumb = name
            n = f'<span class="count">{counts[href]}</span>' if href in counts else ""
            links.append(f'<a href="{up}{href}"{cur}>{icon(ic)}<span>{e(name)}</span>{n}</a>')
        groups.append(f'<div class="navgroup"><span>{e(label)}</span>{"".join(links)}</div>')
    return f"""{head(title, description, up)}
<body>
<div class="app">
<aside class="side">
  <a class="org" href="{up}index.html" title="{PRODUCT} home"><span class="logo">§</span>
    <span><b>Cierzo Seguros</b><span>{PRODUCT} workspace</span></span></a>
  <nav aria-label="Workspace" style="display:contents">{"".join(groups)}</nav>
  <div class="side-foot">
    <span>Law as of {LEGAL_BASIS_DATE:%d %b %Y}</span>
    <span>Cierzo Seguros is fictional. Not legal advice.</span>
    <a href="{up}index.html">About {PRODUCT}</a>
    <a href="{REPO}">Source on GitHub</a>
  </div>
</aside>
<div class="content">
<header class="topbar"><span class="crumb">Cierzo Seguros / <b>{e(crumb)}</b></span>
  <span class="basis">Regulation (EU) 2024/1689, as of {LEGAL_BASIS_DATE:%d %b %Y}</span></header>
<main>
{body}
</main>
<footer>
  <span>Cierzo Seguros is fictional. The law, the survey data and the prices are real. Not legal advice.</span>
  <span><a href="{REPO}">Source on GitHub</a> · built {date.today():%d %b %Y}</span>
</footer>
</div>
</div>
<script>try {{ document.querySelector('.navgroup a[aria-current]').scrollIntoView({{ inline: 'center', block: 'nearest' }}); }} catch (e) {{}}</script>
</body>
</html>
"""


def sec(num: str, title: str, intro: str, inner: str) -> str:
    p = f"<p>{intro}</p>" if intro else ""
    return (f'<section><div class="sec-head"><h2>{title}</h2>{p}</div>'
            f'<div class="sec-body">{inner}</div></section>')


def table_from_md(md_table: str) -> str:
    return '<div class="table-wrap">' + markdown.markdown(md_table, extensions=["tables"]) \
        + "</div>"


# ---------------------------------------------------------------- charts --------------- #
def forest(rows: list[dict], lo: float = 0.6, hi: float = 1.7, band=(0.8, 1.25),
           hot: set[str] | None = None) -> str:
    """Price-to-cost per group with 95% interval, tolerance band shaded, parity at 1.
    Labels sit above each interval so the chart stays legible when scaled to a phone."""
    hot = hot or set()
    w, pad, row_h, top = 560, 14, 64, 34
    h = top + row_h * len(rows) + 30
    x = lambda v: pad + (min(max(v, lo), hi) - lo) / (hi - lo) * (w - 2 * pad)  # noqa: E731
    y0, y1 = top - 10, top + row_h * len(rows)
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Price-to-cost by group">',
             f'<rect class="band" x="{x(band[0]):.1f}" y="{y0}" '
             f'width="{x(band[1]) - x(band[0]):.1f}" height="{y1 - y0}"/>']
    for bnd in band:
        parts.append(f'<line class="band-edge" x1="{x(bnd):.1f}" x2="{x(bnd):.1f}" '
                     f'y1="{y0}" y2="{y1}"/>')
    parts += [f'<line class="parity" x1="{x(1):.1f}" x2="{x(1):.1f}" y1="{y0 - 6}" y2="{y1}"/>',
              f'<text class="tick" x="{x(1):.1f}" y="{y0 - 12}" text-anchor="middle">'
              "1.00 = pays for its own care</text>"]
    for i, r in enumerate(rows):
        ty = top + row_h * i + 16
        y = ty + 20
        a, b = r["price_to_cost_ci"]
        cls = "pt hot" if r["group"] in hot else "pt"
        parts += [
            f'<text class="lbl" x="{pad}" y="{ty}"><tspan font-weight="700">{e(r["group"])}'
            f'</tspan><tspan class="val" dx="10">{r["price_to_cost"]:.2f} ({a:.2f} to '
            f'{b:.2f})</tspan></text>',
            f'<line class="ci" x1="{x(a):.1f}" x2="{x(b):.1f}" y1="{y}" y2="{y}"/>',
            f'<circle class="{cls}" cx="{x(r["price_to_cost"]):.1f}" cy="{y}" r="7"/>',
        ]
    parts.append(f'<line class="axis" x1="{pad}" x2="{w - pad}" y1="{y1 + 6}" y2="{y1 + 6}"/>')
    for t in [0.6, 0.8, 1.0, 1.25, 1.5]:
        if lo <= t <= hi:
            parts.append(f'<text class="tick" x="{x(t):.1f}" y="{y1 + 24}" '
                         f'text-anchor="middle">{t:g}</text>')
    parts.append("</svg>")
    return "".join(parts)


def hbars(items: list[tuple[str, float, tuple[float, float] | None, bool]], fmt,
          vmax: float | None = None) -> str:
    """Horizontal bars, label above each bar, optional interval whiskers.
    items: (label, value, ci, highlight)."""
    w, pad, right, row_h = 560, 0, 70, 44
    vmax = vmax or max((ci[1] if ci else v) for _, v, ci, _ in items) * 1.02
    x = lambda v: pad + v / vmax * (w - pad - right)  # noqa: E731
    h = row_h * len(items) + 4
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img">']
    for i, (label, v, ci, hot) in enumerate(items):
        y = i * row_h
        cls = "bar hot" if hot else "bar"
        parts += [f'<text class="lbl" x="{pad}" y="{y + 15}">{e(label)}</text>',
                  f'<rect class="{cls}" x="{pad}" y="{y + 22}" width="{max(x(v) - pad, 1):.1f}" '
                  'height="12"/>']
        end = x(ci[1]) if ci else x(v)
        if ci:
            parts.append(f'<line class="ci" x1="{x(ci[0]):.1f}" x2="{x(ci[1]):.1f}" '
                         f'y1="{y + 28}" y2="{y + 28}" style="stroke-width:1.5"/>')
        parts.append(f'<text class="val" x="{end + 8:.1f}" y="{y + 33}">{fmt(v)}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- data ---------------- #
def load():
    inv = yaml.safe_load((ROOT / "inventory" / "cierzo_systems.yaml").read_text("utf-8"))
    systems = inv["systems"]
    results = classify_all(systems)
    rows = report.gap_rows(systems, results)
    ev = json.loads((ROOT / "results" / "pricing_evidence.json").read_text("utf-8"))
    tariffs = yaml.safe_load((ROOT / "data" / "tariffs_osakidetza_2024.yaml").read_text("utf-8"))
    return systems, results, rows, ev, tariffs


def pct(x: float, nd: int = 1) -> str:
    return f"{x * 100:.{nd}f}%"


# ---------------------------------------------------------------- pages --------------- #
SUMMARY = {
    "S1": "Prices individual health insurance from the application questionnaire",
    "S2": "Customer chatbot on the website and app, built on a third-party model",
    "S3": "Scores health claims for fraud; investigators decide",
    "S4": "Proposed tool that reads emotions from contact-centre calls",
    "S5": "Vendor engine that rates life insurance applicants",
    "S6": "Prices home insurance",
}


def inventory(systems, results, rows, ev) -> str:
    n = len(systems)
    tiers = [c.tier for c in results]
    banned = tiers.count("prohibited")
    overdue = sum(1 for r in rows if r["state"] == "OVERDUE")
    high = tiers.count("high_risk")
    title = "AI inventory"

    reg = []
    for s, c in zip(systems, results, strict=True):
        late = any(r["system"] == s["id"] and r["state"] == "OVERDUE" for r in rows)
        why = c.basis[0] if c.basis else "Not listed in Annex III, no Article 5 or 50 trigger."
        cites = sorted({m for b in c.basis for m in re.findall(
            r"(Art \d+(?:\(\d+\))?(?:\([a-z]\))?|Annex III \d\([a-z]\))", b)})
        reg.append(
            f'<li><span class="sid">{s["id"]}</span>'
            f'<div><h3>{e(s["name"])}{"<span class=flag>Overdue</span>" if late else ""}</h3>'
            f'<p class="what">{e(SUMMARY[s["id"]])}'
            f'{" (proposed)" if s.get("status") == "proposed" else ""}</p></div>'
            f'<p class="why">{e(why)}<span class="cite">{e(" · ".join(cites))}</span></p>'
            f'<span class="stamp {c.tier}">{TIER[c.tier]}</span></li>')

    born = {g["group"]: g for g in ev["groups"]["born"]}["Born abroad"]
    un = {(u["group"], u["measure"]): u for u in ev["unmet_need"]}
    cls = ev["self_rated_health_by_class"]
    sx = ev["sex_counterfactual"]
    d = ev["data"]
    findings = f"""<div class="findings">
<div class="finding"><span class="big">{born['price_to_cost']:.2f}<small>×</small></span>
<p>What people <b>born abroad</b> would pay per euro of care they use, against 1.00 for
everyone. Country of birth is never an input. A signal, not proof: the interval reaches 1.</p>
<span class="ci">95% CI {born['price_to_cost_ci'][0]:.2f} to {born['price_to_cost_ci'][1]:.2f}</span></div>
<div class="finding"><span class="big">{pct(un[('Born abroad','unmet_cost')]['rate'])}</span>
<p>of people born abroad went without medical care because of cost, against
{pct(un[('Born in Spain','unmet_cost')]['rate'])} of people born in Spain. Lower use is partly
lower access.</p><span class="ci">last 12 months, INE survey</span></div>
<div class="finding"><span class="big">{pct(cls[0]['fair_or_worse_age_standardised'],0)}<small> vs </small>{pct(cls[-1]['fair_or_worse_age_standardised'],0)}</span>
<p>rate their health fair or worse in the top and bottom social class, at the same age. That
answer is the heaviest factor in the price.</p><span class="ci">age-standardised</span></div>
<div class="finding"><span class="big">{sx['female_to_male_premium_unisex']:.2f}<small>×</small></span>
<p>what women are quoted relative to men with sex not an input, against
{sx['female_to_male_actual_cost']:.2f}× in actual cost. Within tolerance, worth watching.</p>
<span class="ci">sex recoverable from other answers: AUC {sx['sex_recoverable_from_rating_factors_auc']:.2f}</span></div>
</div>"""

    urgent = [r for r in sorted(rows, key=report._priority) if r["state"] in
              {"Block before purchase", "OVERDUE"}]
    urgent_html = "".join(
        f"<tr><td><b>{e(r['name'])}</b></td><td class='mono'>{e(r['article'])}</td>"
        f"<td>{e(r['duty'])}</td><td><span class='flag' style='margin:0'>"
        f"{'BLOCK' if r['state'].startswith('Block') else 'OVERDUE'}</span></td></tr>"
        for r in urgent)

    body = f"""
<section class="hero"><div class="page-head"><div>
<h1>{title}</h1>
<p class="lede">Every AI system Cierzo runs or plans to buy, classified under the EU AI Act with the
article behind each call. Its health pricing model was tested for harm on official Spanish data.</p></div>
<div class="actions"><a class="btn ghost" href="documents.html">Documents</a>
<a class="btn" href="roadmap.html">View obligations</a></div></div>
<div class="facts">
<div class="fact"><b>{n}</b><span>AI systems</span></div>
<div class="fact"><b>{high}</b><span>high-risk</span></div>
<div class="fact alert"><b>{banned}</b><span>prohibited, block before purchase</span></div>
<div class="fact alert"><b>{overdue}</b><span>obligation overdue</span></div>
<div class="fact"><b>{d['people']:,}</b><span>people behind the fairness tests</span></div>
</div></section>
{sec("01", "Systems", "Each system is described by facts; the tier is what the rules engine concludes from them.", '<ul class="register">' + "".join(reg) + "</ul>")}
{sec("02", "Needs action now", "Prohibited uses and obligations already past their deadline.", '<div class="table-wrap"><table><thead><tr><th>System</th><th>Article</th><th>Duty</th><th></th></tr></thead><tbody>' + urgent_html + "</tbody></table></div>")}
{sec("03", "Fairness findings: Tarifa Salud", "The health pricing model rebuilt on official Spanish data and tested group by group. <a href='evidence.html'>All the evidence</a>.", findings)}
{sec("04", "Documents", "", doclist())}
"""
    return page("inventory.html", f"AI inventory · Cierzo Seguros · {PRODUCT}", body,
                "EU AI Act readiness for a fictional Spanish insurer: classification, a "
                "fundamental rights impact assessment on INE data, and a dated roadmap.")


def evidence_page(ev, tariffs) -> str:
    d, m = ev["data"], ev["model"]
    born = ev["groups"]["born"]
    priv = ev["private_cover_only"]["born"]
    sexr = ev["groups"]["sex"]
    un = ev["unmet_need"]
    t = tariffs["prices"]

    unmet_items = []
    for measure, label in [("unmet_cost", "Because of cost"),
                           ("unmet_waiting_list", "Because of waiting lists"),
                           ("unmet_transport", "Because of transport")]:
        for g in ["Born abroad", "Born in Spain"]:
            u = next(x for x in un if x["group"] == g and x["measure"] == measure)
            unmet_items.append((f"{label}: {g.replace('Born', 'born')}", u["rate"], tuple(u["ci"]),
                                measure == "unmet_cost" and g == "Born abroad"))
    cls_items = [(r["social_class"], r["fair_or_worse_age_standardised"], None, i == 5)
                 for i, r in enumerate(ev["self_rated_health_by_class"])]
    age_items = [(a["age_band"], a["mean_cost_eur"], None, False) for a in d["age_profile"]]

    rel = m["relativities"]
    from src.pricing import CONDITIONS
    cond_items = sorted(((k.replace("_", " ").replace("copd", "COPD"), rel[k], None, rel[k] < 1)
                         for k in CONDITIONS.values()), key=lambda r: -r[1])

    example = (f"GP          2 visits × 13 × €{t['gp_visit']['eur']:,}   = €{2*13*t['gp_visit']['eur']:,}\n"
               f"Emergency   1 visit            × €{t['emergency_hospital']['eur']:,}  = €{t['emergency_hospital']['eur']:,}\n"
               f"Hospital    3 nights           × €{t['hospital_night']['eur']:,} = €{3*t['hospital_night']['eur']:,}\n"
               f"                                        total €{2*13*t['gp_visit']['eur'] + t['emergency_hospital']['eur'] + 3*t['hospital_night']['eur']:,}")

    body = f"""
<div class="hero">
<p class="kicker">Article 27 evidence · Tarifa Salud</p>
<h1>Does each group pay for the care it uses?</h1>
<p class="lede">A fair price is not the same price for everyone: people with more health
needs cost more. The test is whether each group is charged in line with the care it
actually uses. Everything below is built from official Spanish sources.</p></div>

{sec("01", "Where the numbers come from", "No public Spanish dataset links an insurance application to what the person later costs, so two official sources are joined.", f'''
<div class="sources">
<div class="source"><span class="kicker">The people</span><h3>INE health survey, 2020</h3>
<p>Spain's official health interview survey. It asks what an insurer asks (diagnoses,
self-rated health, smoking, weight, region) and records the care each person used, their
country of birth, their cover, and whether they went without care.</p>
<p class="mono small">{d['people']:,} adults aged 18 to 64 · {d['born_abroad']:,} born abroad ·
{d['with_private_cover']:,} with private cover</p></div>
<div class="source"><span class="kicker">The prices</span><h3>Osakidetza tariff, 2024</h3>
<p>What the Basque public health service bills insurers and other third parties for each
kind of care. Every price carries its page and billing code, and a script checks each one
against the official PDF.</p>
<p class="mono small">{len(t)} prices · verified in CI on every change</p></div>
</div>
<div class="with-notes" style="margin-top:28px">
<div><p>Each person's care is multiplied by its price. Someone who saw their GP twice in the
last four weeks, went to a hospital emergency department once and spent three nights in
hospital:</p><div class="receipt">{e(example)}</div>
<p class="muted small">Visits are asked about over four weeks, so they are scaled by 13 to
a year. Prescriptions, dental, physiotherapy, psychology and childbirth are left out, each
for a stated reason.</p></div>
<aside class="note"><b>AVERAGE ADULT</b>€{d['mean_annual_cost_eur']:,.0f} a year; median
€{d['median_annual_cost_eur']:,.0f}; {pct(d['share_with_no_care'])} used no care at all. A
few people cost a lot, as in any health book.</aside></div>
{table_from_md(report.cost_build(tariffs, None))}
''')}

{sec("02", "Born abroad: a signal, not proof", "Price-to-cost: what a group pays per euro of care it uses, against 1.00 for everyone. The shaded zone is the tolerance band (0.80 to 1.25); a verdict needs the whole interval outside it.", f'''
<figure><p class="chart-title">All adults 18 to 64</p>{forest(born, hot={"Born abroad"})}
<p class="chart-title" style="margin-top:22px">Only people who already hold private cover</p>{forest(priv, hot={"Born abroad"})}
<figcaption><b>Same level, twice.</b> People born abroad would pay about
{born[0]['price_to_cost']:.2f}× their share whether or not they already hold private cover.
The intervals reach 1.0, so this is something to monitor, not a proven breach. Country of
birth is never an input: the gap comes through the answers they give.</figcaption></figure>
''')}

{sec("03", "Lower use, or lower access?", "The survey asks whether people went without care they needed. If a group uses less care and also goes without more often, its low use is not low need.", f'''
<p class="chart-title">Went without care they needed, last 12 months</p>
<figure style="margin-top:0">{hbars(unmet_items, pct)}
<figcaption>Cost stops people born abroad more often; waiting lists and transport affect
both groups about equally. A price built on past use charges people for care they did not
get.</figcaption></figure>''')}

{sec("04", "The heaviest factor follows social class", "Self-rated health moves the price more than any diagnosis. Share rating their health fair or worse, at the same age mix:", f'''
<figure>{hbars(cls_items, pct)}
<figcaption>Spanish insurance law (Ley 4/2018) asks for objective, documented reasons for
health-based loadings. A self-assessment that tracks class needs that justification in
writing.</figcaption></figure>''')}

{sec("05", "Sex, kept out, leaks back a little", "", f'''
<figure>{forest(sexr, lo=0.7, hi=1.4)}
<figcaption>Sex is not an input. Women are quoted
{ev['sex_counterfactual']['female_to_male_premium_unisex']:.2f}× what men are, against
{ev['sex_counterfactual']['female_to_male_actual_cost']:.2f}× in cost, because other answers
partly reveal sex. Within tolerance; maternity costs are excluded, as EU law requires.
</figcaption></figure>''')}

{sec("06", "Sense checks", "Numbers were checked for sense before they were written up.", f'''
<div class="with-notes"><div>
<p class="chart-title">Average yearly cost by age</p>
<figure style="margin-top:0">{hbars(age_items, lambda v: f"€{v:,.0f}")}
<figcaption>Raw cost rises with age. In the model, age adds little once diagnoses and
self-rated health are known, because that is where older people's extra cost shows up.
</figcaption></figure>
<p class="chart-title" style="margin-top:34px">What each diagnosis does to the price</p>
<figure style="margin-top:0">{hbars(cond_items, lambda v: f"{v:.2f}×")}
<figcaption>Multipliers once the other answers are known. Conditions below 1.00 (in red)
do not support a loading on this evidence, which Ley 4/2018 requires.</figcaption></figure>
</div>
<aside class="note"><b>A FALSE FINDING, CAUGHT</b>The first model (Tweedie) priced women at
1.43× men even when it could see sex, against 1.12× in cost. The fault was the loss function,
not women. A Poisson GLM, whose averages match cost for every group it sees, replaced it.
<a href="docs/decisions/0004-poisson-glm.html">ADR 0004</a>.<br><br>
<b>MODEL</b>{e(m['primary'])}; {e(m['validation'])}. Gini {m['gini_glm']:.3f} against
{m['gini_gbm_challenger']:.3f} for gradient boosting. Predicted over actual cost
{m['book_price_to_cost']:.3f}.</aside></div>''')}

{sec("07", "Where it stops", "", '''<div class="prose"><ul>
<li><b>The cost is built, not observed:</b> care people reported using, priced at one
region's official tariff, not an insurer's claims.</li>
<li><b>The survey spans COVID-19:</b> the last four months of fieldwork came after the
state of alarm, when people used less care.</li>
<li><b>Intervals are slightly too narrow:</b> the public file leaves out the census areas the
sample was drawn from.</li>
<li><b>The tolerance band was set after a first look at results</b> and is not a legal
threshold.</li></ul>
<p><a href="docs/decisions/0001-spanish-data-and-prices.html">Every assumption, and which way
it pushes the cost</a></p></div>''')}
"""
    return page("evidence.html", f"Fairness evidence · Cierzo Seguros · {PRODUCT}", body,
                "The Tarifa Salud pricing model rebuilt on INE survey data and Osakidetza "
                "tariffs, tested group by group.")


def roadmap_page(rows) -> str:
    today = LEGAL_BASIS_DATE
    milestones = [
        (date(2025, 2, 2), "Prohibitions and AI literacy",
         lambda r: r["article"].startswith(("Art 5(", "Art 4"))),
        (date(2026, 8, 2), "Chatbots must say they are AI",
         lambda r: r["article"] in {"Art 50(1)", "Art 50(3)"}),
        (today, "Today", None),
        (date(2026, 12, 2), "Generated content must be marked",
         lambda r: r["article"] == "Art 50(2)"),
        (date(2027, 12, 2), "High-risk duties apply",
         lambda r: r["applies_from"] == date(2027, 12, 2)),
    ]
    rows_html = []
    for when, title, pick in milestones:
        cls = "today" if pick is None else ("past" if when < today else "")
        if pick is None:
            live = [r for r in rows if r["live"]]
            items = (f"<p class='muted'>{report.gap_summary(rows).replace('**', '')}</p>")
            rows_html.append(f'<div class="tl-row today"><div class="tl-date">'
                             f'{when:%d %b %Y}</div><div class="tl-dot"><i></i></div>'
                             f'<div class="tl-body"><h3>{title}</h3>{items}</div></div>')
            continue
        per_sys: dict[str, list[str]] = {}
        state: dict[str, str] = {}
        for r in rows:
            if pick(r):
                per_sys.setdefault(r["name"], []).append(r["article"])
                if r["state"] in {"OVERDUE", "Block before purchase"}:
                    state[r["name"]] = "OVERDUE" if r["state"] == "OVERDUE" else "BLOCK"
        lis = "".join(
            f"<li><b>{e(k)}</b> <span class='mono small'>{e(', '.join(dict.fromkeys(v)))}</span>"
            f"{'<span class=flag>' + state[k] + '</span>' if k in state else ''}</li>"
            for k, v in per_sys.items())
        rows_html.append(f'<div class="tl-row {cls}"><div class="tl-date">{when:%d %b %Y}</div>'
                         f'<div class="tl-dot"><i></i></div><div class="tl-body"><h3>{title}'
                         f"</h3><ul>{lis}</ul></div></div>")

    live = [r for r in rows if r["live"]]
    counts = {k: sum(1 for r in live if r["status"] == k) for k in ["met", "partial", "missing"]}
    total = sum(counts.values())
    colors = {"met": "var(--ok)", "partial": "var(--high)", "missing": "var(--accent)"}
    stack = "".join(f'<span style="width:{counts[k] / total * 100:.2f}%;background:{colors[k]}">'
                    "</span>" for k in counts)
    legend = "".join(f'<span><i style="background:{colors[k]}"></i>{counts[k]} {k}</span>'
                     for k in counts)
    body = f"""
<div class="hero">
<p class="kicker">Gap assessment · dated against the Digital Omnibus</p>
<h1>Obligations and deadlines</h1>
<p class="lede">Every obligation the classification produced, set against Cierzo's current
controls. The Omnibus moved stand-alone high-risk duties to 2 December 2027; chatbot
transparency did not move.</p>
<div class="stack" aria-hidden="true">{stack}</div><div class="legend">{legend}</div></div>
{sec("01", "Timeline", "", '<div class="timeline">' + "".join(rows_html) + "</div>")}
{sec("02", "Why plan for December 2027 at all", "", '''<div class="prose"><p>Both high-risk
systems were in service before the rules apply. Under Article 111(2) their duties bite only
after a significant design change, and sources disagree on the post-Omnibus cut-off. Tarifa
Salud is re-rated every January, which is the obvious candidate for such a change, so the plan
does not rely on the exemption. <a href="docs/decisions/0003-legacy-systems.html">ADR 0003</a>.
</p><p><a href="docs/03_gap_assessment.html">Every obligation, with status and the AESIA guide
that covers it</a></p></div>''')}
"""
    return page("roadmap.html", f"Obligations · Cierzo Seguros · {PRODUCT}", body,
                "Every AI Act obligation for Cierzo Seguros, its current status and deadline.")


def doclist() -> str:
    lis = "".join(
        f'<li><a href="{md.replace(".md", ".html")}">{e(t)}</a><span>{e(desc)}</span></li>'
        for md, t, desc in DOCS)
    return f'<ul class="doclist">{lis}</ul>'


def render_doc(md_path: str, title: str, desc: str) -> tuple[str, str]:
    src = (ROOT / md_path).read_text(encoding="utf-8")
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "sane_lists"])
    here = Path(md_path).parent

    def fix(m):
        href = m.group(1)
        if href.startswith(("http", "#", "mailto:")):
            return m.group(0)
        target = (here / href.split("#")[0]).as_posix()
        target = str(Path(target)).replace("\\", "/")
        norm = Path(*[p for p in Path(target).parts])
        resolved = (ROOT / norm).resolve()
        rel = resolved.relative_to(ROOT.resolve()).as_posix()
        if rel.endswith(".md") and rel.startswith("docs/"):
            out = Path(rel).with_suffix(".html").as_posix()
            return f'href="{"../" * md_path.count("/")}{out}"'
        kind = "tree" if resolved.is_dir() else "blob"
        return f'href="{REPO}/{kind}/main/{rel}"'

    body = re.sub(r'href="([^"]+)"', fix, body)
    body = re.sub(r"<table>", '<div class="table-wrap"><table>', body)
    body = re.sub(r"</table>", "</table></div>", body)
    out = md_path.replace(".md", ".html")
    return out, page(out, f"{title} · Cierzo Seguros", f'<article class="doc">{body}</article>',
                     desc)


def documents_page() -> str:
    body = f"""<div class="hero"><h1>Documents</h1>
<p class="lede">The repository's own documents, rendered. Prose is written by hand; every
table and number in them is generated from the results.</p></div>
<section><div class="sec-body">{doclist()}</div></section>"""
    return page("documents.html", f"Documents · Cierzo Seguros · {PRODUCT}", body,
                "The classification, FRIA, gap assessment, Spanish summary and decision records.")


def fact_label(fact: str, value) -> str:
    """A fact as a reviewer would say it."""
    from src.screener.law import ANNEX_III, ART6_3, PROHIBITED
    if fact == "prohibited":
        return f"{PROHIBITED.get(value, ('Art 5', ''))[0]} {str(value).replace('_', ' ')}"
    if fact == "annex_iii":
        return f"Annex III {value}"
    if fact == "art6_3_claim":
        return ART6_3.get(value, str(value)).split(" ", 1)[0] + " claim"
    if fact == "role":
        return str(value)
    names = {"annex_i_safety_component": "Annex I safety component", "fraud_detection_only": "fraud only",
             "profiling": "profiling", "affects_natural_persons": "affects people",
             "interacts_with_people": "talks to people", "generates_synthetic_content": "generates content",
             "deepfake": "deepfake", "emotion_or_biometric_categorisation": "emotion or biometrics",
             "uses_personal_data": "personal data", "uses_special_category_data": "special-category data",
             "automated_decision": "automated decision"}
    _ = ANNEX_III
    return names.get(fact, fact.replace("_", " "))


def annotated(text: str, evidence: list[dict]) -> str:
    """The proposal sentence by sentence; quoted sentences marked, with the facts they gave."""
    from src.screener.readers import sentences
    norm = lambda s: " ".join(s.lower().split())  # noqa: E731
    out = []
    for s in sentences(text):
        tags = [fact_label(ev["fact"], ev["value"]) for ev in evidence
                if norm(ev["quote"]) and norm(ev["quote"]) in norm(s)]
        if tags:
            chips = "".join(f"<span class='fchip'>{e(t)}</span>" for t in dict.fromkeys(tags))
            out.append(f"<mark>{e(s)}</mark><span class='fchips'>{chips}</span>")
        else:
            out.append(f"<span class='dim'>{e(s)}</span>")
    return " ".join(out)


def screening():
    import csv
    data = json.loads((ROOT / "results" / "proposals" / "screening.json").read_text(encoding="utf-8"))
    texts = {r["id"]: r["proposal"] for r in csv.DictReader(
        (ROOT / "data" / "proposals_sample.csv").open(encoding="utf-8"))}
    return data, texts


CHEV = '<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>'
CLOSE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>'


def detail(r: dict, text: str) -> str:
    """Drawer content for one proposal."""
    obligations = "".join(
        f"<tr><td class='mono'>{e(o['article'])}</td><td>{e(o['duty'])}</td>"
        f"<td class='mono nowrap'>{e(o['applies_from'])}</td></tr>"
        for o in r["obligations"] if o["article"] != "Art 4")
    ob = (f"<div class='table-wrap'><table class='obl'><thead><tr><th>Article</th><th>Duty</th>"
          f"<th>Applies from</th></tr></thead><tbody>{obligations}</tbody></table></div>"
          if obligations else "<p class='muted small'>Only AI literacy (Art 4), as for every AI system.</p>")
    rv = ("<div class='review'><b>Sent to a person</b><ul>"
          + "".join(f"<li>{e(x)}</li>" for x in r["review_reasons"]) + "</ul></div>") if r["needs_review"] else ""
    trace = "".join(f"<li>{e(t)}</li>" for t in r["trace"])
    return f"""<div class="dr-head"><span class="sid">{e(r['id'])}</span>
<h2 id="dr-title">{e(r['title'])}</h2><span class="co">{e(r['company'])}</span>
<span><span class="stamp {r['tier']}">{TIER[r['tier']]}</span></span>
<button type="button" class="x" data-close aria-label="Close">{CLOSE}</button></div>
<div class="dr-body">{rv}
<p class="label">Verdict</p><p class="memo">{e(r['memo'])}</p>
<p class="label">Proposal</p><p class="proposal">{annotated(text, r['evidence'])}</p>
<p class="legend-q"><mark>Highlighted</mark> sentences were quoted by the reader. Facts without a real quote are dropped before the law is applied.</p>
<p class="label">Obligations</p>{ob}
<p class="label">Audit trail</p><ol class="trace">{trace}</ol></div>"""


QUEUE_JS = """<script>
(() => {
  const chips = [...document.querySelectorAll('.chip')];
  const items = [...document.querySelectorAll('.pv')];
  const shown = document.getElementById('shown');
  const drawer = document.getElementById('drawer'), scrim = document.getElementById('scrim');
  const inner = document.getElementById('dr-inner');
  let current = null, opener = null;
  const visible = () => items.filter(i => !i.hidden);
  chips.forEach(c => c.addEventListener('click', () => {
    const f = c.dataset.filter;
    chips.forEach(x => x.setAttribute('aria-pressed', String(x === c)));
    let n = 0;
    items.forEach(r => {
      const on = f === 'all' || r.dataset.tags.split(' ').includes(f);
      r.hidden = !on;
      r.classList.remove('in');
      if (on) { r.style.setProperty('--i', Math.min(n++, 10)); void r.offsetWidth; r.classList.add('in'); }
    });
    shown.textContent = n === items.length ? `${n} proposals` : `${n} of ${items.length}`;
  }));
  function open(id) {
    const tpl = document.getElementById('t-' + id);
    if (!tpl) return;
    inner.replaceChildren(tpl.content.cloneNode(true));
    current = id;
    drawer.setAttribute('data-open', ''); scrim.setAttribute('data-open', '');
    drawer.setAttribute('aria-hidden', 'false');
    document.documentElement.style.overflow = 'hidden';
    inner.querySelector('[data-close]').focus({ preventScroll: true });
    const v = visible().map(i => i.dataset.id), k = v.indexOf(id);
    document.getElementById('prev').disabled = k <= 0;
    document.getElementById('next').disabled = k < 0 || k >= v.length - 1;
    try { history.replaceState(null, '', '#' + id); } catch (e) {}
  }
  function close() {
    drawer.removeAttribute('data-open'); scrim.removeAttribute('data-open');
    drawer.setAttribute('aria-hidden', 'true');
    document.documentElement.style.overflow = '';
    current = null;
    try { history.replaceState(null, '', location.pathname); } catch (e) {}
    if (opener) opener.focus({ preventScroll: true });
  }
  function step(d) {
    const v = visible().map(i => i.dataset.id), k = v.indexOf(current) + d;
    if (k >= 0 && k < v.length) open(v[k]);
  }
  items.forEach(i => i.querySelector('.pv-row').addEventListener('click', e => { opener = e.currentTarget; open(i.dataset.id); }));
  scrim.addEventListener('click', close);
  drawer.addEventListener('click', e => { if (e.target.closest('[data-close]')) close(); });
  document.getElementById('prev').addEventListener('click', () => step(-1));
  document.getElementById('next').addEventListener('click', () => step(1));
  document.addEventListener('keydown', e => {
    if (!current) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); step(1); }
    if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); step(-1); }
  });
  const h = location.hash.slice(1);
  if (h && document.getElementById('t-' + h)) open(h);
  document.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy); b.dataset.state = 'done'; setTimeout(() => b.dataset.state = '', 1600); }
    catch (e) { const r = document.createRange(); r.selectNodeContents(b.previousElementSibling); getSelection().removeAllRanges(); getSelection().addRange(r); }
  }));
})();
</script>"""


def queue_rows(res: list[dict], interactive: bool = True) -> str:
    rows = []
    for r in res:
        flag = '<span class="flag rv">Review</span>' if r["needs_review"] else ""
        tag = "button type='button'" if interactive else "div"
        end = "button" if interactive else "div"
        rows.append(
            f'<li class="pv" data-id="{e(r["id"])}" data-tags="{r["tier"]}{" review" if r["needs_review"] else ""}">'
            f'<{tag} class="pv-row"><span class="sid">{e(r["id"])}</span>'
            f'<span class="pv-main"><span class="pv-title">{e(r["title"])}{flag}</span>'
            f'<span class="pv-co">{e(r["company"].replace(" (fictional)", ""))}</span></span>'
            f'<span class="stamp {r["tier"]}">{TIER[r["tier"]]}</span>'
            f'<span class="pv-arts">{e(", ".join(r["articles"][:3]))}</span>{CHEV}</{end}></li>')
    return "".join(rows)


def proposals_page() -> str:
    data, texts = screening()
    res = data["results"]
    n = len(res)
    count = {t: sum(r["tier"] == t for r in res) for t in TIER}
    review = sum(r["needs_review"] for r in res)
    agree = sum(r["tier"] == (x.get("expected_tier") or r["tier"]) for r, x in zip(res, res, strict=True))
    chips = [("all", "All", n)] + [(t, TIER[t], count[t]) for t in TIER] + [("review", "Needs review", review)]
    filters = "".join(
        f'<button type="button" class="chip" data-filter="{k}" aria-pressed="{"true" if k == "all" else "false"}">'
        f'{e(label)}<span class="n">{c}</span></button>' for k, label, c in chips)
    templates = "".join(f'<template id="t-{e(r["id"])}">{detail(r, texts.get(r["id"], ""))}</template>' for r in res)
    steps = [
        ("Read", "agent", "Turns each proposal into facts, quoting the sentence each fact comes from."),
        ("Verify", "code", "Drops any fact whose quote is not in the proposal."),
        ("Classify", "code", "Applies Article 5, Annex III, Annex I, Article 50 and the 6(3) derogation."),
        ("Challenge", "agent", "A second reader looks for missed facts; code re-classifies."),
        ("Explain", "agent", "Writes a memo, checked to cite only articles the classification used."),
        ("Escalate", "code", "Disputed or judgement-heavy cases go to a person."),
    ]
    flow = "".join(f'<li><span class="step-n">{i}</span><h3>{e(t)}</h3><span class="who {w}">{w}</span>'
                   f'<p>{e(d)}</p></li>' for i, (t, w, d) in enumerate(steps, 1))
    cmd = "python -m scripts.screen_proposals my_proposals.xlsx"
    _ = agree
    body = f"""
<section class="hero">
  <div class="page-head">
    <div><h1>Proposal intake</h1>
    <p class="lede">{n} proposals screened against the EU AI Act. Open one to see the sentences behind its verdict.</p></div>
    <div class="actions"><a class="btn ghost" href="downloads/proposals_sample.csv">Sample input</a>
    <a class="btn" href="downloads/screening.xlsx">Export to Excel</a></div>
  </div>
  <div class="facts">
    <div class="fact alert"><b>{count['prohibited']}</b><span>prohibited</span></div>
    <div class="fact"><b>{count['high_risk']}</b><span>high-risk</span></div>
    <div class="fact"><b>{count['transparency']}</b><span>transparency only</span></div>
    <div class="fact"><b>{count['minimal']}</b><span>minimal</span></div>
    <div class="fact"><b>{review}</b><span>waiting for a person</span></div>
  </div>
</section>
<section>
  <div class="sec-body">
    <div class="toolbar"><div class="filters" role="group" aria-label="Filter by verdict">{filters}</div>
    <p class="shown mono" id="shown" aria-live="polite">{n} proposals</p></div>
    <div class="pvs-head" aria-hidden="true"><span>ID</span><span>Proposal</span><span>Verdict</span><span>Articles</span><span></span></div>
    <ol class="pvs">{queue_rows(res)}</ol>
    <p class="small muted" style="margin:12px 0 0">Read by the {e(data['reader'])}, a keyword baseline tuned on these samples, so agreeing with all 16 labels tests the pipeline, not reading ability. Configure Azure OpenAI or Claude to use a model reader.</p>
  </div>
</section>
{sec("", "How a verdict is reached", "A fixed workflow, not a free-roaming agent: the model reads and explains, code decides, so the same proposal always gets the same answer.", '<ol class="flow">' + flow + "</ol>")}
{sec("", "Screen your own proposals", "", f'''<div class="prose"><p>Put proposals in a spreadsheet with the columns
<code>id</code>, <code>company</code>, <code>title</code> and <code>proposal</code>, then run:</p>
<div class="cmd"><code>{cmd}</code><button type="button" class="copy" data-copy="{cmd}"><span class="c1">Copy</span><span class="c2">Copied</span></button></div>
<p class="muted">You get a workbook with a summary, the review queue, every obligation, the quote behind each fact and the audit trail. <a href="{REPO}/tree/main/src/screener">Source code</a>.</p></div>''')}
<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-labelledby="dr-title" aria-hidden="true">
  <div id="dr-inner" class="dr-inner"></div>
  <div class="dr-nav"><button type="button" class="btn ghost" id="prev">Previous</button>
  <button type="button" class="btn ghost" id="next">Next</button></div>
</aside>
{templates}
{QUEUE_JS}
"""
    return page("proposals.html", f"Proposal intake · {PRODUCT}", body,
                "AI use-case proposals screened against the EU AI Act: verdict, articles, obligations and the quotes behind each fact.",
                counts={"proposals.html": n})


def landing() -> str:
    """The product homepage."""
    data, texts = screening()
    res = data["results"]
    by_tier = {}
    for r in res:
        by_tier.setdefault(r["tier"], r)
    examples = [by_tier[t] for t in ("prohibited", "high_risk", "transparency") if t in by_tier]
    tabs = "".join(
        f'<button type="button" role="tab" id="tab-{i}" aria-controls="ex-{i}" aria-selected="{"true" if i == 0 else "false"}"'
        f' tabindex="{0 if i == 0 else -1}">{e(r["title"])}</button>' for i, r in enumerate(examples))
    panels = "".join(f"""<div class="ex" role="tabpanel" id="ex-{i}" aria-labelledby="tab-{i}"{"" if i == 0 else " hidden"}>
<div class="ex-text"><p class="label">The proposal</p><p class="proposal">{annotated(texts.get(r['id'], ''), r['evidence'])}</p></div>
<div class="ex-out"><p class="label">What comes back</p><span class="stamp {r['tier']}">{TIER[r['tier']]}</span>
<p class="memo">{e(r['memo'].split('. ')[0].rstrip('.'))}.</p>
<p class="arts">{"".join(f"<span class='fchip'>{e(a)}</span>" for a in r['articles'][:5])}</p>
<p class="small muted">{len([o for o in r['obligations'] if o['article'] != 'Art 4'])} obligations{f", first due {r['next_deadline']}" if r['next_deadline'] else ""}</p>
<a class="more" href="proposals.html#{e(r['id'])}">Open in the app</a></div></div>""" for i, r in enumerate(examples))
    mini = queue_rows(res[:7], interactive=False)
    n, review = len(res), sum(r["needs_review"] for r in res)
    people = json.loads((ROOT / "results" / "pricing_evidence.json").read_text("utf-8"))["data"]["people"]
    js = """<script>
(() => {
  const tabs = [...document.querySelectorAll('[role=tab]')];
  const pick = t => {
    tabs.forEach(x => { const on = x === t; x.setAttribute('aria-selected', on); x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute('aria-controls')).hidden = !on; });
    const bar = document.querySelector('.seg-ind');
    if (bar) { bar.style.width = t.offsetWidth + 'px'; bar.style.transform = `translateX(${t.offsetLeft - 4}px)`; }
  };
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => pick(t));
    t.addEventListener('keydown', e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (d) { const n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); pick(n); }
    });
  });
  const first = tabs.find(t => t.getAttribute('aria-selected') === 'true');
  if (first) requestAnimationFrame(() => { document.querySelector('.seg').classList.add('ready'); pick(first); });
  addEventListener('resize', () => { const t = tabs.find(x => x.getAttribute('aria-selected') === 'true'); if (t) pick(t); });
})();
</script>"""
    body = f"""<div class="site">
<header class="snav"><a class="sbrand" href="index.html"><span class="logo">§</span>{PRODUCT}</a>
<nav aria-label="Main"><a href="#how">How it works</a><a href="#examples">Examples</a><a href="inventory.html">Case study</a><a href="documents.html">Docs</a></nav>
<span class="snav-cta"><a class="btn ghost sm" href="{REPO}">GitHub</a><a class="btn sm" href="proposals.html">Open the app</a></span></header>

<section class="shero">
  <h1>Check an AI idea against the EU&nbsp;AI&nbsp;Act before anyone builds it.</h1>
  <p class="slede">Send a spreadsheet of proposals. Each comes back with a verdict, the articles behind it,
  its obligations and a short memo. A model reads; the law is applied in code, so the same proposal always
  gets the same answer.</p>
  <p class="actions center"><a class="btn lg" href="proposals.html">Open the app</a>
  <a class="btn ghost lg" href="downloads/screening.xlsx">See a sample result</a></p>
  <p class="fine">Portfolio project. The companies are fictional; the law is current to {LEGAL_BASIS_DATE:%d %B %Y}. Not legal advice.</p>
</section>

<a class="window" href="proposals.html" aria-label="Open the proposal intake">
  <div class="win-bar"><i></i><i></i><i></i><span>veredicto / cierzo-seguros / intake</span></div>
  <div class="win-body">
    <div class="win-side"><span class="logo">§</span><b>Cierzo Seguros</b>
      <span class="on">{icon('inbox')}Proposal intake</span><span>{icon('grid')}AI inventory</span>
      <span>{icon('chart')}Fairness evidence</span><span>{icon('calendar')}Obligations</span></div>
    <div class="win-main"><div class="win-title"><b>Proposal intake</b><span>{n} screened · {review} waiting for a person</span></div>
      <ol class="pvs">{mini}</ol></div>
  </div>
</a>

<section class="sblock" id="examples">
  <h2>Three proposals, three answers.</h2>
  <p class="ssub">Highlighted sentences are the ones the reader quoted. A fact with no real quote never reaches the law.</p>
  <div class="seg" role="tablist" aria-label="Example proposals"><span class="seg-ind" aria-hidden="true"></span>{tabs}</div>
  <div class="ex-wrap">{panels}</div>
</section>

<section class="sblock" id="how">
  <h2>A model reads. Code decides. A person checks.</h2>
  <div class="cols">
    <div><h3>Read, with receipts</h3><p>An agent turns free text into facts, and must quote the sentence each fact comes from. Code throws out any fact whose quote is not in the proposal.</p></div>
    <div><h3>The law, in code</h3><p>Every Article 5 practice, every Annex III area, the Annex I route, Article 50 and the Article 6(3) derogation, with the dates the Digital Omnibus set. The model never picks the tier.</p></div>
    <div><h3>People where it matters</h3><p>A second reader looks for missed facts. Disputed cases, derogation claims and "significant harm" calls go to a review queue instead of getting a confident answer.</p></div>
  </div>
  <div class="runs"><span>Runs on</span><b>Azure OpenAI</b><b>Claude on Azure Foundry</b><b>Claude API</b><b>Offline, no key</b></div>
</section>

<section class="sblock case">
  <div><p class="eyebrow">Case study</p><h2>Cierzo Seguros, a Spanish health and life insurer</h2>
  <p>Six AI systems classified, the health pricing model tested for harm on {people:,} adults from Spain's official
  health survey, and a dated plan for every gap. One prohibited use blocked before purchase, one obligation already overdue.</p>
  <p class="actions"><a class="btn" href="inventory.html">Read the case study</a><a class="btn ghost" href="evidence.html">See the fairness evidence</a></p></div>
</section>

<footer class="sfoot"><span><b>{PRODUCT}</b> · EU AI Act screening</span>
<span>Built by Marco Ortiz Togashi · <a href="{REPO}">Source on GitHub</a> · Not legal advice</span></footer>
</div>
{js}"""
    return f"""{head(f"{PRODUCT}: check AI ideas against the EU AI Act", "Screen AI use-case proposals against the EU AI Act: a model reads, code applies the law, people review the hard cases.", "")}
<body class="landing">
{body}
</body>
</html>
"""


def main() -> int:
    systems, results, rows, ev, tariffs = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy(ROOT / "site_src" / "style.css", OUT / "style.css")
    pages = {
        "index.html": landing(),
        "inventory.html": inventory(systems, results, rows, ev),
        "evidence.html": evidence_page(ev, tariffs),
        "roadmap.html": roadmap_page(rows),
        "proposals.html": proposals_page(),
        "documents.html": documents_page(),
    }
    (OUT / "downloads").mkdir()
    shutil.copy(ROOT / "results" / "proposals" / "screening.xlsx", OUT / "downloads" / "screening.xlsx")
    shutil.copy(ROOT / "data" / "proposals_sample.csv", OUT / "downloads" / "proposals_sample.csv")
    for md, title, desc in DOCS:
        out, text = render_doc(md, title, desc)
        pages[out] = text
    for rel, text in pages.items():
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(pages)} pages into {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
