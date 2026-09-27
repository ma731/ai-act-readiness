# AI Act readiness: a Spanish health insurer

**Live site: [ma731.github.io/ai-act-readiness](https://ma731.github.io/ai-act-readiness/)**

This project does what a Responsible AI team does for a client: it takes an insurer's AI
systems, works out what the EU AI Act requires of each one, tests the riskiest one for harm
to people, and says what to fix and by when.

The client, **Cierzo Seguros**, is a fictional mid-size health and life insurer in Zaragoza.
It is invented on purpose: publishing a claim that a real, named insurer breaks the law
would need that insurer's data. **Everything else is real**: the law as it stands on
27 September 2026, the survey data and the prices.

This is a portfolio project, not legal advice.

## The four documents

| | What it answers | |
|---|---|---|
| 1 | Which of the insurer's six AI systems does the AI Act catch, and why? | [Classification](docs/01_classification.md) |
| 2 | Does its health pricing model harm anyone, and who? | [Fundamental rights impact assessment](docs/02_fria_tarifa_salud.md) |
| 3 | What is missing, and what is the deadline for each gap? | [Gap assessment and roadmap](docs/03_gap_assessment.md) |
| 4 | The same, in one page, in Spanish | [Resumen ejecutivo](docs/resumen_ejecutivo.md) |

## What it found

<!-- BEGIN:gap-summary -->
35 obligations on live systems: 5 met, 13 partial, 17 missing. **1 overdue today**, 1 prohibited use to block before purchase.
<!-- END:gap-summary -->

| System | What it does | AI Act classification | Why |
|---|---|---|---|
| Tarifa Salud | Prices individual health insurance | **High-risk** | Annex III 5(c) lists health insurance pricing. The business claimed it only "prepares" a decision (Art 6(3)), but it profiles people, which rules that out |
| Suscripcion Vida | Vendor tool that rates life insurance applicants | **High-risk** | Annex III 5(c). Cierzo only uses it, so it has the user's (deployer's) duties, plus the impact assessment |
| Asistente Cierzo | Customer chatbot | **Transparency** | Must tell people they are talking to an AI (Art 50(1)). This has applied since 2 Aug 2026 and is not done: **overdue** |
| Voz Calidad | Proposed tool reading emotions from call-centre voices | **Prohibited** | Reading employees' emotions is banned (Art 5(1)(f)). Reading customers' is high-risk |
| Detector Fraude | Scores health claims for fraud | Minimal | Insurance fraud scoring is not on the Annex III list |
| Tarifa Hogar | Prices home insurance | Minimal | Annex III 5(c) covers life and health insurance only |

**Testing the health pricing model** on real Spanish data found:

<!-- BEGIN:evidence-headline -->
- **People born abroad would pay 1.17x their share of care costs** (95% CI 0.96 to 1.44): a signal, not a proven breach, because the interval reaches 1.0. Country of birth is never an input.
- **They also go without care because of cost more often**: 2.7% against 1.8% for people born in Spain. Part of their lower use looks like lower access, not lower need.
- **Sex leaks back in, a little.** Sex is not an input, yet women are quoted 1.17x what men are, against 1.12x in cost; the other answers predict sex with AUC 0.66. Within tolerance.
- **The model is calibrated and explainable**: predicted over actual cost 1.005, and the GLM ranks as well as a gradient-boosted challenger (Gini 0.597 against 0.598).
<!-- END:evidence-headline -->

## Where the data comes from

The model needs, for each person, the answers they would give on an insurance application,
and what their health care then cost. No public Spanish dataset has both: insurers keep
theirs private. So the project joins two official sources.

**1. The people: INE's health survey.** The *Encuesta Europea de Salud en España 2020* is
Spain's official health interview survey, run by the national statistics institute (INE).
It asks 22,072 adults the same things an insurer asks (diagnosed conditions, how they rate
their health, smoking, height and weight, region) and records how much care each person
used: doctor visits, emergencies, nights in hospital, scans and tests. It also records
country of birth, type of health cover, and whether people went without care they needed.

**2. The prices: the Basque health service's tariff.** Osakidetza publishes what it charges
insurers and other third parties for each kind of care. Every price used here is listed in
[`data/tariffs_osakidetza_2024.yaml`](data/tariffs_osakidetza_2024.yaml) with its page and
billing code, and [`scripts/verify_tariffs.py`](scripts/verify_tariffs.py) checks each one
against the official PDF.

**Joining them.** Each person's care is multiplied by its price. For example, someone who saw
their GP twice in the last four weeks, went to a hospital emergency department once and spent
three nights in hospital costs:

    GP:          2 visits x 13 (four weeks to a year) x EUR 65  = EUR 1,690
    Emergency:   1 visit                            x EUR 257   = EUR   257
    Hospital:    3 nights                           x EUR 1,278 = EUR 3,834
                                                          total = EUR 5,781

Prescriptions, dental, physiotherapy, psychology and childbirth are left out, each for a
stated reason. [ADR 0001](docs/decisions/0001-spanish-data-and-prices.md) lists every
assumption and which way it pushes the cost.

## How to read the fairness numbers

A fair price is not the same price for everyone: people with more health needs cost more.
The question is whether **each group pays for the care it uses**. So the key number is
**price-to-cost**: what a group is charged per euro of care it uses, compared with everyone
else.

- **1.00** means the group pays exactly for its own care.
- **1.17** means it pays 17% more per euro of care than the average person.
- Every figure comes with a **95% interval**, the range the true value plausibly lies in.
  A group is only called over- or undercharged when the whole interval sits outside
  0.80 to 1.25. If the interval crosses a line, the verdict is "inconclusive": worth
  watching, not proven.

## How it is built

```
inventory/cierzo_systems.yaml      facts about each AI system and the insurer's current controls
src/rules.py                       AI Act classification and obligations, citing each article
data/tariffs_osakidetza_2024.yaml  the prices, each with page and billing code
src/pricing.py                     turns survey answers into costs; the pricing model (Poisson GLM)
src/evidence.py                    price-to-cost by group, unmet need, bootstrap intervals
src/report.py                      writes every table and number into the documents
docs/decisions/                    why each important choice was made
```

The documents are written by hand, but **every table and number in them is generated** from
the results, between markers, so the text cannot drift from the data. CI fails if a document
is out of date, and a second CI job re-downloads the public data, rebuilds everything from
scratch and fails if any published number changes.

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m scripts.fetch_data          # INE survey and Osakidetza tariff, about 20 MB
python -m scripts.verify_tariffs      # every price checked against the official PDF
python -m scripts.run_assessment      # classify, build costs, fit, test, write the docs
pytest
```

## Where it stops

- **The cost is built, not observed.** It is care people reported using, priced at one
  region's official tariff, not an insurer's claims. It is on the low side by design.
- **The survey spans COVID-19.** Interviews ran from July 2019 to July 2020; the last four
  months of fieldwork came after the state of alarm, when people used less care.
- **Intervals are slightly too narrow.** The public survey file leaves out the census areas
  the sample was drawn from.
- **The tolerance band was set after a first look at results**, and is not a legal
  threshold. [ADR 0002](docs/decisions/0002-tolerance-band.md)
- **The rules engine covers what an insurer's inventory touches**, not the whole AI Act.
- **One legal date is uncertain.** Sources disagree on the Article 111(2) cut-off after the
  Digital Omnibus, so the plan does not rely on it.
  [ADR 0003](docs/decisions/0003-legacy-systems.md)

Sources: INE, Encuesta Europea de Salud en España 2020 (microdata); Osakidetza, Tarifas para
facturación de servicios sanitarios 2024; Regulation (EU) 2024/1689 as amended by the Digital
Omnibus on AI; AESIA guides.
