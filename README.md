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


