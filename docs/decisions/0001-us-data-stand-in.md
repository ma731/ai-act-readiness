# ADR 0001: US survey data as the stand-in for a Spanish book

**Decision.** Fit the Tarifa Salud stand-in on MEPS 2022 (AHRQ, HC-243).

**Why.** The FRIA needs a model whose price can be compared with what each person actually
went on to cost. No public Spanish source has that: INE's national health survey has the
questionnaire but not the spending, and insurers' books are private. MEPS has both, for
22,431 people, with survey weights and a published variance design.

**What transfers.** The mechanics: how a questionnaire-based GLM spreads cost, how a
one-year cost target behaves, how far protected traits leak through other answers, and how
routes land on groups. The method runs unchanged on Cierzo's own data.

**What does not.** The levels. US health spending, US access to care and US ethnic
categories are not Spain's. The Hispanic finding is evidence that a cost-trained price can
overcharge a group whose use of care is low, not a claim about any group in Spain. Region
stands in for province only as a rating factor of the same kind.

**Cohort.** Adults 18 to 64 with any private cover in 2022, who answered the round 5
questions: 8,166 people. People who skipped those questions are dropped. An applicant cannot
skip them, and in the survey skipping tracked hospitalisation or death: kept in, it was a
3.2x relativity, a leak rather than a rating factor.
