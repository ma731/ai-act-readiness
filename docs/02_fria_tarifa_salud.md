# 2. Fundamental rights impact assessment: Tarifa Salud

Article 27 requires a deployer of an Annex III 5(c) system to assess its impact on
fundamental rights before first use and notify the result to the market surveillance
authority. For an insurer that authority is the financial supervisor (Article 74(6)), in
Spain the DGSFP unless the national designation says otherwise. This document follows the
six elements of Article 27(1).

The client and its processes are **fictional**. The evidence is not: it comes from a
stand-in for Tarifa Salud fitted on real health spending data, described in section (d).

## Headline

<!-- BEGIN:evidence-headline -->
- **Hispanic applicants pay 1.45x their share of claims** (95% CI 1.27 to 1.66), 15% of the book. Ethnicity is never an input.
- **Applicants in the 'Other or multiple' ethnic group are declined 2.0x as often** as White applicants (4.6% against 2.3%).
- **Smokers are priced 38% below non-smokers**, because the target is one year of spending.
- **The unisex rule holds.** Women pay 1.11x what men pay against 1.53x the cost; the other answers barely reveal sex (AUC 0.59).
<!-- END:evidence-headline -->

## (a) The process the system sits in

An applicant for individual health cover answers a questionnaire, directly or through
Asistente Cierzo: age, province, smoking, diagnosed conditions and self-rated health.
Tarifa Salud turns the answers into an expected annual cost, applies a loading and returns a
premium. It then routes the application:

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

- **By sex**, because EU law forbids sex from changing premiums (Directive 2004/113,
  Article 5, after Test-Achats, C-236/09).
- **By ethnic or migrant origin**, protected by Article 21 of the Charter and the Race
  Equality Directive, and never collected by Cierzo.
- **People with chronic conditions**, protected in Spanish insurance law: since Ley 4/2018,
  the fifth additional provision of the Insurance Contract Law (Ley 50/1980) lets an insurer
  price or decline on a health condition only for reasons that are justified, proportionate
  and documented beforehand.
- **Smokers and people in poor self-rated health**, who carry the largest loadings.

## (d) Specific risks of harm, with evidence

### How the evidence was produced

No public Spanish dataset links an application questionnaire to what each person later
costs. So the stand-in is fitted on **MEPS 2022**, the US federal survey of health spending,
restricted to the population a private health insurer prices. It asks exactly what Cierzo's
questionnaire asks. US regions stand in for provinces and US ethnicity categories stand in
for origin; [ADR 0001](decisions/0001-us-data-stand-in.md) sets out what transfers to Spain
and what does not.

<!-- BEGIN:evidence-model -->
- Data: MEPS HC-243, 2022 Full Year Consolidated (AHRQ); adults 18-64 with any private cover, questionnaire answered; **8,166 people** weighted to 144.7 million.
- Model: Tweedie GLM (power 1.6, log link), survey-weighted; 5-fold cross-fitting, households kept within a fold.
- Ranking power: Gini **0.387** for the GLM against 0.339 for a gradient-boosted challenger, so the explainable model is also the better one.
- Book level: predicted over actual cost 1.014.
- Smokers: relativity **0.62** against non-smokers.
- Self-rated health: excellent 0.57, poor 2.01 (base: good).
- Conditions: arthritis 1.90, coronary heart disease 1.70, cancer 1.69, asthma 1.45, stroke 1.32, diabetes 1.29, emphysema 1.05, high blood pressure 0.97, high cholesterol 0.96.
- Sex is not an input. Women pay **1.11x** what men pay and cost 1.53x as much. With sex as a factor the ratio would be 1.65x. Sex is only weakly recoverable from the other answers (AUC 0.59).
<!-- END:evidence-model -->

The fairness metric is **relative price-to-cost**: what a group is charged per euro of its
actual claims, divided by the same figure for the whole book. 1.00 is a fair share. The
tolerance band of 0.80 to 1.25 is explained, including when it was set, in
[ADR 0002](decisions/0002-tolerance-band.md). A group is called over- or undercharged only
when its whole 95% interval sits outside the band.

### Risk 1: a group pays for claims it does not make

<!-- BEGIN:evidence-ethnicity -->
| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | Verdict | Declined | Referred |
|---|---|---|---|---|---|---|---|
| Asian | 669 | 0.85 | 0.80 | **1.07** (0.88 to 1.31) | inconclusive | 1.5% (0.8% to 2.3%) | 2.4% |
| Black | 1,032 | 1.00 | 0.85 | **1.17** (1.05 to 1.32) | inconclusive | 1.9% (1.2% to 2.7%) | 8.8% |
| Hispanic | 1,360 | 0.90 | 0.62 | **1.45** (1.27 to 1.66) | overcharged | 1.1% (0.7% to 1.6%) | 6.1% |
| Other or multiple | 249 | 1.13 | 0.91 | **1.24** (0.97 to 1.60) | inconclusive | 4.6% (2.8% to 6.7%) | 5.8% |
| White | 4,856 | 1.04 | 1.15 | **0.90** (0.88 to 0.93) | within tolerance | 2.3% (1.8% to 2.6%) | 9.3% |
<!-- END:evidence-ethnicity -->

Hispanic applicants are quoted slightly below average, but they cost much less than
average, so per euro of claims they pay far more than anyone else. The model is not using
ethnicity. At the same age, region and diagnoses, this group simply spends less on health
care in the data.

Whether that is lower *need* or lower *use* is the question the data cannot answer, and it
decides what the finding means. If it is lower use (language, time off work, distrust),
then Cierzo would be charging a group full price for care it does not get. Either way the
group is funding part of everyone else's cover.

What does **not** fix it: adding ethnicity as a factor. That is unlawful and would need
data Cierzo must not collect for pricing. What can be done is covered in (f).

The Spanish analogue to test is migrant origin, which is also not collected. Article 10(5)
of the AI Act, extended by the Omnibus to all AI systems, allows special category data to
be processed strictly to detect and correct bias, under safeguards. That is the legal route
to measure this on Cierzo's own book instead of on US data.

### Risk 2: declines fall unevenly

The decline route is 2% of applications overall, but the table shows it is not spread
evenly. A decline is the most serious outcome here: it denies access to the service, not
just a higher price. Each decline is confirmed by an underwriter, but underwriters see only
the model's recommendation, not how often it lands on each group.

### Risk 3: the model rewards smoking

Priced on one year of spending, smokers come out cheaper than non-smokers. That is the
wrong horizon: smoking costs arrive over decades, and the policy renews. No insurer would
file this relativity. It matters for rights less than for Article 10 (relevant data) and
Article 15 (accuracy), and it shows why a one-year cost target cannot be taken at face
value, which is also part of the explanation for Risk 1.

### Risk 4: sex re-enters through the back door

<!-- BEGIN:evidence-sex -->
| Group | People | Premium index | Cost index | Price-to-cost (95% CI) | Verdict | Declined | Referred |
|---|---|---|---|---|---|---|---|
| Female | 4,269 | 1.05 | 1.21 | **0.87** (0.82 to 0.91) | within tolerance | 2.2% (1.8% to 2.6%) | 9.2% |
| Male | 3,897 | 0.95 | 0.79 | **1.20** (1.12 to 1.31) | inconclusive | 1.9% (1.5% to 2.3%) | 7.0% |
<!-- END:evidence-sex -->

This is the cross-subsidy the law requires: women cost more than men in this age range and
pay only slightly more, so men pay above their share. The unisex rule is working. The
residual difference in women's premiums comes from the other answers, which are only weakly
linked to sex. Two things to watch: pregnancy and maternity costs must not raise premiums at
all (Directive 2004/113, Article 5(3)), and this data cannot separate them out.

### Risk 5: loadings for conditions that do not predict cost

Under Ley 4/2018 each loading on a health condition needs a documented actuarial reason.
Several conditions on the questionnaire come out near 1.00 once the other answers are known,
high blood pressure and high cholesterol among them. If Cierzo's underwriting manual loads
them anyway, those loadings are not documented by this model.

### Risk 6: automation without explanation

About 90% of applications are accepted with no human involved, and nobody is told a model
set their price. Article 26(11) requires telling applicants, Article 86 gives them a right to
an explanation, and GDPR Article 22 applies to a solely automated price.

## (e) Human oversight

| Today | Proposed |
|---|---|
| Underwriters see refers and declines only | Monthly report of routes and price-to-cost by group, reviewed by the pricing committee |
| No authority to override a price | Underwriters may override price and route, with a logged reason (Article 14) |
| No guidance on the model's limits | Instructions for use naming the one-year target and the groups it misprices (Article 13) |
| Logs kept 90 days | Logs kept at least six months (Article 26(6)) |

## (f) If the risks materialise

1. **Measure on Cierzo's own book.** Run this analysis on real applications and claims,
   using Article 10(5) to process origin data for bias detection only, with the DPO's
   sign-off and deletion afterwards.
2. **Fix the target before the factors.** Price on a multi-year cost horizon, or blend in
   external mortality and morbidity tables, then re-check Risk 1 and Risk 3.
3. **Justify every loading** in writing, as Ley 4/2018 requires, and drop the ones the data
   does not support.
4. **Decline review.** Any group whose decline rate stays above twice the book's rate
   triggers a manual review of the declines and the underwriting rules behind them.
5. **Complaints.** Applicants can ask for the explanation Article 86 gives them through
   Cierzo's customer service department, with escalation to the DGSFP.
6. **Governance.** The pricing committee owns this assessment, reviews it at each annual
   re-rating (a re-rating is also when Article 27(2) requires an update), and reports
   breaches of the tolerance band to the board risk committee.
