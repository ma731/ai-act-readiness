# ADR 0004: A Poisson GLM, not Tweedie

## Decision

Price with a Poisson GLM (log link, survey-weighted), not the Tweedie GLM (power 1.6) the first
version used.

## Why

A Poisson GLM with a log link has the **balance property**: for every level of every factor it
uses, the average price equals the average cost in the data it was fitted on. For a fairness
review that matters. If a group is still over- or undercharged, the gap must come from
something the model does not see, which is exactly the question the FRIA asks.

Tweedie 1.6 is common for pure premiums and ranked people slightly better (Gini 0.614 against
0.597), but it does not have that property, and the difference was not small. Given sex as a
factor, it quoted women 1.43x what men pay, when women's care cost 1.12x as much. A model that
gets a group's average this wrong even when it can see the group cannot be used to judge
whether groups are priced fairly.

The Poisson GLM given sex quotes women 1.115x in sample, matching their cost. On the book as a
whole its price is within 1% of cost, and a gradient-boosted challenger ranks no better, so the
simple, explainable model loses nothing.

## How this was found

By checking whether the numbers made sense before writing them up. The Tweedie result looked
like a finding about women and turned out to be a property of the loss function.
