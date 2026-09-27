# ADR 0001: Spanish survey data, priced with an official Spanish tariff

## Decision

Build the Tarifa Salud stand-in from two official Spanish sources:

- **People:** INE, *Encuesta Europea de Salud en España 2020* (EESE), adult microdata.
- **Prices:** Osakidetza (Basque public health service), *Tarifas 2024*.

## Why not something else

The first version of this project used MEPS, the US federal health spending survey, because
it has both questionnaire answers and each person's actual spending. That was replaced: US
spending, US access to care and US ethnic categories cannot say anything reliable about a
Spanish insurer's applicants.

No public Spanish dataset links application answers to what each person later costs: insurers'
books are private. So the cost is built: the survey records how much care each person used,
and an official tariff says what each unit of care costs.

## Why these two sources

**EESE 2020** is Spain's official health interview survey, run by INE as part of the European
Health Interview Survey. It asks what an insurer's questionnaire asks (doctor-diagnosed
conditions, self-rated health, smoking, height and weight, region), plus country of birth,
type of health cover, use of care over the last 4 weeks and 12 months, and whether people
went without care they needed. It comes with survey weights.

**Osakidetza's tariff** is the list of prices the Basque health service bills to third parties
that owe the cost of care, such as insurers and mutuals. That is the cost concept an insurer
prices. One tariff covers every kind of care needed here, so every price comes from one
consistent source, and each line is checked against the official PDF by
[`scripts/verify_tariffs.py`](../../scripts/verify_tariffs.py).

## How cost is built, and the assumptions it makes

| Assumption | Why | Effect |
|---|---|---|
| Visits in the last 4 weeks x 13 = visits in a year | The survey only counts visits over 4 weeks | Right on average, noisy per person; the model estimates the average |
| Every specialist visit priced as a follow-up (119), not a first visit (238) | The survey does not say which | Cost is on the low side |
| Scans and lab tests priced as one each | The survey asks yes or no over 12 months | Cost is on the low side |
| One region's prices for all of Spain | One consistent official source | Regional factors reflect use of care, not price differences |
| Prescriptions, dental, physiotherapy, psychology left out | Not covered by standard policies, or counts not recorded | Cost covers the core of a health policy only |
| Childbirth left out | The survey's hospital questions exclude it; EU law keeps maternity out of premiums | Consistent with Directive 2004/113, Art 5(3) |
| "Don't know" or "no answer" to a count makes the year unknown | Guessing zero would understate cost | Those people are dropped (a small number) |

## Who is in the cohort

Adults 18 to 64 with complete answers: 14,336 people. The main analysis uses all of them, not
only the 2,772 who already hold private cover, because an insurer prices applicants who come
from the whole population, and 244 people born abroad with private cover are too few to
measure much. The private-cover group is rerun separately as a check.

## Known limits

- **COVID-19.** Fieldwork ran from 15 July 2019 to 24 July 2020, so the last four months of
  fieldwork came after the state of alarm (14 March 2020), when use of care dropped. INE calibrated the
  weights separately for the two periods, but the public file does not say which period each
  interview belongs to. This lowers the overall level of cost; group comparisons are affected
  only if groups were interviewed in different proportions after March 2020.
- **Intervals.** The sample was drawn by census section within region; the public file does
  not include the sections, so the bootstrap resamples people within region. The intervals
  are therefore somewhat too narrow.
- **Self-report.** Use of care is what people remember and report, not claims records.
