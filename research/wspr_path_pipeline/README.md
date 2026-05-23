# WSPR Path Research Pipeline

Offline research pipeline for developing and reviewing short-path / long-path WSPR propagation evidence.

The pipeline separates:

- Theory: solar illumination, path darkness, twilight/grey-line state, band rules, and endpoint geometry.
- Validation: Daily WSPR Path Matrix activity, directional antenna evidence, and reviewer/operator experience.
- Review: SME critique of the theory, regional assumptions, endpoint clusters, and confidence wording.

Validation is not part of the theory. It is used to test whether the theory is realistic.

## Current Theory Model

The current reviewer ledger uses `theory_v3_path_darkness`.

For 30m and 40m, the theory compares the short-path and long-path great-circle routes:

```text
path_score =
  0.70 * dark_fraction
  + 0.20 * twilight_fraction
  + 0.10 * endpoint_twilight_score
```

The path with the larger score is favoured.

Grey-line/twilight improves the score, but does not override the main darkness comparison. For 20m, the same scores are shown as context only; 20m rows are marked as possible or mixed-path because more than one path may be active.

## Model Fitting and Validation

The script uses regression (data-driven optimization) as the primary method for determining the coefficients (weights) for the path score variables. The function model_matrix() builds a matrix of features (variables) and the observed direction scores. The function fit_wls() (weighted least squares) is used to fit the model, finding the optimal coefficients (betas) for each variable to best match the observed data.

This is a form of regression, and the script also includes an r2_score() function to compute the coefficient of determination (figure of merit). Ideally, we are looking for an r2_score() figure of merit of at least 0.7. The figure will improve as we get feedback from reviewers.

Reviewers can adjust the calculated coefficients to better reflect their own environment or region. This flexibility allows for practical adaptation and helps inform future model refinements, especially for different latitudes or seasonal conditions. Feedback from reviewer adjustments is encouraged and will be used to improve the regression model.

The script also supports fixed theoretical weights (e.g., 0.70, 0.20, 0.10) for transparency and historical comparison, but these are not the recommended standard for all regions.

Note: Consistency over time (e.g., through seasons) is a possible future variable for confidence, pending sufficient data.

## VK7JJ Reviewer Sample

The VK7JJ reviewer sample uses wspr.live rows where:

- receiver callsign is `VK7JJ`
- date is `2026-05-18` UTC
- bands are 40m, 30m, and 20m
- transmitter locations are within 1200 km of Frankfurt or London

This matches the Hobart < Europe validation scope used in the Daily Path Matrix spreadsheet.

## Run

From the repository root:

```bash
uv run --project research/wspr_path_pipeline python research/wspr_path_pipeline/wspr_path_pipeline.py /home/john/WSPR_path_matrix/wspr_path_research/raw_data_QG62LR_L2_330deg_L3_150deg_20m_30m_40m_*.csv
```

Or from this directory:

```bash
cd /home/john/Projects/grey-line/research/wspr_path_pipeline
uv run python wspr_path_pipeline.py /home/john/WSPR_path_matrix/wspr_path_research/raw_data_QG62LR_L2_330deg_L3_150deg_20m_30m_40m_*.csv
```

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

- `THEORY_REWORK_DRAFT.md`
- `SME_PANEL_INVITATION_DRAFT.md`
- `BASELINE_AUDIT.md`

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

## Notes

The old baseline regression work is retained only in `BASELINE_AUDIT.md`. Current reviewer reports should use the V3 path-darkness theory.

The next likely development step is a slim standalone JavaScript app for reviewer use, separate from the current grey-line app but able to share endpoint, solar, and WSPR query logic.
