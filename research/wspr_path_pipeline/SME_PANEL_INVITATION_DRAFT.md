# Invitation To Join A WSPR Propagation Review Panel

## Purpose

We are developing an evidence-based method for identifying likely short-path and long-path HF propagation using WSPR activity, solar illumination, grey-line geometry, and transparent propagation rules.

The goal is to produce a practical propagation reporting tool that can be used by radio operators, emergency communications groups, scientific users, and other organisations without requiring specialist antenna systems.

## Why This Work Is Needed

WSPR reports provide a large and useful record of HF propagation activity. However, current public WSPR spot data generally reports path distance as short-path distance and does not attempt to identify likely long-path propagation.

This leaves an important gap. Operators often care not only that a signal was heard, but which path was likely active, when that path tends to open, and how much confidence should be placed in that conclusion.

Our project is building a transparent evidence model that separates:

- Theory: solar illumination, grey-line state, band behaviour, regional activity, and repeatability.
- Validation: independent checks using directional antennas or other suitable methods.
- Review: scrutiny by experienced operators and propagation specialists.

## Why We Are Seeking Subject Matter Expert Panel Members

Propagation behaviour differs by continent, season, path length, band, time of day, solar conditions, and regional geography. A rule set developed for one region should not be assumed to apply globally without review.

We are seeking subject matter experts to help formulate and review continent-specific propagation rules. The panel’s role is not to endorse a black-box model. The role is to help ensure that the rules are technically reasonable, transparent, and useful to real operators.

## What We Would Ask Panel Members To Review

Panel members may contribute in different ways:

- Formulate and review propagation rules for your continent or region and band.
- One-time critical review of a draft report.
- Ongoing review as the model develops.
- Validation data from a known directional antenna system.
- Practical operator feedback on whether report wording and outputs are useful.
- Recommend clusters of Maidenhead grids, or radius, to cover continents or regions:  https://www.egloff.eu/qralocator/
- Refine methods to translate theory variables and propagation rules into final path indications.

## Current Development Stage

The first research pass is focused on Europe to the Australian east coast, using QG62LR near Brisbane as the receiving location.

Validation data currently comes from two fixed directional loop antennas:

- Loop 2 at 330 degrees, used as validation evidence for short-path-to-Europe activity.
- Loop 3 at 150 degrees, used as validation evidence for long-path-to-Europe activity.

These antennas are not part of the theory. They are one validation instrument. The theory must be useful to operators who do not have directional antennas.

## Intended Outcome

The intended outcome is a report that can say, in plain language:

- Which path is likely active.
- What evidence supports that conclusion.
- What confidence rating is justified.
- Whether independent validation agrees with the theory.
- What limitations or cautions apply.

The method should remain transparent. A reviewer should be able to see why a confidence rating was assigned.

## Reviewers Will Receive

A summary bar chart of likely path indications by time and confidence level - for reviewer's WSPR record for one day.
A copy of a sample Evidence Ledger Report, containing variables supporting a likely path indication.

Variables in the ledger report (draft):

1. Date
2. Time
3. Region Grid
4. Activity
5. Theory
   a. Sun/path
   b. Grey-line
   c. Repeatability
   d. Final indication - Long-Path or Short-Path
   e. Confidence rating
   f. Flags
   
6. Validation

   a. Directional Antennas
   b. Propagation rules
   c. Daily path matrix

## Model Fitting

How the Model Indicates Short-Path or Long-Path

When directional antenna data is available, the model uses the difference in spot counts between antennas (a = short-path, b = long-path):

If (a - b) is positive, the indication is short-path.
If (a - b) is negative, the indication is long-path.

When antenna data is not available (the common case for most reviewers), the model calculates a path score for both the short-path and long-path using fitted coefficients and the relevant variables: (dark_fraction, twilight_fraction, endpoint_twilight_score) for each path.

The model computes the score for both the short-path and the long-path for each time-slot.
The path with the higher score is indicated as the likely propagation path.
This approach allows the model to provide a short-path or long-path indication based solely on propagation theory and observed data, even without directional antennas. The regression ensures that the coefficients are optimised to best match the observed outcomes in cases where validation data is available.

The model uses separate coefficients for each band (40m 30m 20m).

The script uses regression (data-driven optimisation) as the primary method for determining the coefficients (weights) for the path score variables. A function model_matrix() builds a matrix of features (variables) and the observed direction scores. The function fit_wls() (weighted least squares) is used to fit the model, finding the optimal coefficients (betas) for each variable to best match the observed data.

This is a form of regression, and the script also includes an r2_score() function to compute the coefficient of determination (figure of merit). Ideally, we are looking for an r2_score() figure of merit of at least 0.7. The figure will improve as we get feedback from reviewers.

Reviewers have flexibility to adjust and override the calculated coefficients to better reflect their own environment or region. This flexibility allows for practical adaptation and helps inform future model refinements, especially for different latitudes and seasonal conditions. Feedback from reviewer adjustments is encouraged and will be used to improve the regression model.

Note: Consistency over time (e.g., through seasons) is a possible future variable for confidence, pending sufficient data.

## Draft Review Questions

1. Are any assumptions misleading or too broad?
2. Are the endpoint grid-square clusters appropriate and understandable?
3. Does the Evidence Ledger separate theory from validation clearly enough?
4. Are the confidence ratings conservative and defensible?
5. What additional evidence would increase confidence?
6. What warnings or caveats should be visible to users?

## Invitation

If you have experience with HF propagation, WSPR, long-path operation, directional antennas, grey-line operation, or regional band behaviour, we would value your critical review.

The project is still in development. Early review will help shape a tool that is useful to operators and credible to technical reviewers before any public release.

