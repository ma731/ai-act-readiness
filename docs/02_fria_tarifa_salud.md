# 2. Fundamental rights impact assessment: Tarifa Salud

Article 27 requires a deployer of an Annex III 5(c) system to assess its impact on
fundamental rights before first use and notify the result to the market surveillance
authority. For an insurer that authority is the financial supervisor (Article 74(6)), in
Spain the DGSFP unless the national designation says otherwise. This document follows the
six elements of Article 27(1).

The insurer and its processes are **fictional**. The evidence is not: it comes from a
stand-in for Tarifa Salud built only on official Spanish sources, described in section (d).

## Headline

<!-- BEGIN:evidence-headline -->
- **People born abroad would pay 1.17x their share of care costs** (95% CI 0.96 to 1.44): a signal, not a proven breach, because the interval reaches 1.0. Country of birth is never an input.
- **They also go without care because of cost more often**: 2.7% against 1.8% for people born in Spain. Part of their lower use looks like lower access, not lower need.
- **Sex leaks back in, a little.** Sex is not an input, yet women are quoted 1.17x what men are, against 1.12x in cost; the other answers predict sex with AUC 0.66. Within tolerance.
- **The model is calibrated and explainable**: predicted over actual cost 1.005, and the GLM ranks as well as a gradient-boosted challenger (Gini 0.597 against 0.598).
<!-- END:evidence-headline -->

## (a) The process the system sits in

An applicant for individual health cover answers a questionnaire, directly or through
Asistente Cierzo: age, region, smoking, height and weight, diagnosed conditions and
self-rated health. Tarifa Salud turns the answers into an expected annual cost of care,
applies a loading and returns a premium. It then routes the application:

| Route | Share of applications | Who decides |
|---|---|---|
| Accept at the quoted premium | about 90% | Automatic, no human |
| Refer to an underwriter | about 8% | Underwriter; may accept, load or decline |
| Decline | about 2% | Underwriter confirms |

Factors and relativities are reviewed every January.

## (b) Period and frequency of use

Continuous: every new application and every renewal re-quote, about 60,000 a year
(fictional volume).

## (c) People and groups affected

Adults 18 to 64 applying for individual private health cover in Spain. Groups the
assessment looks at specifically:

- **People born abroad.** Nationality and origin are protected by Article 21 of the Charter,
  and origin by the Race Equality Directive. Cierzo does not ask about either.
- **Women and men**, because EU law forbids sex from changing premiums (Directive 2004/113,
  Article 5, after Test-Achats, C-236/09).
- **People with chronic conditions**, protected in Spanish insurance law: since Ley 4/2018,
  the fifth additional provision of the Insurance Contract Law (Ley 50/1980) lets an insurer
  price or decline on a health condition only for reasons that are justified, proportionate
  and documented beforehand.
- **People in poor self-rated health**, who carry by far the largest loadings.

## (d) Specific risks of harm, with evidence

### How the evidence was produced

A pricing model needs two things per person: the answers they would give on an application,
and what their care then cost. No public Spanish dataset has both, so the stand-in joins two
official sources. [ADR 0001](decisions/0001-spanish-data-and-prices.md) explains every
choice below and what it leaves out.

**The people** come from INE's *Encuesta Europea de Salud en España 2020*: 22,072 adults
interviewed by Spain's statistics institute, with the same questions an insurer asks
(diagnosed conditions, self-rated health, smoking, height and weight, region) and a record of
how much care they used in the past year.

**The prices** come from the Basque public health service's 2024 tariff (Osakidetza), the
prices it bills to insurers and other third parties. Every price below was checked against the
official PDF by [`scripts/verify_tariffs.py`](../scripts/verify_tariffs.py):

<!-- BEGIN:cost-build -->
| Survey answer | Price | Osakidetza 2024 line | Page |
|---|---|---|---|
| GP visits in the last 4 weeks, x13 for a year | EUR 65 | Consulta médica (atención primaria, en centro) (10001485) | 58 |
| Specialist visits in the last 4 weeks, x13 | EUR 119 | Consultas externas: Sucesivas (10001463) | 46 |
| Emergency visits in 12 months, at a hospital | EUR 257 | Urgencias (hospital) (10001461) | 43 |
| Emergency visits in 12 months, elsewhere | EUR 88 | Urgencias médicas en el Centro o P.A.C. (10001489) | 58 |
| Nights in hospital in 12 months (childbirth excluded) | EUR 1,278 | Estancia/día: Hospitalización (10001459) | 13 |
| Admissions with no overnight stay | EUR 346 | Ingreso sin estancia (10002910) | 43 |
| Day-hospital sessions in 12 months | EUR 519 | Hospital de día (médico) (10001464) | 48 |
| Had a CT scan in 12 months (priced as one) | EUR 182 | TAC abdominal (10015035) | 108 |
| Had an MRI (one) | EUR 151 | RM columna lumbar sin contraste (10015212) | 103 |
| Had an ultrasound (one) | EUR 78 | Ecografía abdominal (10015309) | 96 |
| Had an X-ray (one) | EUR 26 | RX abdomen supino (one plain radiograph, 1 URV) (10014904) | 105 |
| Had blood or lab tests (one request) | EUR 34 | Perfil analítico básico y de rutina (10001596) | 51 |
| Plus the handling fee per lab request | EUR 5 | Gestión de pedido (por petición analítica) (10003755) | 51 |

Average cost per adult per year: **EUR 1,110** (hospital nights EUR 474, GP EUR 202, specialists EUR 182, day hospital EUR 101, emergencies EUR 80, tests EUR 71). The median is EUR 65 and 20.9% used no care at all: a few people cost a lot, as in any health book.
<!-- END:cost-build -->

Not priced: prescriptions (standard Spanish private health policies do not pay for them),
dental (a separate product), physiotherapy and psychology (the survey says whether, not how
many sessions) and childbirth (excluded by the survey's hospital questions, and by law from
premiums anyway).

**The model** is a Poisson GLM, the standard shape of an insurance rating table.
[ADR 0004](decisions/0004-poisson-glm.md) explains why it replaced the first choice.

<!-- BEGIN:evidence-model -->
- **People:** INE, Encuesta Europea de Salud en España 2020 (fieldwork 15 Jul 2019 to 24 Jul 2020). Adults 18 to 64 with complete answers: **14,336 people**, weighted to 29.4 million; 1,791 born abroad, 2,772 with private cover.
- **Prices:** Osakidetza, Tarifas 2024 (data/tariffs_osakidetza_2024.yaml).
- **Model:** Poisson GLM (log link), survey-weighted; 5-fold cross-fitting, so every price is out-of-sample.
- **Accuracy:** Gini 0.597 (GBM challenger 0.598); predicted over actual cost 1.005.
- **Self-rated health** is the strongest factor: very good 0.62, fair 3.06, bad 7.00, very bad 13.31 (base: good).
- **Diagnosed conditions:** cancer 2.27, other heart 1.85, stroke 1.64, kidney disease 1.57, heart attack 1.42, diabetes 1.37, chronic anxiety 1.36, coronary disease 1.33, asthma 1.22, hypertension 1.12, chronic low back pain 1.03, depression 1.02, high cholesterol 0.91, COPD 0.90, osteoarthritis 0.89.
- **Smoking** (base: never): daily 0.87, former 1.28.
- **Age** (base: 35-44): 18-24 1.15, 55-64 0.82, once conditions and health are known.
<!-- END:evidence-model -->

**A check that the data make sense.** The model's age factors fall with age, which no rate
table would show. That is not an error: raw cost does rise with age, but once someone's
diagnoses and self-rated health are known, age adds little, because that is where older
people's extra cost shows up.

<!-- BEGIN:evidence-age -->
| Age | People | Average cost | Diagnosed conditions | Fair or worse health |
|---|---|---|---|---|
| 18-24 | 1,082 | EUR 743 | 0.20 | 7.3% |
| 25-34 | 1,824 | EUR 898 | 0.35 | 10.3% |
| 35-44 | 3,633 | EUR 969 | 0.49 | 14.4% |
| 45-54 | 3,886 | EUR 1,143 | 0.88 | 20.6% |
| 55-64 | 3,911 | EUR 1,606 | 1.54 | 29.8% |
<!-- END:evidence-age -->

Smoking follows a pattern epidemiologists know well: former smokers cost the most, because
many people quit after falling ill, while current smokers' costs have mostly not arrived yet.

### How to read the fairness tables

The fairness question for a price is not "do groups pay the same?". They should not, if their
risk differs. It is "does each group pay for the care it uses?". So each table shows:

- **Premium index:** the group's average price against the book's (1.10 = 10% above average).
- **Cost index:** the group's average actual cost against the book's.
- **Price-to-cost:** premium index divided by cost index. 1.00 means the group pays exactly
  for its own care; 1.20 means it pays 20% more per euro of care than everyone else.
- **95% CI:** the range the true figure plausibly sits in, from 400 resamples of the survey.
- **Verdict:** over- or undercharged only when the whole interval is outside 0.80 to 1.25
  ([ADR 0002](decisions/0002-tolerance-band.md)); "inconclusive" when it straddles a line.

### Risk 1: people born abroad pay more than their care costs

<!-- BEGIN:evidence-born -->
| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | Verdict | Declined | Referred |
|---|---|---|---|---|---|---|---|
| Born abroad | 1,791 | 1.11 | 0.95 | **1.17** (0.96 to 1.44) | inconclusive | 2.0% (1.2% to 2.7%) | 9.6% (8.1% to 11.2%) |
| Born in Spain | 12,545 | 0.97 | 1.01 | **0.96** (0.92 to 1.01) | within tolerance | 2.1% (1.8% to 2.4%) | 7.6% (7.1% to 8.2%) |
<!-- END:evidence-born -->

People born abroad are quoted above average but use slightly less care than average, so per
euro of care they pay more. The model never sees country of birth: the gap comes through
the answers they give. The interval reaches 1.0, so this is a signal to monitor, not a proven
breach. It holds at the same level among people who already have private cover:

<!-- BEGIN:evidence-private -->
Only the 2,772 people who already hold private cover:

| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | Verdict | Declined | Referred |
|---|---|---|---|---|---|---|---|
| Born abroad | 244 | 1.02 | 0.88 | **1.17** (0.88 to 1.54) | inconclusive | 0.7% (0.1% to 1.5%) | 7.5% (4.2% to 11.1%) |
| Born in Spain | 2,528 | 1.00 | 1.02 | **0.98** (0.95 to 1.02) | within tolerance | 1.4% (0.9% to 1.8%) | 6.1% (5.0% to 7.2%) |
<!-- END:evidence-private -->

**Is it lower need or lower access?** The survey can partly answer, because it asks whether
people went without care they needed:

<!-- BEGIN:evidence-unmet -->
| In the last 12 months | Born abroad | Born in Spain |
|---|---|---|
| Went without care because of waiting lists | 11.1% (9.5% to 12.8%) | 12.0% (11.3% to 12.6%) |
| Went without care because of transport | 0.9% (0.4% to 1.4%) | 0.9% (0.8% to 1.1%) |
| Went without medical care because of cost | 2.7% (1.8% to 3.6%) | 1.8% (1.5% to 2.1%) |
<!-- END:evidence-unmet -->

People born abroad go without medical care because of cost more often than people born in
Spain (the intervals only just overlap), while waiting lists and transport affect both groups
about equally. Some of their lower
use is therefore missed care, not lower need. A price built on past use would charge them as
if they were sicker than the care they receive shows, which is the harm to watch.

What does **not** fix it: adding country of birth or nationality as a factor. That would be
direct discrimination. What can be done is in (f).

### Risk 2: routing differs by group

Decline rates are about equal, but people born abroad are referred to an underwriter more
often (see the Risk 1 table; the intervals only just overlap). A referral means delay and a human judgement the applicant cannot see.
Underwriters today see only the model's recommendation, not how often it lands on each group.

### Risk 3: sex leaks back in through other answers

<!-- BEGIN:evidence-sex -->
| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | Verdict | Declined | Referred |
|---|---|---|---|---|---|---|---|
| Female | 7,239 | 1.08 | 1.05 | **1.02** (0.95 to 1.10) | within tolerance | 2.3% (1.9% to 2.7%) | 9.1% (8.4% to 10.0%) |
| Male | 7,097 | 0.92 | 0.95 | **0.98** (0.90 to 1.07) | within tolerance | 1.8% (1.5% to 2.2%) | 6.8% (6.2% to 7.6%) |
<!-- END:evidence-sex -->

Sex is not an input, but women report more of some conditions and rate their health lower,
so the model quotes them a little more than their care costs. The gap is within tolerance,
and pregnancy and maternity costs, which Directive 2004/113 Article 5(3) keeps out of premiums,
are already excluded from the cost. It needs watching at each re-rating, because a new factor
that correlates with sex could widen it.

### Risk 4: loadings for conditions that do not predict cost

Under Ley 4/2018 each loading on a health condition needs a documented actuarial reason. In
the list above, several conditions come out at or below 1.00 once the other answers are known,
including osteoarthritis, COPD and high cholesterol. If Cierzo's underwriting manual loads them
anyway, those loadings are not supported by this evidence.

### Risk 5: one subjective answer drives the price

Self-rated health moves the price more than any diagnosis. It predicts cost well, but it is a
self-assessment, not a diagnosis: applicants who answer candidly pay more than those who do
not, and the answer follows social class even at the same age:

<!-- BEGIN:evidence-class -->
| Social class of the household | People | Rate their health fair or worse (age-standardised) |
|---|---|---|
| 1 Managers of large firms, professionals | 1,693 | 10.8% |
| 2 Managers of small firms, associate professionals | 1,206 | 12.5% |
| 3 Intermediate occupations, self-employed | 2,880 | 15.4% |
| 4 Supervisors, skilled technical workers | 1,845 | 18.8% |
| 5 Skilled primary sector, semi-skilled workers | 4,411 | 20.6% |
| 6 Unskilled workers | 1,869 | 22.9% |
<!-- END:evidence-class -->

So the heaviest factor in the price also moves with class. Ley 4/2018 asks for objective
reasons, and a price that rests this heavily on one self-assessment needs that justification
written down, and its effect by class monitored.

### Risk 6: automation without explanation

About 90% of applications are accepted with no human involved, and nobody is told a model set
their price. Article 26(11) requires telling applicants, Article 86 gives them a right to an
explanation, and GDPR Article 22 applies to a solely automated price.

## (e) Human oversight

| Today | Proposed |
|---|---|
| Underwriters see refers and declines only | Monthly report of routes and price-to-cost by group, reviewed by the pricing committee |
| No authority to override a price | Underwriters may override price and route, with a logged reason (Article 14) |
| No guidance on the model's limits | Instructions for use naming the one-year horizon, the weight on self-rated health and the groups to watch (Article 13) |
| Logs kept 90 days | Logs kept at least six months (Article 26(6)) |

## (f) If the risks materialise

1. **Measure on Cierzo's own book.** Run this analysis on real applications and claims,
   using Article 10(5) to process origin data for bias detection only, with the DPO's
   sign-off and deletion afterwards.
2. **Price need, not only past use.** Blend in external morbidity data, or cap how far one
   year of low use can pull a group's price, then re-check Risk 1.
3. **Justify every loading** in writing, as Ley 4/2018 requires, and drop the ones the data
   do not support.
4. **Referral review.** Any group whose referral or decline rate stays well above the
   book's triggers a review of those cases and the rules behind them.
5. **Complaints.** Applicants can ask for the explanation Article 86 gives them through
   Cierzo's customer service department, with escalation to the DGSFP.
6. **Governance.** The pricing committee owns this assessment, reviews it at each annual
   re-rating (a re-rating is also when Article 27(2) requires an update), and reports
   breaches of the tolerance band to the board risk committee.
