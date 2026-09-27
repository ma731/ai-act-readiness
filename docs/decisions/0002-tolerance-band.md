# ADR 0002: The 0.80 to 1.25 price-to-cost tolerance

## Decision

A group is **overcharged** when the whole 95% interval of its price-to-cost is above 1.25,
**undercharged** when it is below 0.80, **within tolerance** when it sits inside, and
**inconclusive** when it straddles a line.

## Why these numbers

0.80 and 1.25 are reciprocals, so paying 25% over your share and 20% under it count as the
same distance from fair. It borrows the shape of the four-fifths rule without claiming its
legal standing. Every pricing model cross-subsidises to some degree; the band says how much
the pricing committee accepts before it must act.

## Why intervals, not single numbers

Health costs have a long tail: a few very expensive people move a group's average a lot. A
verdict on the single estimate would flip between samples. So verdicts use the 95% interval
from 400 bootstrap resamples, drawn within region because the survey is stratified by region.

## Stated plainly: the band was chosen after a first look at results

The band was set during the first version of this project, on US data, after seeing the first
numbers. It was not changed when the analysis moved to Spanish data. A real engagement would
agree it with the pricing committee before any results exist.
