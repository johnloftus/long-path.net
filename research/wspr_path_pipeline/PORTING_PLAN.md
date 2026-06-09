# Long-Path JavaScript Porting Plan

## Purpose

This document records the recommended plan for moving the current Python WSPR long-path research pipeline into a browser-based `index.html` application for long-path.net.

The Python pipeline remains the reference implementation until the JavaScript version reproduces the selected Python outputs on known VK4EMM test data.

The project roles remain:

- SME design: propagation method, terminology, interpretation, validation rules, and public-facing scientific clarity.
- Technical implementation: code structure, calculations, data loading, reports, testing, and Git workflow.

## Current Progress At 2026-06-07

The first browser milestone is substantially implemented in `/home/john/Projects/long-path/index.html`.

Completed or substantially complete:

- local loading of one or more VK4EMM directional-antenna CSV files;
- JavaScript feature-row and Europe bar-truth generation;
- independent regression models for 40m, 30m, and 20m;
- independent read-only Model coefficients and editable Trial coefficients for each band;
- band-specific prediction rows and short-path / long-path R2 review;
- band charts with observed Loop 2, observed Loop 3, and the model-predicted dominant path;
- dominance confidence, endpoint illumination, and path grey-line overlap strips;
- per-band tables and CSV exports;
- printable browser HTML/PDF report support.

Current next milestone:

1. bring `wspr_path_pipeline.py` into exact agreement with the browser app's independent-band model;
2. build repeatable Python-versus-JavaScript comparison tests across all known VK4EMM dates;
3. resolve every unexplained numerical difference before broader operator features are added.

Later operator milestone:

- add Continent / City path selectors using patterns from `grey-line-index.html`;
- add independently selectable endpoint radius controls;
- use the selected cities and endpoint radii for WSPR path-data filtering and reporting.

## Current Canonical Files

Project folder:

```text
/home/john/Projects/long-path/research/wspr_path_pipeline
```

Note: use `long-path`, not `long_path`, when working in the local project folder.

Current reference implementation:

```text
wspr_path_pipeline.py
```

Current browser implementation:

```text
/home/john/Projects/long-path/index.html
```

Current reference CSV outputs:

```text
out_review_clean/wspr_path_features.csv
out_review_clean/europe_bar_truth.csv
out_review_clean/europe_regression_predictions.csv
out_review_clean/europe_regression_report.md
```

Current source data examples:

```text
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-02-08.csv
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-03-08.csv
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-03-18.csv
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-03-29.csv
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-04-15.csv
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-05-27.csv
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-05-05.csv
```

Useful browser and UI references:

```text
prototype_part_UI.html
grey-line-index.html
rpr_bars_2026-05-05_20m_Europe_spot_count_side_by_side.png
rpr_bars_2026-05-05_30m_Europe_spot_count_side_by_side.png
```

Later panels that may reuse selected `grey-line-index.html` patterns:

- Great Circle Path;
- WSPR Band Activity Report for the selected path;
- Daily WSPR Path Matrix.

Later decisions:

- Mercator map showing short path and long path;
- 24-hour UTC timeline with a configurable solar-altitude threshold.

Archived folders are for recovery only. Do not use them as active references.

```text
archive_old_outputs_2026-05-30/
out_review_clean/archive_old_duplicates_2026-05-30/
```

## Current Scientific Language

Use this terminology consistently in the JavaScript app.

- `path_dominance_score`: observed antenna evidence from Loop 2 and Loop 3.
- `observed_antenna_path_dominance_score`: observed validation value from antenna counts.
- `simple_model_path_dominance_score`: derived model-estimated path dominance, calculated from the separate short-path and long-path model count predictions.
- `enhanced_model_path_dominance_score`: model-estimated path dominance using the larger research model.
- `constant`: the baseline term in the regression equation. Scientists may also call this the intercept.
- `coefficient`: the regression weight applied to a variable.
- `R2`: coefficient of determination; a figure of merit for model agreement with observations.
- `bearing_difference`: the difference in degrees between an antenna bearing and a calculated path bearing.
- `path_greyline_overlap`: a visual guide showing when sampled grey-line support overlaps along the reference path.

The observed antenna formula is:

```text
path_dominance_score = (Loop2_count - Loop3_count) / (Loop2_count + Loop3_count)
```

Interpretation:

- positive observed antenna score favours Loop 2 / short path;
- negative observed antenna score favours Loop 3 / long path;
- near zero means neither antenna clearly dominates.

The model formula is different. It uses a constant plus coefficients multiplied by solar/path variables. Separate short-path and long-path formulas estimate support for their own path; the app then derives model path dominance from the two predicted counts.

Plain-language explanation:

The regression model tests how well selected solar and path variables agree with observed short-path and long-path antenna evidence in each 30-minute time slot. If agreement is poor, the model needs more work. A validated model may later help stations without directional antennas estimate likely short-path or long-path activity between known endpoints. Use of the same coefficients on other paths, seasons, and latitudes remains an open research question.

## Important Scientific Separation

The browser app must keep these concepts separate.

The project must also keep these analysis groups separate:

- different UTC dates;
- different amateur bands;
- short-path and long-path evidence;
- different selected endpoint areas.

The browser app currently fits independent coefficient sets for each band and each path. It does not use one combined coefficient set for 40m, 30m, and 20m, and it does not merge short-path and long-path into one coefficient set.

### 1. Observed Antenna Evidence

Directional antenna observations are the validation source.

For the VK4EMM Brisbane/QG62LR Europe reference case:

- Loop 2 at 330 degrees is treated as short-path-to-Europe validation evidence.
- Loop 3 at 150 degrees is treated as long-path-to-Europe validation evidence.

SNR is not used. A decoded WSPR spot is counted as a spot regardless of signal strength.

### 2. Model Estimate

The model uses solar and path variables to estimate short-path support and long-path support separately. The two predictions can then be compared with the observed antenna path dominance score.

The simple model currently uses:

- `dark_delta`: short-path dark fraction minus long-path dark fraction;
- `greyline_delta`: short-path grey-line fraction minus long-path grey-line fraction;
- `endpoint_twilight`: the strongest twilight score at either endpoint;
- `constant`: the baseline value in the regression equation before variable terms are added.

The enhanced model currently adds band and UTC cyclic terms plus endpoint solar altitude terms. It is useful for research comparison, but the first browser app should start with the simple model.

The current simple browser model is fitted independently for each band and each path. Band indicators are therefore not needed to distinguish 40m, 30m, and 20m within that simple model.

### 3. Trial Coefficients

Operators or reviewers may enter trial coefficients manually.

Trial coefficients are not official model coefficients. They are for experiment, explanation, and review.

## Model And Trial Coefficient Panels

The browser app preserves the two-column concept from `prototype_part_UI.html`, independently for each band.

### Model Column

Purpose:

- show coefficients derived from empirical antenna observations;
- make the source of coefficients transparent;
- prevent accidental editing of published model values.

Behaviour:

- populated when the selected city-to-city path has a known model coefficient record;
- blank when no model coefficient record exists;
- read-only;
- the Calibrate Model action updates only the Model column and must not overwrite existing Trial coefficients;
- source metadata such as call sign, receiver grid, antenna pair, and date range is shown once where practical rather than repeated beside every band.

### Trial Column

Purpose:

- allow operators and reviewers to experiment with coefficients;
- support paths where no validated model coefficients exist;
- allow expert review without overwriting model data.

Behaviour:

- editable by the user;
- may be copied from the model column only through the explicit Copy Model To Trial action;
- preserved when the Model is recalibrated;
- clearly labelled as trial data;
- not saved as official model coefficients unless deliberately exported and reviewed later.

## Recommended Browser Data Files

JSON files are preferred for the browser app because they are easy to inspect and can run without a server when bundled into `index.html`.

Recommended files or embedded JavaScript constants:

```text
data/cities.json
data/path_models.json
data/antenna_pairs.json
data/sample_datasets.json
```

### `cities.json`

```json
{
  "id": "brisbane",
  "name": "Brisbane",
  "country": "Australia",
  "continent": "Oceania",
  "maidenhead": "QG62LR",
  "lat": -27.47,
  "lon": 153.03
}
```

### `path_models.json`

```json
{
  "path_id": "brisbane_frankfurt",
  "from_city_id": "brisbane",
  "to_city_id": "frankfurt",
  "source": {
    "call_sign": "VK4EMM",
    "receiver_grid": "QG62LR",
    "antenna_pair": "Loop2 330deg / Loop3 150deg",
    "date_range": "2026-02-08 to 2026-05-27",
    "data_source": "local directional antenna CSV files"
  },
  "simple_model": {
    "40m": {
      "short_path": {"constant": 0.0, "dark_delta": 0.0, "greyline_delta": 0.0, "endpoint_twilight": 0.0},
      "long_path": {"constant": 0.0, "dark_delta": 0.0, "greyline_delta": 0.0, "endpoint_twilight": 0.0}
    },
    "30m": {
      "short_path": {"constant": 0.0, "dark_delta": 0.0, "greyline_delta": 0.0, "endpoint_twilight": 0.0},
      "long_path": {"constant": 0.0, "dark_delta": 0.0, "greyline_delta": 0.0, "endpoint_twilight": 0.0}
    },
    "20m": {
      "short_path": {"constant": 0.0, "dark_delta": 0.0, "greyline_delta": 0.0, "endpoint_twilight": 0.0},
      "long_path": {"constant": 0.0, "dark_delta": 0.0, "greyline_delta": 0.0, "endpoint_twilight": 0.0}
    }
  }
}
```

The exact band-specific coefficient values should be exported after Python and JavaScript agree and the current model is accepted.

### Selected Path And Endpoint Radius

The later operator workflow should hold endpoint selection separately from validated model coefficients.

Example:

```json
{
  "from_city_id": "brisbane",
  "from_radius_km": 1200,
  "to_city_id": "frankfurt",
  "to_radius_km": 1200
}
```

The two radii are independent user choices. They define endpoint areas for path-data filtering and do not redefine the fixed antenna evidence used to validate a model.

## Input Data Modes

The JavaScript app should support two different data modes.

### Mode A: Directional Antenna CSV

Used for empirical validation and coefficient development.

Characteristics:

- local CSV input;
- includes antenna/source fields;
- supports Loop 2 versus Loop 3 validation;
- can reproduce `europe_bar_truth.csv` and `europe_regression_predictions.csv`.

### Mode B: WSPR Path Data

Used later for operator/reviewer path analysis where no directional antenna validation exists.

Characteristics:

- local CSV or wspr.live-style rows;
- no Loop 2 / Loop 3 validation fields;
- useful for activity, endpoint, path, and solar calculations;
- confidence must be described carefully because directional validation is absent.

## Build Order

### Stage 1: Static App Shell

Status: substantially complete for the directional-antenna research workflow.

Create or update `index.html` with:

- header and project identity;
- path selectors;
- UTC date selector;
- endpoint and antenna metadata panel;
- Model and Trial coefficient panels;
- visual report area;
- CSV load area;
- export buttons.

Reuse selected UI patterns from `grey-line-index.html`, especially:

- city selectors;
- date/time controls;
- print/PDF handling;
- table layout;
- CSV export/download helpers;
- localStorage patterns where useful.

Path selectors and endpoint controls remain for the later operator workflow.

### Stage 2: CSV Loader

Status: complete for current VK4EMM directional-antenna CSV files.

Add browser CSV loading for VK4EMM antenna files.

The first accepted input should be the current files beginning with:

```text
vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_*.csv
```

The loader should support multiple selected files in one operation.

### Stage 3: Pure Calculation Port

Status: ported; formal Python-versus-JavaScript parity tests remain.

Port and test these Python functions before building final visuals:

- `maidenhead_to_latlon`;
- `haversine_km`;
- `initial_bearing_deg`;
- `bearing_difference_deg`;
- `interpolate_gc`;
- `interpolate_long_gc`;
- `solar_altitude_deg`;
- `path_solar_features`;
- `path_darkness_theory_features`;
- `slot_from_dt`.

The JavaScript result must match the Python reference closely enough for practical reporting.

### Stage 4: Feature Rows

Status: implemented in the browser; formal parity testing remains.

Port the logic needed to reproduce:

```text
wspr_path_features.csv
```

Required comparison fields:

- `date_utc`;
- `utc_slot`;
- `slot_index`;
- `band_m`;
- `continent`;
- `country_code`;
- `tx_grid`;
- `loop2_count`;
- `loop3_count`;
- `observation_count`;
- `path_dominance_score`;
- `rx_sun_altitude`;
- `tx_sun_altitude`;
- `short_path_dark_fraction`;
- `long_path_dark_fraction`;
- `short_path_greyline_fraction`;
- `long_path_greyline_fraction`.

### Stage 5: Europe Bar Truth

Status: implemented in the browser; formal parity testing remains.

Port the logic needed to reproduce:

```text
europe_bar_truth.csv
```

This is the first major app truth table.

Required fields:

- `date_utc`;
- `utc_slot`;
- `slot_index`;
- `band_m`;
- `loop2_count`;
- `loop3_count`;
- `observation_count`;
- `path_dominance_score`;
- `rx_sun_altitude`;
- `tx_sun_altitude`;
- `short_path_dark_fraction`;
- `long_path_dark_fraction`;
- `dark_delta`;
- `short_path_greyline_fraction`;
- `long_path_greyline_fraction`;
- `greyline_delta`;
- `endpoint_twilight_score`.

### Stage 6: Simple Regression

Status: implemented independently for 40m, 30m, and 20m, with separate short-path and long-path coefficient sets. Python and JavaScript parity testing passes across the known VK4EMM dates.

Port the simple regression first:

```text
path_support_score =
  constant
  + coefficient_dark_delta * dark_delta
  + coefficient_greyline_delta * greyline_delta
  + coefficient_endpoint_twilight * endpoint_twilight_score
```

Each band and each path must have its own coefficient set. The app should report:

- Model and Trial coefficients for that band/path pair;
- short-path R2 for that band;
- long-path R2 for that band;
- predicted Loop 2 and Loop 3 counts;
- derived predicted path-dominance score and residual against observed antenna path dominance score.

Weighted R2 is weighted by spot count, not SNR.

Do not report one overall R2 or one combined coefficient set made by amalgamating bands or paths.

### Stage 7: Visual Story

Status: substantially complete in `index.html`; reviewer wording and worked-example integration remain.

Build the browser equivalent of:

```text
out_review_clean/reviewer_package/visual_report.html
```

The first browser visual should include:

- 40m at top;
- 30m second;
- 20m last;
- 30-minute UTC slots;
- observed Loop 2 and Loop 3 bars;
- one simple model bar showing only the model-predicted dominant path;
- confidence strip;
- receiver endpoint light/dark strip;
- beacon endpoint light/dark strip;
- path grey-line overlap strip;
- shared colour legend and sandwich guide;
- worked example in plain language.

Each band presentation should place its short-path and long-path Model/Trial coefficient panels directly above its chart so a reviewer can edit Trial coefficients and immediately inspect the response.

The chart shows both observed antenna counts. It shows only the model prediction for the dominant path. Predictions for both paths remain available in the Regression Predictions table.

The earlier PNG charts are useful visual references, but the browser version should be generated from the current data.

### Stage 8: Reviewer Documentation In App

Status: partially complete. The external reviewer documents are well developed; fuller integration into `index.html` remains.

Add an About / How to Read panel based on:

```text
out_review_clean/reviewer_package/project_overview.md
out_review_clean/reviewer_package/project_about.md
```

Keep chapters 1 and 2 in everyday language. Keep deeper scientific detail separate.

### Stage 9: Export

Status: substantially complete for CSV, browser HTML, print, and PDF. Trial-coefficient JSON export and final report polish remain.

Add exports after the calculations are trusted:

- CSV for feature rows;
- CSV for Europe bar truth;
- CSV for regression predictions;
- printable HTML/PDF visual report;
- optional JSON export for trial coefficients.

Exports must remain separated by band. Filenames and report headings must clearly identify the band, selected date or dates, path, and later the endpoint radii.

### Stage 10: Continent / City Path Selection And Endpoint Radius

Status: foundation implementation begun after Python/JavaScript numerical parity was established. `index.html` now has shared Continent / City selectors, independent endpoint radii, UTC date, path metadata, browser persistence, and exact validated-model status.

Reuse appropriate patterns from `grey-line-index.html` for:

- Continent and City selection at both endpoints;
- city names, Maidenhead grids, latitude, and longitude;
- favourite or saved paths where useful;
- independently selectable radius for each endpoint.


Selected Path foundation responsibilities:

- describe the endpoint context for imported paired directional-antenna data;
- provide the shared path, UTC date, and independent endpoint radii for later WSPR activity panels;
- declare whether an exact directional-antenna validation model exists for the selected path;
- never silently apply a validated model from one city pair to a different city pair;
- allow WSPR activity to be reported for unvalidated paths without claiming short-path or long-path validation.

Endpoint-radius behaviour:

- each endpoint may use a different radius;
- the selected radius defines the station/grid area associated with that endpoint;
- the practical first method is to include station locations or Maidenhead grid centres within the selected radius;
- treatment of grid cells overlapping the radius boundary must be documented and tested;
- selected endpoint radii must appear in reports and exports;
- radius filtering belongs mainly to Mode B WSPR path data and must not silently alter fixed VK4EMM directional-antenna validation evidence.

### Stage 11: Mode B Operator Path Data

Status: future work.

After path selectors and endpoint radii are stable:

- load local or wspr.live-style path data;
- filter spots between the selected endpoint areas;
- calculate path and solar variables without claiming directional-antenna validation;
- apply only model coefficients appropriate to the selected band and path record;
- clearly distinguish model indication from empirically validated antenna evidence.

## Testing Principle

The first JavaScript milestone is numerical trust, not visual polish.

For each known VK4EMM test file, JavaScript should match Python for selected reference rows and band-specific model outputs.

Recommended comparison command for Python reference:

```bash
cd /home/john/Projects/long-path/research/wspr_path_pipeline
uv run python wspr_path_pipeline.py vk4emm_raw_spots_data_Loop2_Loop3_20m_30m_40m_2026-*.csv --out-dir out_review_clean
```

Then compare the JavaScript outputs against:

```text
out_review_clean/wspr_path_features.csv
out_review_clean/europe_bar_truth.csv
out_review_clean/europe_regression_predictions.csv
```

Differences should be explained before changing either implementation.

Required parity checks:

- feature rows by date, band, UTC slot, and transmitter grid;
- Europe bar-truth rows by date, band, and UTC slot;
- independent 40m, 30m, and 20m coefficients, separated again into short-path and long-path coefficient sets;
- predicted Loop 2 and Loop 3 counts;
- predicted path-dominance score and residual;
- short-path R2 and long-path R2 for each band;
- visual chart values and hover values for selected reference slots.

## Suggested First JavaScript Milestone

Status: substantially complete. The remaining acceptance requirement is formal Python-versus-JavaScript parity testing.

The first useful `index.html` milestone should:

1. Load multiple VK4EMM CSV files from the user's computer.
2. Build `europe_bar_truth` rows in the browser.
3. Fit independent simple regressions for each band and each path.
4. Show short-path and long-path R2 independently for each band.
5. Show a compact 40m / 30m / 20m visual story.
6. Export the generated CSVs.

This milestone will be accepted when the browser reproduces the agreed Python band-by-band research result before broader operator features are added.

## Immediate Next Work

Completed in this milestone:

- `wspr_path_pipeline.py` now fits and reports independent simple models for 40m, 30m, and 20m, separated again into short-path and long-path models.
- Short-path and long-path R2 remain separate within every band.
- `compare_python_js_band_models.mjs` provides repeatable Python-versus-JavaScript comparison across all known VK4EMM dates.
- Python reports and JavaScript calculations agree within report precision for feature rows, bar-truth rows, simple model predictions, and per-band/per-path coefficients.

Remaining immediate work:

1. Continue the Selected Path foundation into the WSPR Band Activity Report and Daily WSPR Path Matrix while keeping directional validation evidence separate.
2. Adapt the Great Circle Path and later grey-line planning panels from `grey-line/index.html` after the shared path contract is stable.
3. Add export/import of calibrated Model and Trial coefficients after the main operator workflow is stable.
4. Complete reviewer documentation and final export polish after development settles.
5. Leave the Mercator map undecided until the path workflow and model presentation are settled.

## Git Workflow

Because this is a research project with many experimental files, use Git conservatively.

Recommended pattern:

```bash
cd /home/john/Projects/long-path
git status
git add research/wspr_path_pipeline/PORTING_PLAN.md
git commit -m "Update JavaScript porting plan"
git push origin main
```

Before each commit, inspect `git status` and only add the intended files.
---------------------------------------------------------------------
