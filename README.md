# AI Act readiness · Veredicto

**Is this AI idea legal in the EU? Type it in plain words and get an answer in seconds: which
risk tier it falls in, the article behind it, what it would cost to comply, and the smallest
change that makes it lighter.**

**[Open the live site](https://ma731.github.io/ai-act-readiness/)** (nothing to install)
· [Supply-chain ideas](https://ma731.github.io/ai-act-readiness/supply.html)
· [Insurer case study](https://ma731.github.io/ai-act-readiness/inventory.html)
· [Glossary](#glossary)

The project has two parts:

1. **Veredicto, the screener.** A company sends a spreadsheet of AI ideas; each comes back with
   a verdict, the reason, the obligations and whether a person should double-check it.
2. **A full assessment of one company.** What a Responsible AI team would hand a client: the
   AI Act duties of a (fictional) Spanish health insurer, a fairness test of its pricing
   model on real Spanish data, and a plan with deadlines.

This is a portfolio project, not legal advice. The law is as it stood on 27 September 2026.

---

## The EU AI Act in 60 seconds

The AI Act sorts AI uses into four tiers by how much harm they could do to people.

| Tier | What it means | Example | Worst fine |
|---|---|---|---|
| **Banned** | Not allowed at all | Reading employees' emotions from their voice | EUR 35M or 7% of turnover |
| **High-risk** | Allowed, with heavy duties: risk management, human oversight, records, testing | Screening CVs, pricing health insurance, ranking workers | EUR 15M or 3% |
| **Transparency** | Allowed, but people must be told it's AI | A customer chatbot | EUR 15M or 3% |
| **Minimal** | No AI Act duties | Demand forecasting, route planning, spam filters | none |

Bans apply since February 2025, chatbot notices since August 2026, and most high-risk duties
from December 2027.

---

## Part 1 · Veredicto: check an AI idea

**[Try it](https://ma731.github.io/ai-act-readiness/)**: type an idea, or upload a spreadsheet
on the [proposals page](https://ma731.github.io/ai-act-readiness/proposals.html).

How an idea gets its verdict:

| Step | Done by | In plain words |
|---|---|---|
| 1. Read | AI | Turns the description into facts, and must quote the sentence each fact came from |
| 2. Check | code | Throws away any "fact" whose quote is not really in the text, so the AI cannot make one up |
| 3. Decide | code | Applies the law, article by article, so the same idea always gets the same answer |
| 4. Second opinion | AI | A second reader looks for anything the first one missed |
| 5. Explain | AI + code | Writes a short memo, checked so it only cites articles the decision actually used |
| 6. Escalate | code | Borderline cases go to a person instead of getting a confident guess |

**Why the AI does not decide.** A legal answer has to be predictable and repeatable. So the
AI only reads and explains; plain code applies the law. Without an AI key, a simple keyword
reader runs instead, so the demo always works for free.

**How good is it, honestly:**

- On the 16 sample proposals it agrees with every expected answer, but the free reader was
  tuned on them, so that only proves the pipeline works.
- On a **stress test** of 160 proposals, the free reader gets **96% right when the wording is
  plain, but only 32% when the idea is disguised** ("a wellbeing layer" instead of "emotion
  recognition"). That gap is exactly why you would plug in an AI reader, and the quote check
  is what makes that safe.
- It also screens the **1,360 real AI systems** the EU public sector runs today
  ([live page](https://ma731.github.io/ai-act-readiness/cases.html)), refreshed every morning.

### Supply chain: where the AI Act actually bites

**[Open the page](https://ma731.github.io/ai-act-readiness/supply.html)**: 12 typical
supply-chain AI ideas, each with the answer, the reason, the smallest change that lowers the
tier, and the fine ceiling.

- **7 of 12 have no AI Act duties.** Forecasting, routing and inspecting *things* is left alone.
- **3 are high-risk, and all three judge people at work:** allocating warehouse tasks by
  each worker's pick rate, ranking pickers' productivity, screening CVs for seasonal jobs.
- **1 is banned:** reading call-centre agents' stress from their voices.
- **1 only needs an AI notice.**

The value is in the redesign: "read sentiment from text, not voices" takes the banned idea
to no duties at all. Changing a design before it is built is cheap; after, it is expensive.

---

## Part 2 · The insurer case study

**Cierzo Seguros** is a fictional mid-size health and life insurer in Zaragoza. It is
invented on purpose: claiming a real, named insurer breaks the law would need that
insurer's data. Everything else is real: the law, the survey data and the prices.

| | Question | Document |
|---|---|---|
| 1 | Which of its six AI systems does the AI Act catch, and why? | [Classification](docs/01_classification.md) |
| 2 | Does its health pricing model treat any group unfairly? | [Fundamental rights impact assessment](docs/02_fria_tarifa_salud.md) |
| 3 | What is missing, and by when must it be fixed? | [Gap assessment and roadmap](docs/03_gap_assessment.md) |
| 4 | All of the above on one page, in Spanish | [Resumen ejecutivo](docs/resumen_ejecutivo.md) |

### What it found

<!-- BEGIN:gap-summary -->
35 obligations on live systems: 5 met, 13 partial, 17 missing. **1 overdue today**, 1 prohibited use to block before purchase.
<!-- END:gap-summary -->

| System | What it does | Tier | Why, in plain words |
|---|---|---|---|
| Tarifa Salud | Prices individual health insurance | **High-risk** | Health insurance pricing is on the law's high-risk list. The business argued it only "prepares" a decision, but it profiles people, so that exception does not apply |
| Suscripcion Vida | Vendor tool that rates life insurance applicants | **High-risk** | Same list. Cierzo only uses it, so it carries the user's duties, plus an impact assessment |
| Asistente Cierzo | Customer chatbot | **Transparency** | Must tell people they are talking to an AI. Required since 2 Aug 2026 and not done: **overdue** |
| Voz Calidad | Proposed tool reading emotions from call-centre voices | **Banned** | Reading employees' emotions is prohibited. Must be stopped before purchase |
| Detector Fraude | Scores health claims for fraud | Minimal | Fraud scoring is not on the high-risk list |
| Tarifa Hogar | Prices home insurance | Minimal | The list covers life and health insurance only |

### Is the health pricing fair?

The test asks whether **each group pays for the care it actually uses**. A ratio of 1.00 means
a group pays exactly its share; 1.17 means 17% more per euro of care.

<!-- BEGIN:evidence-headline -->
- **People born abroad would pay 1.17x their share of care costs** (95% CI 0.96 to 1.44): a signal, not a proven breach, because the interval reaches 1.0. Country of birth is never an input.
- **They also go without care because of cost more often**: 2.7% against 1.8% for people born in Spain. Part of their lower use looks like lower access, not lower need.
- **Sex leaks back in, a little.** Sex is not an input, yet women are quoted 1.17x what men are, against 1.12x in cost; the other answers predict sex with AUC 0.66. Within tolerance.
- **The model is calibrated and explainable**: predicted over actual cost 1.005, and the GLM ranks as well as a gradient-boosted challenger (Gini 0.597 against 0.598).
<!-- END:evidence-headline -->

In plain words: nobody is clearly overcharged, but people born abroad are worth watching, and
part of why they look "cheaper" is that they skip care they cannot afford.

---

## Glossary

| Term | Meaning |
|---|---|
| **AI Act** | The EU law on artificial intelligence (Regulation 2024/1689) |
| **Annex III** | The law's list of high-risk uses: hiring, workers, credit, insurance, education and more |
| **Art 5** | The list of banned practices |
| **Art 6(3)** | An exception: a tool that only *prepares* a decision a person makes may not be high-risk, unless it profiles people |
| **Art 50** | The transparency duties, such as telling people they are talking to an AI |
| **Provider / deployer** | Who builds the AI system / who uses it. Each has different duties |
| **FRIA** | Fundamental rights impact assessment: a check of who an AI system could harm |
| **Profiling** | Scoring people on their personal traits or behaviour |
| **Price-to-cost** | What a group is charged per euro of care it uses, compared with everyone else |
| **95% interval** | The range the true value most likely lies in. If it includes 1.0, the result is not proven |
| **GLM** | The simple, explainable statistical model used for the price |
| **Gini, AUC** | Standard scores of how well a model ranks people (higher is better) |
| **Stress test** | 160 test proposals, plain and disguised, with answers written in advance |

---

## For engineers

### Running the screener

```bash
python -m scripts.screen_proposals my_proposals.xlsx    # columns: id, company, title, proposal
```

| Step | Who | What |
|---|---|---|
| 1. Read | agent | turns the proposal into facts, quoting the sentence each fact comes from |
| 2. Verify | code | drops any fact whose quote is not in the proposal, so a reader cannot invent one |
| 3. Classify | code | applies the Act: every Art 5 practice, every Annex III area, the Annex I route, Art 50, the Art 6(3) derogation, the GDPR links ([`law.py`](src/screener/law.py)) |
| 4. Challenge | agent | a second reader hunts for missed facts; code re-classifies if it finds any |
| 5. Explain | agent + code | a memo, checked so it cites only articles the classification used |
| 6. Escalate | code | disputed or judgement-heavy cases go to a human-review queue |

It is a workflow, not a free-roaming agent, on purpose: a legal classification must be
predictable and repeatable, so the model reads and explains and code decides. Without a model
configured, an offline keyword reader runs, so the demo and CI need no key.

**Choosing the model.** Set one of these in your environment (or a `.env` you load); the
screener picks the first one it finds, or the one named in `SCREENER_PROVIDER`.

| Provider | `SCREENER_PROVIDER` | Variables |
|---|---|---|
| OpenAI model on Azure OpenAI | `azure_openai` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT` (your deployment name, e.g. `gpt-4o-mini`) |
| Claude on Azure (Microsoft Foundry) | `foundry` | `ANTHROPIC_FOUNDRY_API_KEY`, `ANTHROPIC_FOUNDRY_RESOURCE`, `SCREENER_MODEL` (your Claude deployment name) |
| Claude API | `anthropic` | `ANTHROPIC_API_KEY` |

Every provider gets the same prompts, the same strict JSON schema and the same quote check,
so swapping models changes who reads, never how the verdict is reached. A run of 16
proposals is three short calls each (read, challenge, memo): cents on a small model.

On the [16 sample proposals](data/proposals_sample.csv) (fictional companies, one per outcome)
the screener agrees with every label and sends the two judgement calls to review: a shift
planner that claims the Art 6(3) exemption while profiling workers, and a toy whose "significant
harm" a person should weigh. **That is a test of the pipeline, not of reading ability:** the
offline reader was tuned on these samples. Measuring the Claude reader needs proposals labelled
by someone other than the person who wrote the rules.

### Live proposals and a stress test, refreshed every morning

Sixteen hand-written samples cannot show whether the screener reads well. Two more sources can:

| | What | Measured |
|---|---|---|
| [EU public sector](https://ma731.github.io/ai-act-readiness/cases.html) | Every AI case in the European Commission's [Public Sector Tech Watch](https://data.europa.eu/data/datasets/e8e7bddd-8510-4936-9fa6-7e1b399cbd92) catalogue from EU member states and EU bodies: real systems public bodies run today, each with an English description | 1,360 cases in use or piloted (file of 2026-09-24); the keyword reader calls 250 of them high-risk or worse on a first pass |
| [Stress test](https://ma731.github.io/ai-act-readiness/stress.html) | 160 generated proposals over 20 scenarios with hand-written answers, each phrased plainly and in disguise ("a wellbeing layer" for emotion recognition) | keyword reader: 96% on plain wording, 32% on disguised; 48 prohibited or high-risk proposals called milder |

The EU cases show a company which everyday uses the AI Act treats as high-risk, which only need a
notice to users, and which it leaves alone. A case is a summary written for the catalogue, so the
tier is a first pass for a person to confirm, not a finding about the body that runs it. The
stress-test gap is the case for a model reader, and the quote check is what makes one safe to use.

```bash
python -m scripts.live_cases             # download the newest catalogue file, screen what is new or changed
python -m scripts.stress_test            # generate the test set and score the reader
python -m scripts.stress_test --rewrite 20   # plus 20 model-rewritten proposals (needs a model)
```

**Auto-update.** The `pages` workflow runs every morning: it asks data.europa.eu for the newest
catalogue file, screens only cases that are new, edited, or were read by an older reader, re-runs
the stress test, keeps the results on the `live-data` branch (so no bot writes to `main`), and
redeploys the site. Add the Azure OpenAI or Foundry variables from the table above as repository
secrets and the daily run uses that model instead of the keyword reader.

**Voice guide.** Every page has a guide (bottom right) that explains the page, the case study and
the live data, and takes typed or spoken questions. Its lines are pre-recorded with a free neural
voice (`python scripts/build_voice.py`, edge-tts, en-US-AvaNeural) and committed, so it works on
GitHub Pages; answers with live numbers use the browser's own voice.

### Where the data comes from

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

### How to read the fairness numbers

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

### How it is built

```
inventory/cierzo_systems.yaml      facts about each AI system and the insurer's current controls
src/rules.py                       AI Act classification and obligations, citing each article
data/tariffs_osakidetza_2024.yaml  the prices, each with page and billing code
src/pricing.py                     turns survey answers into costs; the pricing model (Poisson GLM)
src/evidence.py                    price-to-cost by group, unmet need, bootstrap intervals
src/report.py                      writes every table and number into the documents
src/screener/                      the proposal screener: law.py (the Act, wide), readers.py
                                   (offline, Azure OpenAI and Claude readers, quote guard), pipeline.py
scripts/screen_proposals.py        spreadsheet in, Excel workbook + memos out
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

### Where it stops

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
