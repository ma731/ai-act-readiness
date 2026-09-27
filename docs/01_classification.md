# 1. Inventory and classification

Cierzo Seguros is a **fictional** mid-size Spanish life and health insurer. It runs or plans
six AI systems. Each one is described by facts in
[`inventory/cierzo_systems.yaml`](../inventory/cierzo_systems.yaml), and the tier below is
what [`src/rules.py`](../src/rules.py) concludes from those facts, citing the article each
step rests on. Law as of 27 September 2026, including the Digital Omnibus on AI.

<!-- BEGIN:inventory -->
| ID | System | Role | Classification | Why | FRIA |
|---|---|---|---|---|---|
| S1 | Tarifa Salud | provider, deployer | **High-risk** | Risk assessment or pricing of natural persons in health insurance: Annex III 5(c). Derogation claimed (Art 6(3)(d) preparatory task) but the system profiles natural persons, so Art 6(3) keeps it high-risk. | Required |
| S2 | Asistente Cierzo | provider, deployer | **Transparency** | Interacts directly with people: Art 50(1) disclosure at first contact (Art 50(5)). | No |
| S3 | Detector Fraude Siniestros | provider, deployer | **Minimal** | Claims fraud detection is not listed in Annex III. The fraud carve-out in 5(b) concerns credit scoring and is not needed here. | No |
| S4 | Voz Calidad (proposed) | deployer | **Prohibited** | Infers emotions of workers from biometric data: prohibited by Art 5(1)(f) since 2 Feb 2025. Emotion recognition on customers is listed high-risk in Annex III 1(c). | No |
| S5 | Suscripcion Vida | deployer | **High-risk** | Risk assessment or pricing of natural persons in life insurance: Annex III 5(c). Profiles natural persons: Art 6(3) derogation unavailable. | Required |
| S6 | Tarifa Hogar | provider, deployer | **Minimal** | Pricing in home insurance is not listed: Annex III 5(c) covers life and health only. | No |
<!-- END:inventory -->

## The calls a quick reading gets wrong

**Tarifa Salud is high-risk even though the business says it only "prepares" a decision.**
Article 6(3)(d) lets an Annex III system out of the high-risk tier if it only performs a
preparatory task. The same paragraph closes that door for any system that profiles people,
and pricing an applicant from their health answers is profiling. The owner's claim is
recorded in the inventory so the rejection is visible, not silent.

**Home pricing is not high-risk. Health pricing is.** Annex III 5(c) names life and health
insurance only. Tarifa Hogar prices people too, but the AI Act does not list it. The unisex
rule from Test-Achats still applies to it, which is why the other-law notes list it.

**Claims fraud scoring is not high-risk, and the reason is not the fraud carve-out.** Annex
III 5(b) exempts fraud detection from the *credit scoring* entry. Insurance fraud scoring is
simply not listed anywhere. The distinction matters: if Cierzo ever let the score deny a
claim on its own, GDPR Article 22 would bite even though the AI Act does not.

**The voice tool is two systems in one box.** Inferring the emotions of contact-centre
agents from their voice is a prohibited practice (Article 5(1)(f), in force since
2 February 2025). Doing the same to customers is not prohibited but is high-risk
(Annex III 1(c)) and needs disclosure (Article 50(3)). Switching the tool to text sentiment
on transcripts would take it out of both, because Article 3(39) defines emotion recognition
on biometric data.

**The chatbot is Cierzo's even though the model is not.** Building a customer assistant on
a third-party model through an API makes Cierzo the provider of the assistant, so the
Article 50(1) duty to say "you are talking to an AI" is Cierzo's. It has applied since
2 August 2026 and is the one obligation overdue today.

**The chatbot also feeds the high-risk system.** Asistente Cierzo collects the health
questionnaire for new quotes and hands it to Tarifa Salud. That conversational path is an
input channel of a high-risk system and belongs in its data governance and logs.

## Flags for the reviewer

<!-- BEGIN:flags -->
- **S1 Tarifa Salud:** Already in service: under Art 111(2) the high-risk duties bite only once its design changes significantly. Confirm the post-Omnibus cut-off in Regulation (EU) 2026/1744 before relying on this; a scheduled re-rating that changes factors or model form is likely such a change.
- **S1 Tarifa Salud** (outside the AI Act): GDPR Art 9: health data is special category; needs an Art 9(2) basis. Art 35 DPIA (the FRIA may reuse it, AI Act Art 27(4)).
- **S1 Tarifa Salud** (outside the AI Act): GDPR Art 22: solely automated decisions with significant effect need a lawful basis, human intervention and contest rights.
- **S1 Tarifa Salud** (outside the AI Act): Directive 2004/113 Art 5 (Test-Achats, C-236/09): sex must not change premiums or benefits; pregnancy and maternity costs must not either.
- **S2 Asistente Cierzo:** A system built on a third-party model is still the provider of that system; check whether the model vendor's marking reaches your output.
- **S2 Asistente Cierzo:** Its output becomes input to S1: that path must be in the receiving system's data governance, logs and instructions for use.
- **S2 Asistente Cierzo** (outside the AI Act): GDPR Art 9: health data is special category; needs an Art 9(2) basis. Art 35 DPIA (the FRIA may reuse it, AI Act Art 27(4)).
- **S3 Detector Fraude Siniestros** (outside the AI Act): GDPR Art 9: health data is special category; needs an Art 9(2) basis. Art 35 DPIA (the FRIA may reuse it, AI Act Art 27(4)).
- **S4 Voz Calidad:** Biometric system: Art 43(1) conformity route depends on harmonised standards; a notified body may be required.
- **S5 Suscripcion Vida:** Already in service: under Art 111(2) the high-risk duties bite only once its design changes significantly. Confirm the post-Omnibus cut-off in Regulation (EU) 2026/1744 before relying on this.
- **S5 Suscripcion Vida** (outside the AI Act): GDPR Art 9: health data is special category; needs an Art 9(2) basis. Art 35 DPIA (the FRIA may reuse it, AI Act Art 27(4)).
- **S5 Suscripcion Vida** (outside the AI Act): Directive 2004/113 Art 5 (Test-Achats, C-236/09): sex must not change premiums or benefits; pregnancy and maternity costs must not either.
- **S6 Tarifa Hogar** (outside the AI Act): Directive 2004/113 Art 5 (Test-Achats, C-236/09): sex must not change premiums or benefits; pregnancy and maternity costs must not either.
<!-- END:flags -->

## Limits

This is a rules engine for the parts of the Act an insurer's inventory touches, not a full
encoding of the regulation. It does not cover general-purpose AI model obligations, Annex I
products, or public-sector deployers. Its conclusions are a starting position for legal
review, and the tests in [`tests/test_rules.py`](../tests/test_rules.py) pin each call
above so a change to the rules shows up as a failing test.
