# AI Act readiness: a Spanish health insurer

An EU AI Act readiness assessment for **Cierzo Seguros**, a fictional mid-size Spanish life
and health insurer, done the way a Responsible AI team would do it for a client:

1. **Inventory and classification** of its six AI systems, by a rules engine that cites the
   article behind every step. [Read it](docs/01_classification.md)
2. **Fundamental rights impact assessment** (Article 27) of its health pricing model, with
   evidence from a stand-in model fitted on **real** health spending data.
   [Read it](docs/02_fria_tarifa_salud.md)
3. **Gap assessment and roadmap** against current deadlines, mapped to the Spanish AI
   supervisor's (AESIA) guides. [Read it](docs/03_gap_assessment.md)
4. **Resumen ejecutivo** en español. [Leer](docs/resumen_ejecutivo.md)

Law as of 27 September 2026, including the Digital Omnibus on AI (in force 27 July 2026),
which moved stand-alone high-risk obligations to 2 December 2027 and left chatbot
transparency at 2 August 2026. This is a portfolio project, not legal advice. The company
is invented; any resemblance to a real insurer is unintended.

## What it found

<!-- BEGIN:gap-summary -->
35 obligations on live systems: 5 met, 13 partial, 17 missing. **1 overdue today**, 1 prohibited use to block before purchase.
<!-- END:gap-summary -->

<!-- BEGIN:evidence-headline -->
- **Hispanic applicants pay 1.45x their share of claims** (95% CI 1.27 to 1.66), 15% of the book. Ethnicity is never an input.
- **Applicants in the 'Other or multiple' ethnic group are declined 2.0x as often** as White applicants (4.6% against 2.3%).
- **Smokers are priced 38% below non-smokers**, because the target is one year of spending.
- **The unisex rule holds.** Women pay 1.11x what men pay against 1.53x the cost; the other answers barely reveal sex (AUC 0.59).
<!-- END:evidence-headline -->

| System | Classification | Why |
|---|---|---|
| Tarifa Salud, health pricing | High-risk | Annex III 5(c); profiling rules out the Art 6(3) exit the business claimed |
| Suscripcion Vida, vendor life underwriting | High-risk | Annex III 5(c); deployer duties only, plus the FRIA |
| Asistente Cierzo, chatbot | Transparency | Art 50(1) disclosure, overdue; feeds the health pricing model |
| Voz Calidad, proposed voice analytics | Prohibited | Emotion recognition on staff, Art 5(1)(f); on customers it is high-risk |
| Detector Fraude Siniestros | Minimal | Insurance fraud scoring is not listed in Annex III |
| Tarifa Hogar, home pricing | Minimal | Annex III 5(c) covers life and health only |

## How it works

```
inventory/cierzo_systems.yaml   facts about each system, and current controls
src/rules.py                    AI Act classification and obligations, with citations
src/pricing.py                  the health pricing stand-in (Tweedie GLM on MEPS 2022)
src/evidence.py                 price-to-cost by group, survey-design bootstrap
src/report.py                   renders every table and number into the docs
docs/                           the assessment; prose by hand, figures generated
docs/decisions/                 why the data, the tolerance band and the legacy call
```

Every figure in the documents sits between generated markers, so the prose cannot drift
from the results; CI fails if a document is stale. The Spanish summary quotes numbers by
hand, so a test holds it to the results.

```bash
python -m venv .venv && .venv/Scripts/activate      # or source .venv/bin/activate
pip install -r requirements-dev.txt
python -m scripts.fetch_data                         # MEPS 2022, public, about 6 MB
python -m scripts.run_assessment                     # classify, fit, test, render
pytest
```

## Where it stops

- **US data, Spanish client.** No public Spanish data links a health questionnaire to what
  each person later costs. The method transfers; the levels do not.
  [ADR 0001](docs/decisions/0001-us-data-stand-in.md)
- **The tolerance band was set after a first look** at the results.
  [ADR 0002](docs/decisions/0002-tolerance-band.md)
- **The rules engine covers what an insurer's inventory touches**, not the whole Act:
  no general-purpose model duties, Annex I products or public-sector deployers.
- **Article 111(2)'s cut-off after the Omnibus** is reported inconsistently; the plan does
  not rely on it. [ADR 0003](docs/decisions/0003-legacy-systems.md)

Data: Agency for Healthcare Research and Quality, Medical Expenditure Panel Survey,
HC-243 (2022 Full Year Consolidated Data File).
