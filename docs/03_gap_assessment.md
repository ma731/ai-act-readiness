# 3. Gap assessment and roadmap

Every obligation the classification produced, set against Cierzo's current controls
(recorded in the inventory as met, partial or missing), and ordered by urgency.

<!-- BEGIN:gap-summary -->
35 obligations on live systems: 5 met, 13 partial, 17 missing. **1 overdue today**, 1 prohibited use to block before purchase.
<!-- END:gap-summary -->

## Roadmap

<!-- BEGIN:roadmap -->
**Now: prohibited or overdue**

- S4 Voz Calidad: Art 5(1)(f)
- S2 Asistente Cierzo: Art 50(1)

**Now: in force, partly done**

- S1 Tarifa Salud: Art 4
- S2 Asistente Cierzo: Art 4

**By 2 Dec 2026**

- S2 Asistente Cierzo: Art 50(2)

**By 2 Dec 2027, when high-risk duties apply**

- S1 Tarifa Salud: Art 9, Art 10, Art 11, Art 12, Art 13, Art 14, Art 15, Art 17, Art 43, Art 47-48, Art 49(1), Art 72-73, Art 26(1), Art 26(2), Art 26(5), Art 26(6), Art 26(11), Art 86, Art 27
- S5 Suscripcion Vida: Art 26(1), Art 26(4), Art 26(5), Art 26(6), Art 26(11), Art 86, Art 27
<!-- END:roadmap -->

### Why plan for December 2027 at all

Tarifa Salud and Suscripcion Vida were in service before the high-risk rules apply. Under
Article 111(2), the high-risk duties reach such a system only once its design changes
significantly. That is a real argument, but not a plan: Tarifa Salud is re-rated every
January, and a re-rating that adds a factor or changes the model form is the obvious
candidate for a significant change. The post-Omnibus cut-off date also needs confirming
against Regulation (EU) 2026/1744. [ADR 0003](decisions/0003-legacy-systems.md) records the
choice to plan as if the duties apply on 2 December 2027. Articles 4, 5 and 50 get no such
relief.

## Where AESIA's guides help

Spain's AI supervisor published 16 guides after its regulatory sandbox, with a checklist
manual for self-assessment. Each high-risk gap maps to one of them, so the remediation work
can follow the guide rather than start from the article text:

| Article | AESIA guide |
|---|---|
| Art 9 risk management | 05 Gestión de riesgos |
| Art 10 data governance | 07 Datos y gobernanza de datos |
| Art 11 technical documentation | 15 Documentación técnica |
| Art 12 logging | 12 Registros |
| Art 13 transparency to deployers | 08 Transparencia |
| Art 14 human oversight | 06 Vigilancia humana |
| Art 15 accuracy, robustness, cybersecurity | 09 Precisión, 10 Solidez, 11 Ciberseguridad |
| Art 17 quality management | 04 Sistema de gestión de la calidad |
| Art 43 conformity assessment | 03 Evaluación de conformidad |
| Art 72 post-market monitoring | 13 Vigilancia poscomercialización |
| Art 73 serious incidents | 14 Gestión de incidentes |
| Self-assessment across all of the above | 16 Manual de checklist |

Source: [aesia.digital.gob.es/es/guias](https://aesia.digital.gob.es/es/guias).

## Every obligation

<!-- BEGIN:gaps -->
| Priority | System | Article | Duty | Holder | Current state | Status |
|---|---|---|---|---|---|---|
| 1 | S4 | Art 5(1)(f) | Do not use on employees; remove that capability | deployer | not assessed | **Block before purchase** |
| 2 | S2 | Art 50(1) | Tell users they are talking to an AI, clearly, at first interaction | provider | Missing: Persona 'Luz' is not labelled as AI anywhere. | **OVERDUE** |
| 3 | S1 | Art 4 | Support AI literacy of staff who operate or use it (as softened by the Omnibus) | provider | Partial: Actuaries trained; underwriters and sales are not. | In force, partial |
| 4 | S2 | Art 4 | Support AI literacy of staff who operate or use it (as softened by the Omnibus) | provider | Partial: Product team trained; contact centre is not. | In force, partial |
| 5 | S3 | Art 4 | Support AI literacy of staff who operate or use it (as softened by the Omnibus) | provider | Met: Investigators trained on score limits annually. | Done |
| 6 | S4 | Art 4 | Support AI literacy of staff who operate or use it (as softened by the Omnibus) | deployer | not assessed | Pre-deployment |
| 7 | S5 | Art 4 | Support AI literacy of staff who operate or use it (as softened by the Omnibus) | deployer | Met: Underwriters trained by vendor. | Done |
| 8 | S6 | Art 4 | Support AI literacy of staff who operate or use it (as softened by the Omnibus) | provider | Met: Pricing team trained. | Done |
| 9 | S4 | Art 50(3) | Inform people exposed to emotion recognition | deployer | not assessed | Pre-deployment |
| 10 | S2 | Art 50(2) | Mark generated text or audio as AI-made, machine-readably | provider | Missing: Generated replies carry no machine-readable mark. | Due 02 Dec 2026 (3 mo) |
| 11 | S1 | Art 9 | Risk management system across the lifecycle | provider | Partial: Model risk policy exists; no AI-specific risk register. | Due 02 Dec 2027 (15 mo) |
| 12 | S1 | Art 10 | Data governance: relevant, representative, bias examined | provider | Missing: No bias examination of training data on record. | Due 02 Dec 2027 (15 mo) |
| 13 | S1 | Art 11 | Technical documentation (Annex IV) | provider | Partial: Actuarial pricing memo; not Annex IV structured. | Due 02 Dec 2027 (15 mo) |
| 14 | S1 | Art 12 | Automatic event logging | provider | Partial: Quotes logged 90 days; override reasons not logged. | Due 02 Dec 2027 (15 mo) |
| 15 | S1 | Art 13 | Instructions for use for deployers | provider | Missing: No instructions for use for underwriters. | Due 02 Dec 2027 (15 mo) |
| 16 | S1 | Art 14 | Designed for effective human oversight | provider | Partial: Underwriters see refers only; no override guidance. | Due 02 Dec 2027 (15 mo) |
| 17 | S1 | Art 15 | Accuracy, robustness, cybersecurity declared and met | provider | Partial: Accuracy tracked (Gini); no robustness tests. | Due 02 Dec 2027 (15 mo) |
| 18 | S1 | Art 17 | Quality management system | provider | Missing: No quality management system covering AI. | Due 02 Dec 2027 (15 mo) |
| 19 | S1 | Art 43 | Conformity assessment before putting into service | provider | Missing: No conformity assessment planned. | Due 02 Dec 2027 (15 mo) |
| 20 | S1 | Art 47-48 | EU declaration of conformity and CE marking | provider | Missing: No declaration of conformity. | Due 02 Dec 2027 (15 mo) |
| 21 | S1 | Art 49(1) | Register in the EU database | provider | Missing: Not registered. | Due 02 Dec 2027 (15 mo) |
| 22 | S1 | Art 72-73 | Post-market monitoring and serious incident reporting | provider | Partial: Monthly loss ratio review; no incident procedure. | Due 02 Dec 2027 (15 mo) |
| 23 | S1 | Art 26(1) | Use according to the instructions for use | deployer | Partial: Pricing manual exists; underwriters not trained on it. | Due 02 Dec 2027 (15 mo) |
| 24 | S1 | Art 26(2) | Human oversight by competent, trained, empowered staff | deployer | Partial: Underwriters review refers; no authority to override price. | Due 02 Dec 2027 (15 mo) |
| 25 | S1 | Art 26(4) | Input data relevant and representative, where controlled | deployer | Met: Cierzo designs and validates the questionnaire. | Done |
| 26 | S1 | Art 26(5) | Monitor operation, report risks and serious incidents | deployer | Missing: No route to report a model incident. | Due 02 Dec 2027 (15 mo) |
| 27 | S1 | Art 26(6) | Keep logs at least six months | deployer | Missing: 90-day log retention is below six months. | Due 02 Dec 2027 (15 mo) |
| 28 | S1 | Art 26(11) | Tell people a high-risk system is used in decisions about them | deployer | Missing: Applicants are not told a model prices them. | Due 02 Dec 2027 (15 mo) |
| 29 | S1 | Art 86 | Explain the system's role in a decision on request | deployer | Missing: No process to explain a price or decline. | Due 02 Dec 2027 (15 mo) |
| 30 | S1 | Art 27 | Fundamental rights impact assessment before first use, notified to the market surveillance authority | deployer | Missing: No fundamental rights impact assessment. | Due 02 Dec 2027 (15 mo) |
| 31 | S4 | Art 26(1) | Use according to the instructions for use | deployer | not assessed | Pre-deployment |
| 32 | S4 | Art 26(2) | Human oversight by competent, trained, empowered staff | deployer | not assessed | Pre-deployment |
| 33 | S4 | Art 26(4) | Input data relevant and representative, where controlled | deployer | not assessed | Pre-deployment |
| 34 | S4 | Art 26(5) | Monitor operation, report risks and serious incidents | deployer | not assessed | Pre-deployment |
| 35 | S4 | Art 26(6) | Keep logs at least six months | deployer | not assessed | Pre-deployment |
| 36 | S4 | Art 26(11) | Tell people a high-risk system is used in decisions about them | deployer | not assessed | Pre-deployment |
| 37 | S4 | Art 86 | Explain the system's role in a decision on request | deployer | not assessed | Pre-deployment |
| 38 | S5 | Art 26(1) | Use according to the instructions for use | deployer | Partial: Vendor manual exists; not built into procedure. | Due 02 Dec 2027 (15 mo) |
| 39 | S5 | Art 26(2) | Human oversight by competent, trained, empowered staff | deployer | Met: Underwriters sign off every rating. | Done |
| 40 | S5 | Art 26(4) | Input data relevant and representative, where controlled | deployer | Partial: Disclosures sent as typed; no completeness check. | Due 02 Dec 2027 (15 mo) |
| 41 | S5 | Art 26(5) | Monitor operation, report risks and serious incidents | deployer | Missing: No channel to report vendor incidents. | Due 02 Dec 2027 (15 mo) |
| 42 | S5 | Art 26(6) | Keep logs at least six months | deployer | Partial: Vendor holds logs; Cierzo has no access. | Due 02 Dec 2027 (15 mo) |
| 43 | S5 | Art 26(11) | Tell people a high-risk system is used in decisions about them | deployer | Missing: Applicants not informed. | Due 02 Dec 2027 (15 mo) |
| 44 | S5 | Art 86 | Explain the system's role in a decision on request | deployer | Missing: No explanation process. | Due 02 Dec 2027 (15 mo) |
| 45 | S5 | Art 27 | Fundamental rights impact assessment before first use, notified to the market surveillance authority | deployer | Missing: No fundamental rights impact assessment. | Due 02 Dec 2027 (15 mo) |
<!-- END:gaps -->
