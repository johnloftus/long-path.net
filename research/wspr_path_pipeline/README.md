# WSPR Path Research Pipeline

Offline research pipeline for developing and reviewing short-path / long-path WSPR propagation evidence.

The pipeline separates:

- Theory: solar illumination, path darkness, twilight/grey-line state, band rules, and endpoint geometry.
- Validation: Daily WSPR Path Matrix activity, directional antenna evidence, and reviewer/operator experience.
- Review: SME critique of the theory, regional assumptions, endpoint clusters, and confidence wording.

Validation is not part of the theory. It is used to test whether the theory is realistic.


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


## VK7JJ Reviewer Sample

The VK7JJ reviewer sample uses wspr.live rows where:

- receiver callsign is `VK7JJ`
- date is `2026-05-18` UTC
- bands are 40m, 30m, and 20m
- transmitter locations are within 1200 km of Frankfurt or London
- receiver locations are within 1200 km of Hobart

This matches the Hobart < Europe validation scope used in a Daily Path Matrix.

## Main Outputs

VK4EMM Europe validation sample:

- `out/vk4emm_europe_evidence_ledger_2026-05-05.csv`
- `out/vk4emm_europe_evidence_report_2026-05-05.html`
- `out/vk4emm_europe_evidence_summary_2026-05-05.html`

VK7JJ reviewer sample:

- `out/vk7jj_reviewer_ledger_2026-05-18.csv`
- `out/vk7jj_reviewer_ledger_2026-05-18.html`
- `out/vk7jj_reviewer_summary_2026-05-18.html`

Theory and review documents:

- `SME_PANEL_INVITATION_DRAFT.md`

## Reviewer Ledger Columns

The reviewer ledger includes:

- date and UTC 30-minute slot
- band
- endpoint region
- activity count
- short-path darkness and twilight fractions
- long-path darkness and twilight fractions
- short-path theory score
- long-path theory score
- score margin
- theory indication
- confidence
- flags
- propagation rule
- validation status


