# ADR 0003: Plan high-risk compliance for systems already in service

**Context.** Tarifa Salud (2024) and Suscripcion Vida (2025) were in service before the
high-risk rules apply. Article 111(2) applies those rules to such systems only if their
design changes significantly afterwards. Sources disagree on the post-Omnibus cut-off date,
and it needs confirming against Regulation (EU) 2026/1744.

**Decision.** Plan as if the high-risk duties apply to both on 2 December 2027.

**Why.**
- Tarifa Salud is re-rated every January. Adding a factor, dropping one or changing the
  model form is the likeliest meaning of a significant design change, and the FRIA itself
  recommends such changes.
- Suscripcion Vida belongs to a vendor who will ship new versions; Cierzo does not control
  when its design changes.
- Relying on the exemption means freezing the models to keep it, which is the opposite of
  fixing what the FRIA found.
- Articles 4, 5 and 50 get no legacy relief.

**What would change this.** Legal confirmation that the cut-off falls after a planned
re-rating, and a board decision to freeze Tarifa Salud's design until then. Neither is
recommended.
