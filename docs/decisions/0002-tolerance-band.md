# ADR 0002: The 0.80 to 1.25 price-to-cost tolerance

**Decision.** A group is overcharged when the whole 95% interval of its relative
price-to-cost is above 1.25, undercharged when it is below 0.80, within tolerance when it
sits inside, and inconclusive otherwise.

**Why these numbers.** 0.80 and 1.25 are reciprocals, so paying 25% over your share and 20%
under it are treated as the same distance from fair. It borrows the shape of the four-fifths
rule without claiming its legal standing. Any pricing model cross-subsidises to some degree;
the band says how much the pricing committee accepts before it must act.

**Why intervals, not point estimates.** Health costs have a long tail: a few very expensive
people move a group's average a lot. A verdict on the point estimate would flip between
runs. Intervals come from a survey-design bootstrap (primary sampling units resampled
within strata, 400 replicates), because MEPS is a clustered sample and treating people as
independent would make the intervals too narrow.

**Stated plainly: the band was chosen after seeing the first results.** A first pass showed
large gaps on a small hold-out with wide intervals. The band was then fixed and the analysis
moved to cross-fitting to use the whole cohort. The band did not move after that. A real
engagement would set it with the pricing committee before any results exist.

**What it does not cover.** Sex. The unisex rule makes men pay above their share by design,
so the verdict column for sex describes the legally required cross-subsidy, not a breach.
