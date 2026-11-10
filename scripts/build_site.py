"""Build the GitHub Pages site into site/ from the committed results and documents.

    python -m scripts.build_site

Nothing on the site is typed by hand twice: numbers come from results/*.json and the
rules engine, and the long documents are the repo's own markdown, rendered.
"""
from __future__ import annotations

import html
import json
import math
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import quote

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
FONTS = ("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600"
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
    "radio": '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49M7.76 16.24a6 6 0 0 1 0-8.49M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14"/>',
    "flask": '<path d="M9 3h6M10 3v6L4.5 18.5A2 2 0 0 0 6.2 21.5h11.6a2 2 0 0 0 1.7-3L14 9V3"/><path d="M7 15h10"/>',
    "back": '<path d="M19 12H5M12 19l-7-7 7-7"/>',
}
APP_NAV = [
    ("Screening", [("proposals.html", "Proposal intake", "inbox"), ("cases.html", "EU public sector", "radio"),
                   ("stress.html", "Stress test", "flask")]),
    ("Cierzo assessment", [("inventory.html", "AI inventory", "grid"),
                           ("evidence.html", "Fairness evidence", "chart"),
                           ("roadmap.html", "Obligations", "calendar"),
                           ("documents.html", "Documents", "file")]),
]
NAV = [(h, label) for _, items in APP_NAV for h, label, _ in items]


# ---------------------------------------------------------------- brand ---------------- #
LOGO_SVG = ('<svg class="{cls}" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#003399"/>'
            '<rect x="7" y="7.6" width="18" height="2.8" rx="1.4" fill="#fff" fill-opacity=".5"/>'
            '<rect x="5.6" y="12.4" width="20.8" height="6.2" rx="2.2" fill="#FFCC00"/>'
            '<rect x="8" y="14.1" width="12.5" height="2.8" rx="1.4" fill="#003399"/>'
            '<rect x="7" y="20.8" width="8.5" height="2.8" rx="1.4" fill="#fff" fill-opacity=".5"/>'
            '<path d="M18.4 22.4l2.5 2.5 4.9-5.6" fill="none" stroke="#fff" stroke-width="2.8" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def logo(cls: str = "mark") -> str:
    """Veredicto's mark: lines of a proposal, the quoted one highlighted, and a verdict."""
    return LOGO_SVG.format(cls=cls)


def _star(cx: float, cy: float, r: float) -> str:
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.382
        pts.append(f"{cx + rr * math.cos(a):.2f},{cy + rr * math.sin(a):.2f}")
    return " ".join(pts)


def eu_flag(cls: str = "flag-eu") -> str:
    """The EU flag, used only to mark EU law, never as this project's logo."""
    w, h = 27, 18
    stars = "".join(
        f'<polygon points="{_star(w / 2 + h / 3 * math.cos(-math.pi / 2 + i * math.pi / 6), h / 2 + h / 3 * math.sin(-math.pi / 2 + i * math.pi / 6), h / 18)}"/>'
        for i in range(12))
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" role="img" aria-label="Flag of the European Union">'
            f'<rect width="{w}" height="{h}" fill="#003399"/><g fill="#FFCC00">{stars}</g></svg>')


FAVICON = "data:image/svg+xml," + quote(LOGO_SVG.format(cls="f").replace('class="f" ', 'xmlns="http://www.w3.org/2000/svg" '))
NOT_EU = "Independent project. Not affiliated with or endorsed by the European Union or any EU institution."


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
<link rel="icon" href="{FAVICON}">
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
<body data-page="{path}">
<div class="app">
<aside class="side">
  <a class="org" href="{up}index.html" title="{PRODUCT} home">{logo()}
    <span><b>Cierzo Seguros</b><span>{PRODUCT} workspace</span></span></a>
  <span class="eu-badge side-badge" title="Screens against the EU AI Act, Regulation (EU) 2024/1689">{eu_flag()}EU AI Act</span>
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
  <span class="basis">{eu_flag()}Regulation (EU) 2024/1689, as of {LEGAL_BASIS_DATE:%d %b %Y}</span></header>
<main>
{body}
</main>
<footer>
  <span>Cierzo Seguros is fictional. The law, the survey data and the prices are real. Not legal advice. {NOT_EU}</span>
  <span><a href="{REPO}">Source on GitHub</a> · built {date.today():%d %b %Y}</span>
</footer>
</div>
</div>
<script>try {{ document.querySelector('.navgroup a[aria-current]').scrollIntoView({{ inline: 'center', block: 'nearest' }}); }} catch (e) {{}}</script>
<script src="{up}site.js" data-up="{up}"></script>
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
    reg, st = live_data()
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
<header class="snav"><a class="sbrand" href="index.html">{logo()}{PRODUCT}</a><span class="eu-badge" title="Screens against the EU AI Act, Regulation (EU) 2024/1689">{eu_flag()}EU AI Act</span>
<nav aria-label="Main"><a href="#how">How it works</a><a href="#examples">Examples</a><a href="inventory.html">Case study</a><a href="documents.html">Docs</a></nav>
<span class="snav-cta"><a class="btn ghost sm" href="{REPO}">GitHub</a><a class="btn sm" href="proposals.html">Open the app</a></span></header>

<section class="shero">
  <p class="hero-tag">{eu_flag()}Built on Regulation (EU) 2024/1689, the AI Act, as amended by the Digital Omnibus</p>
  <h1>Check an AI idea against the <span class="gold">EU&nbsp;AI&nbsp;Act</span> before anyone builds it.</h1>
  <p class="slede">Send a spreadsheet of proposals. Each comes back with a verdict, the articles behind it,
  its obligations and a short memo. A model reads; the law is applied in code, so the same proposal always
  gets the same answer.</p>
  <p class="actions center"><a class="btn gold lg" href="proposals.html">Open the app</a>
  <a class="btn light lg" href="downloads/screening.xlsx">See a sample result</a></p>
  {f'<a class="live" href="cases.html"><span class="pulse" aria-hidden="true"></span><b>Live</b> {reg["summary"]["in_use"]:,} AI systems in EU public bodies, screened daily · checked {_day(reg["synced"])}</a>' if reg else ""}
  <p class="fine">Portfolio project. The companies are fictional; the law is current to {LEGAL_BASIS_DATE:%d %B %Y}. Not legal advice.</p>
</section>

<a class="window" href="proposals.html" aria-label="Open the proposal intake">
  <div class="win-bar"><i></i><i></i><i></i><span>veredicto / cierzo-seguros / intake</span></div>
  <div class="win-body">
    <div class="win-side">{logo()}<b>Cierzo Seguros</b>
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
  <p class="actions center try"><button type="button" class="btn lg" data-guide="idea">Check your own idea</button></p>
</section>

<section class="sblock" id="how">
  <h2>A model reads. Code decides. A person checks.</h2>
  <p class="ssub">Watch a proposal go through. Every fact has to point at a sentence, or it never reaches the law.</p>
  {demo_html(examples, texts)}
  <div class="cols">
    <div><h3>Read, with receipts</h3><p>An agent turns free text into facts, and must quote the sentence each fact comes from. Code throws out any fact whose quote is not in the proposal.</p></div>
    <div><h3>The law, in code</h3><p>Every Article 5 practice, every Annex III area, the Annex I route, Article 50 and the Article 6(3) derogation, with the dates the Digital Omnibus set. The model never picks the tier.</p></div>
    <div><h3>People where it matters</h3><p>A second reader looks for missed facts. Disputed cases, derogation claims and "significant harm" calls go to a review queue instead of getting a confident answer.</p></div>
  </div>
  <div class="runs"><span>Runs on</span><b>Azure OpenAI</b><b>Claude on Azure Foundry</b><b>Claude API</b><b>Offline, no key</b></div>
</section>

{measured_html(reg, st, n)}

<section class="sblock case">
  <div><p class="eyebrow">Case study</p><h2>Cierzo Seguros, a Spanish health and life insurer</h2>
  <p>Six AI systems classified, the health pricing model tested for harm on {people:,} adults from Spain's official
  health survey, and a dated plan for every gap. One prohibited use blocked before purchase, one obligation already overdue.</p>
  <p class="actions"><a class="btn" href="inventory.html">Read the case study</a><a class="btn ghost" href="evidence.html">See the fairness evidence</a></p></div>
</section>

<footer class="sfoot"><span><b>{PRODUCT}</b> · EU AI Act screening</span>
<span>Built by Marco Ortiz Togashi · <a href="{REPO}">Source on GitHub</a> · Not legal advice</span>
<span class="not-eu">{NOT_EU}</span></footer>
</div>
{js}
{DEMO_JS}"""
    return f"""{head(f"{PRODUCT}: check AI ideas against the EU AI Act", "Screen AI use-case proposals against the EU AI Act: a model reads, code applies the law, people review the hard cases.", "")}
<body class="landing" data-page="index.html">
{body}
<script src="site.js" data-up=""></script>
</body>
</html>
"""


def live_data() -> tuple[dict | None, dict | None]:
    """The live EU cases and stress-test results, if they exist."""
    cs, st = ROOT / "results" / "live" / "eu_cases.json", ROOT / "results" / "generated" / "stress_test.json"
    return (json.loads(cs.read_text("utf-8")) if cs.exists() else None,
            json.loads(st.read_text("utf-8")) if st.exists() else None)


def cases_json(cs: dict) -> str:
    """The list the cases page loads; details live in data/c/<id>.json."""
    rows = [{"i": r["id"], "t": r["title"], "o": r["company"], "c": r["country"], "s": r["tier"],
             "a": r["articles"][:4], "v": int(r["needs_review"]), "p": r["updated"], "st": r["status"],
             "f": r.get("area", "")} for r in cs["results"]]
    return json.dumps({"synced": cs["synced"], "reader": cs.get("reader", ""), "rows": rows},
                      ensure_ascii=False, separators=(",", ":"))


def cases_details(cs: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for r in cs["results"]:
        d = {"u": r["url"], "k": r.get("kind", ""), "y": r.get("start", ""), "x": r["proposal"],
             "f": [[ev["fact"], str(ev["value"]), ev["quote"]] for ev in r["evidence"]], "w": r["review_reasons"]}
        (out / f"{r['id']}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


CASES_JS = """<script>
(async () => {
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const TIER = {prohibited:'Prohibited', high_risk:'High-risk', transparency:'Transparency', minimal:'Minimal'};
  const list = document.getElementById('rg-list'), more = document.getElementById('rg-more');
  const shown = document.getElementById('shown'), q = document.getElementById('rg-q'), ctry = document.getElementById('rg-c');
  let data;
  try { data = await (await fetch('data/cases.json')).json(); }
  catch (e) { list.innerHTML = '<li class="empty">Could not load the case data. Try reloading the page.</li>'; return; }
  const rows = data.rows; let filter = 'use', page = 60, view = rows;
  const sev = s => s === 'high_risk' || s === 'prohibited';
  const inUse = r => r.st === 'Implemented' || r.st === 'Pilot';
  const match = r => filter === 'all' || (filter === 'use' && inUse(r)) || (filter === 'flagged' && inUse(r) && sev(r.s))
    || (filter === 'transparency' && inUse(r) && r.s === 'transparency') || (filter === 'review' && inUse(r) && r.v);
  function render() {
    const term = q.value.trim().toLowerCase(), c = ctry.value;
    view = rows.filter(r => match(r) && (!c || r.c === c) && (!term || (r.t + ' ' + r.o + ' ' + r.f).toLowerCase().includes(term)));
    list.innerHTML = view.slice(0, page).map((r, n) => `<li class="pv" data-k="${n}"><button type="button" class="pv-row">
      <span class="sid">${esc(r.c)}</span>
      <span class="pv-main"><span class="pv-title">${esc(r.t)}</span>
      <span class="pv-co">${esc(r.o)}${r.st ? ' · ' + esc(r.st) : ''}</span></span>
      <span class="stamp ${esc(r.s)}">${TIER[r.s] || esc(r.s)}</span>
      <span class="pv-arts">${esc(r.a.join(', '))}</span>
      <svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg></button></li>`).join('')
      || '<li class="empty">No case matches. Clear the search or pick another filter.</li>';
    shown.textContent = `${view.length.toLocaleString()} of ${rows.length.toLocaleString()}`;
    more.hidden = view.length <= page;
  }
  document.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {
    document.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', String(x === c)));
    filter = c.dataset.filter; page = 60; render();
  }));
  let t; q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { page = 60; render(); }, 120); });
  ctry.addEventListener('change', () => { page = 60; render(); });
  more.addEventListener('click', () => { page += 120; render(); });

  const drawer = document.getElementById('drawer'), scrim = document.getElementById('scrim'), inner = document.getElementById('dr-inner');
  let cur = -1, opener = null;
  const sentences = s => s.split(/(?<=[.!?])\\s+/).filter(Boolean);
  const norm = s => s.toLowerCase().split(/\\s+/).join(' ');
  function body(r) {
    const quotes = r.f.map(f => norm(f[2]));
    const text = sentences(r.x).map(s => {
      const hit = quotes.some(qq => qq && norm(s).includes(qq));
      const facts = r.f.filter(f => norm(s).includes(norm(f[2]))).map(f => `<span class="fchip">${esc(f[0] === 'annex_iii' ? 'Annex III ' + f[1] : f[0] === 'role' ? f[1] : f[0].replace(/_/g, ' '))}</span>`);
      return hit ? `<mark>${esc(s)}</mark><span class="fchips">${[...new Set(facts)].join('')}</span>` : `<span class="dim">${esc(s)}</span>`;
    }).join(' ');
    return `<div class="dr-head"><span class="sid">${esc(r.c)} · ${esc(r.st)}${r.y ? ' · since ' + esc(r.y) : ''}</span><h2 id="dr-title">${esc(r.t)}</h2>
      <span class="co">${esc(r.o)}${r.k ? ' · ' + esc(r.k) : ''}</span><span><span class="stamp ${esc(r.s)}">${TIER[r.s]}</span></span>
      <button type="button" class="x" data-close aria-label="Close"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div>
      <div class="dr-body">
      ${r.w.length ? `<p class="label">Open questions for a person</p><ul class="trace">${r.w.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
      <p class="label">Case description (European Commission catalogue)</p><p class="proposal">${text}</p>
      <p class="label">Articles</p><p class="arts">${r.a.map(a => `<span class="fchip">${esc(a)}</span>`).join('') || '<span class="muted small">None</span>'}</p>
      <p class="small muted">Catalogue entry updated ${esc(r.p)}.</p>
      ${r.u ? `<p><a class="more" href="${esc(r.u)}" target="_blank" rel="noopener">Read about it at the source</a></p>` : ''}</div>`;
  }
  const cache = {};
  async function open(k) {
    const base = view[k]; if (!base) return;
    cur = k;
    if (!cache[base.i]) {
      try { cache[base.i] = await (await fetch(`data/c/${encodeURIComponent(base.i)}.json`)).json(); }
      catch (e) { cache[base.i] = { u: '', k: '', y: '', x: '', f: [], w: ['Could not load this case.'] }; }
    }
    if (cur !== k) return;
    const r = { ...base, ...cache[base.i] };
    inner.innerHTML = body(r);
    drawer.setAttribute('data-open', ''); scrim.setAttribute('data-open', ''); drawer.setAttribute('aria-hidden', 'false');
    document.documentElement.style.overflow = 'hidden';
    inner.querySelector('[data-close]').focus({ preventScroll: true });
    document.getElementById('prev').disabled = k <= 0; document.getElementById('next').disabled = k >= view.length - 1;
  }
  function close() {
    drawer.removeAttribute('data-open'); scrim.removeAttribute('data-open'); drawer.setAttribute('aria-hidden', 'true');
    document.documentElement.style.overflow = ''; cur = -1; if (opener) opener.focus({ preventScroll: true });
  }
  list.addEventListener('click', e => { const b = e.target.closest('.pv-row'); if (!b) return; opener = b; open(+b.parentElement.dataset.k); });
  scrim.addEventListener('click', close);
  drawer.addEventListener('click', e => { if (e.target.closest('[data-close]')) close(); });
  document.getElementById('prev').addEventListener('click', () => open(cur - 1));
  document.getElementById('next').addEventListener('click', () => open(cur + 1));
  document.addEventListener('keydown', e => {
    if (cur < 0) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); open(Math.min(cur + 1, view.length - 1)); }
    if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); open(Math.max(cur - 1, 0)); }
  });
  render();
})();
</script>"""


def _when(iso: str) -> str:
    from datetime import datetime as _dt
    try:
        return _dt.strptime(iso[:16], "%Y-%m-%dT%H:%M").strftime("%d %b %Y, %H:%M UTC")
    except ValueError:
        return iso


def _day(ymd: str) -> str:
    from datetime import datetime as _dt
    try:
        return _dt.strptime(ymd[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return ymd


def count(n: int | float, fmt: str = "{:,}") -> str:
    """A number that counts up when it scrolls into view (site.js); the text is the real value."""
    return f'<span class="num" data-count="{n}">{fmt.format(n)}</span>'


def cases_page(cs: dict) -> str:
    s = cs["summary"]
    rows = cs["results"]
    tiers = s["tiers"]
    hr = s["high_risk_or_prohibited"]
    in_use = [r for r in rows if r["status"] in ("Implemented", "Pilot")]
    chips = [("use", "In use or piloted", s["in_use"]), ("flagged", "Looks high-risk", hr),
             ("transparency", "Transparency only", tiers.get("transparency", 0)),
             ("review", "Needs a person", sum(r["needs_review"] for r in in_use)), ("all", "All, incl. retired", len(rows))]
    filters = "".join(
        f'<button type="button" class="chip" data-filter="{k}" aria-pressed="{"true" if k == "use" else "false"}">'
        f'{e(label)}<span class="n">{n:,}</span></button>' for k, label, n in chips)
    countries = sorted({r["country"] for r in rows})
    opts = '<option value="">All countries</option>' + "".join(f'<option>{e(c)}</option>' for c in countries)
    amax = max((n for _, n, _ in s["by_area"]), default=1)
    areas = "".join(
        f"<li><span class='fa'>{e(a)}</span><span class='fb' role='img' aria-label='{n} in use, {h} look high-risk'>"
        f"<i style='width:{n / amax * 100:.1f}%'></i><b style='width:{h / amax * 100:.1f}%'></b></span>"
        f"<span class='fv mono'>{h}<small> / {n}</small></span></li>" for a, n, h in s["by_area"])
    from src.screener.law import ANNEX_III as _A3
    annex = s["by_annex"]
    xmax = max(annex.values()) if annex else 1
    bars = "".join(
        f"<li><span class='ar'>{e(k.replace('Annex III ', ''))}</span><span class='an'>{e(_A3.get(k.replace('Annex III ', ''), ''))}</span>"
        f"<span class='ab'><i style='width:{v / xmax * 100:.1f}%'></i></span><span class='av mono'>{v}</span></li>"
        for k, v in annex.items())
    share = hr / s["in_use"] if s["in_use"] else 0
    body = f"""
<section class="hero"><div class="page-head"><div>
<p class="kicker">{eu_flag()} <span class="pulse" aria-hidden="true"></span> Live · Commission file of {_day(s['newest'])} · checked {_when(cs['synced'])}</p>
<h1>AI already at work in Europe's public sector</h1>
<p class="lede why">These are real AI systems that public bodies across the EU run today, as catalogued by the European Commission.
Screening each one shows a company getting ready for the AI Act which everyday uses the law treats as high-risk, which only need
a notice to users, and which it leaves alone.</p></div>
<div class="actions"><a class="btn ghost" href="{e(cs.get('page', ''))}" target="_blank" rel="noopener">Open the dataset</a></div></div>
<div class="facts">
<div class="fact"><b>{count(s['in_use'])}</b><span>cases in use or piloted, in {s['countries'] - 1} member states and EU bodies</span></div>
<div class="fact alert"><b>{count(hr)}</b><span>look high-risk or worse on a first pass ({share:.0%})</span></div>
<div class="fact"><b>{count(tiers.get('transparency', 0))}</b><span>only need to tell people they are talking to AI</span></div>
<div class="fact"><b>{count(tiers.get('minimal', 0))}</b><span>fall outside the AI Act's duties</span></div>
</div></section>
<div class="two">
{sec("", "Where the high-risk uses sit", "By government function. The bright part of each bar is the share that looks high-risk.",
     f"<ol class='funcs'>{areas}</ol>")}
{sec("", "Which part of Annex III", "The high-risk areas behind those calls.", f"<ol class='areas'>{bars}</ol>")}
</div>
<section><div class="sec-body">
  <div class="toolbar"><div class="filters" role="group" aria-label="Filter cases">{filters}</div>
  <label class="sr" for="rg-c">Country</label><select id="rg-c" class="search sel">{opts}</select>
  <input id="rg-q" class="search" type="search" placeholder="Search name, body or function" aria-label="Search the cases">
  <p class="shown mono" id="shown" aria-live="polite"></p></div>
  <div class="pvs-head" aria-hidden="true"><span>Country</span><span>Case</span><span>Screener</span><span>Articles</span><span></span></div>
  <ol class="pvs" id="rg-list"><li class="empty">Loading the cases...</li></ol>
  <p class="actions" style="margin-top:12px"><button type="button" class="btn ghost" id="rg-more" hidden>Show more</button></p>
</div></section>
{sec("", "Read these numbers with care", "", f'''<div class="prose"><ul>
<li><b>Source.</b> <a href="{e(cs.get('page', ''))}">Public Sector Tech Watch</a>, the European Commission's catalogue of AI in
public administrations (DIGIT and the Joint Research Centre). Only AI cases in EU member states and EU bodies are kept. The Commission
publishes a new file about once a month; this page checks for one every morning and only re-reads cases that changed.</li>
<li><b>A summary is not a system.</b> Each case is a description written for the catalogue, so the tier is a first pass that a
person should confirm, not a finding about the body that runs it.</li>
<li><b>Read by: {e(cs.get('reader', ''))}.</b> The keyword reader over-calls some cases (a call-centre tool that routes by
"sentiment" reads as emotion recognition) and misses paraphrase; see the <a href="stress.html">stress test</a>. With a model
reader configured, the daily run re-reads every case.</li>
</ul></div>''')}
<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-labelledby="dr-title" aria-hidden="true">
  <div id="dr-inner" class="dr-inner"></div>
  <div class="dr-nav"><button type="button" class="btn ghost" id="prev">Previous</button>
  <button type="button" class="btn ghost" id="next">Next</button></div>
</aside>
{CASES_JS}"""
    return page("cases.html", f"EU public-sector AI · {PRODUCT}", body,
                "Real AI systems run by public bodies across the EU, from the European Commission's catalogue, screened against the AI Act every day.",
                counts={"cases.html": f"{s['in_use']:,}"})


def stress_page(st: dict) -> str:
    styles = [("plain", "Plain wording", "the words a reviewer expects"), ("disguised", "Disguised wording", "the same practice in product language"),
              ("rewritten", "Model-rewritten", "a model's paraphrase of the plain text")]
    bars = "".join(
        f"<li><span class='sl'><b>{e(lbl)}</b><span>{e(note)} · {st['by_style'][k]['n']} proposals</span></span>"
        f"<span class='sb'><i style='width:{st['by_style'][k]['accuracy'] * 100:.1f}%'></i></span>"
        f"<span class='sv'>{st['by_style'][k]['accuracy']:.0%}</span></li>"
        for k, lbl, note in styles if k in st["by_style"])
    tiers = ["prohibited", "high_risk", "transparency", "minimal"]
    cm = {(x["expected"], x["got"]): x["n"] for x in st["confusion"]}
    cmax = max(cm.values()) if cm else 1
    head = "".join(f"<th>{TIER[t]}</th>" for t in tiers)
    rows = "".join(
        f"<tr><td><b>{TIER[a]}</b></td>" + "".join(
            f"<td class='cell heat{' ok' if a == b else (' bad' if tiers.index(b) > tiers.index(a) else '')}' "
            f"style='--h:{cm.get((a, b), 0) / cmax:.2f}'>{cm.get((a, b), 0) or ''}</td>" for b in tiers) + "</tr>"
        for a in tiers)
    misses = "".join(
        f"<li><span class='stamp {m['expected']}'>{TIER[m['expected']]}</span><span class='arrow' aria-hidden='true'>&rarr;</span>"
        f"<span class='stamp {m['got']}'>{TIER[m['got']]}</span><span class='ms'>{e(m['style'])} · {e(m['role'])}</span>"
        f"<p>{e(m['proposal'].split('. ', 1)[1] if '. ' in m['proposal'] else m['proposal'])}</p></li>"
        for m in st["misses"][:24])
    body = f"""
<section class="hero"><div class="page-head"><div>
<p class="kicker">Measured {_when(st['run'])} · {e(st['reader'])}</p>
<h1>Stress test</h1>
<p class="lede">{st['n']} generated proposals across {st['scenarios']} scenarios, each answer written by hand. The same practice is
phrased plainly and in disguise, so the score shows how much the reader leans on keywords.</p></div>
<div class="actions"><a class="btn ghost" href="downloads/generated_proposals.csv">Download the test set</a></div></div>
<div class="facts">
<div class="fact"><b>{st['accuracy']:.0%}</b><span>correct overall</span></div>
<div class="fact"><b>{st['by_style'].get('plain', {}).get('accuracy', 0):.0%}</b><span>plain wording</span></div>
<div class="fact alert"><b>{st['by_style'].get('disguised', {}).get('accuracy', 0):.0%}</b><span>disguised wording</span></div>
<div class="fact alert"><b>{st['under_called_severe']}</b><span>prohibited or high-risk called milder</span></div>
</div></section>
{sec("", "Accuracy by wording", "Same scenarios, same answers; only the words change.", f"<ol class='styles'>{bars}</ol>")}
<div class="two">
{sec("", "What it said, against the right answer", "Rows: the correct tier. Columns: the screener. Red cells are the costly mistake: calling something milder than it is.",
     f"<div class='table-wrap'><table class='matrix'><thead><tr><th></th>{head}</tr></thead><tbody>{rows}</tbody></table></div>")}
{sec("", "Why the score matters", "", '''<div class="prose"><p>The keyword reader finds a practice when the proposal names it.
When the same practice is described in product language ("a wellbeing layer", "surfaces the best fits"), it misses most of them,
and every miss on a prohibited or high-risk system is the dangerous kind.</p><p>That is the case for a model reader, and the quote
check is what makes one safe to use: whatever it reads, it has to point at the sentence.</p><p class="small muted">Labels are written
per scenario by hand, never computed by the classifier, so the test does not grade the code against itself.</p></div>''')}
</div>
{sec("", "Misses", "The first two dozen, with the sentence that should have been caught.", f"<ul class='misses'>{misses}</ul>")}
"""
    return page("stress.html", f"Stress test · {PRODUCT}", body,
                "Generated proposals with hand-written answers, phrased plainly and in disguise, to measure the screener's reader.")


def demo_html(examples: list[dict], texts: dict) -> str:
    """The animated walk-through: sentences light up, facts appear, the law runs, the verdict lands."""
    from src.screener.readers import sentences
    norm = lambda s: " ".join(s.lower().split())  # noqa: E731
    blocks = []
    for n, r in enumerate(examples):
        sents, facts = [], []
        k = 0
        for s in sentences(texts.get(r["id"], "")):
            tags = list(dict.fromkeys(fact_label(ev["fact"], ev["value"]) for ev in r["evidence"]
                                      if norm(ev["quote"]) and norm(ev["quote"]) in norm(s)))
            if tags:
                sents.append(f'<span class="ds q" data-k="{k}">{e(s)}</span>')
                facts += [f'<li data-k="{k}"><span class="fchip">{e(t)}</span></li>' for t in tags]
                k += 1
            else:
                sents.append(f'<span class="ds">{e(s)}</span>')
        arts = " · ".join(r["articles"][:3]) or "no article"
        blocks.append(f"""<div class="demo-ex" data-n="{k}"{"" if n == 0 else " hidden"}>
<div class="demo-col"><p class="label">1 · An agent reads</p><p class="demo-text">{" ".join(sents)}</p>
<p class="demo-co">{e(r['title'])} · {e(r['company'].replace(' (fictional)', ''))}</p></div>
<div class="demo-col"><p class="label">2 · Facts, each with a quote</p><ul class="demo-facts">{"".join(facts)}</ul>
<div class="demo-law"><span class="mono">law.py</span><span class="run"><i></i></span><span class="mono small">{e(arts)}</span></div></div>
<div class="demo-col"><p class="label">3 · Code decides</p><div class="demo-verdict"><span class="stamp {r['tier']}">{TIER[r['tier']]}</span>
<p>{e(r['memo'].split('. ')[0].rstrip('.'))}.</p>{'<span class="flag rv">Sent to a person</span>' if r['needs_review'] else ''}</div></div>
</div>""")
    current = ' aria-current="true"'
    dots = "".join(f'<button type="button" class="dot" aria-label="Example {i + 1}"{current if i == 0 else ""}></button>'
                   for i in range(len(examples)))
    return f'<div class="demo" data-demo>{"".join(blocks)}<div class="demo-dots">{dots}</div></div>'


DEMO_JS = """<script>
(() => {
  const root = document.querySelector('[data-demo]'); if (!root) return;
  const exs = [...root.querySelectorAll('.demo-ex')], dots = [...root.querySelectorAll('.dot')];
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let i = 0, timers = [], visible = true, hover = false;
  const later = (f, ms) => timers.push(setTimeout(f, ms));
  const clear = () => { timers.forEach(clearTimeout); timers = []; };
  function play(n) {
    clear(); i = n;
    exs.forEach((x, k) => { x.hidden = k !== n; x.classList.remove('law', 'done'); x.querySelectorAll('.lit').forEach(el => el.classList.remove('lit')); });
    dots.forEach((d, k) => d.toggleAttribute('aria-current', k === n));
    const ex = exs[n], count = +ex.dataset.n;
    const light = k => ex.querySelectorAll(`[data-k="${k}"]`).forEach(el => el.classList.add('lit'));
    if (still) { for (let k = 0; k < count; k++) light(k); ex.classList.add('law', 'done'); return; }
    for (let k = 0; k < count; k++) later(() => light(k), 500 + k * 750);
    const t = 500 + count * 750;
    later(() => ex.classList.add('law'), t);
    later(() => ex.classList.add('done'), t + 700);
    later(() => { if (visible && !hover) play((i + 1) % exs.length); else later(() => play((i + 1) % exs.length), 1500); }, t + 4200);
  }
  dots.forEach((d, k) => d.addEventListener('click', () => play(k)));
  root.addEventListener('pointerenter', () => hover = true);
  root.addEventListener('pointerleave', () => hover = false);
  new IntersectionObserver(es => { visible = es[0].isIntersecting; }, { threshold: 0.3 }).observe(root);
  play(0);
})();
</script>"""


def measured_html(reg: dict | None, st: dict | None, n_samples: int) -> str:
    cards = [f"""<a class="m" href="proposals.html"><span class="mk">Sample proposals</span><b>{n_samples} / {n_samples}</b>
<p>agree with their labels. A pipeline check only: the keyword reader was tuned on them.</p></a>"""]
    if st:
        p, d = st["by_style"].get("plain", {}).get("accuracy", 0), st["by_style"].get("disguised", {}).get("accuracy", 0)
        cards.append(f"""<a class="m" href="stress.html"><span class="mk">Stress test · {st['n']} generated</span>
<div class="mbars"><span><em>Plain wording</em><i><s style="width:{p * 100:.0f}%"></s></i><b>{p:.0%}</b></span>
<span><em>Disguised</em><i><s class="hot" style="width:{d * 100:.0f}%"></s></i><b>{d:.0%}</b></span></div>
<p>Hand-labelled scenarios, phrased plainly and in disguise. Disguise is where a keyword reader breaks.</p></a>""")
    if reg:
        s = reg["summary"]
        cards.append(f"""<a class="m live-card" href="cases.html"><span class="mk"><span class="pulse" aria-hidden="true"></span> EU public sector, live</span>
<b>{count(s['high_risk_or_prohibited'])} <small>of {s['in_use']:,}</small></b>
<p>AI systems that EU public bodies run today look high-risk on a first pass. Data: European Commission, file of {_day(s['newest'])}.</p></a>""")
    return f"""<section class="sblock" id="measured"><h2>Measured, not claimed.</h2>
<p class="ssub">Every number below is recomputed by the daily run, including the ones that make the free reader look bad.</p>
<div class="meas">{"".join(cards)}</div>
<p class="why-now">Why now: Accenture's <i>Future of Work Trends 2026</i> finds that jobs asking for AI governance skills roughly
tripled between 2022 and 2025 (p. 35). Checking AI ideas early is becoming a routine business task, not a one-off legal review.</p></section>"""


def main() -> int:
    systems, results, rows, ev, tariffs = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy(ROOT / "site_src" / "style.css", OUT / "style.css")
    shutil.copy(ROOT / "site_src" / "site.js", OUT / "site.js")
    shutil.copytree(ROOT / "site_src" / "guide", OUT / "guide")
    # the screener itself, so the guide can check a typed idea in the browser (Pyodide)
    for f in ("src/__init__.py", "src/rules.py", "src/screener/__init__.py", "src/screener/law.py",
              "src/screener/readers.py", "src/screener/pipeline.py", "src/screener/ask.py"):
        (OUT / "py" / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, OUT / "py" / f)
    pages = {
        "index.html": landing(),
        "inventory.html": inventory(systems, results, rows, ev),
        "evidence.html": evidence_page(ev, tariffs),
        "roadmap.html": roadmap_page(rows),
        "proposals.html": proposals_page(),
        "documents.html": documents_page(),
        **({"cases.html": cases_page(live_data()[0])} if live_data()[0] else {}),
        **({"stress.html": stress_page(live_data()[1])} if live_data()[1] else {}),
    }
    (OUT / "downloads").mkdir()
    (OUT / "data").mkdir()
    if live_data()[0]:
        (OUT / "data" / "cases.json").write_text(cases_json(live_data()[0]), encoding="utf-8")
        cases_details(live_data()[0], OUT / "data" / "c")
    if (ROOT / "data" / "generated_proposals.csv").exists():
        shutil.copy(ROOT / "data" / "generated_proposals.csv", OUT / "downloads" / "generated_proposals.csv")
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
