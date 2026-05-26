# Long-Path JavaScript Porting Plan

## Purpose

This document records the recommended build plan for moving the current Python WSPR long-path research pipeline into a browser-based `index.html` application for long-path.net.

The project has two complementary roles:

- SME design: propagation method, terminology, interpretation, validation rules, and public-facing scientific clarity.
- Technical implementation: code structure, calculations, data loading, report generation, testing, and Git workflow.

The Python pipeline remains the reference implementation until the JavaScript version produces matching results on known test data.

## Current Project State

The current reference implementation is:

- `wspr_path_pipeline.py`

The current browser prototype is:

- `index.html`

The Python pipeline currently includes:

- Maidenhead grid conversion.
- Distance and bearing calculations.
- Solar altitude calculations.
- Short-path and long-path darkness/twilight feature calculations.
- Evidence ledgers for directional validation data.
- Reviewer ledgers for wspr.live-style data.
- Theory v3 scoring and confidence classification.
- Markdown, CSV, HTML, and chart/report outputs.

The current `index.html` is a prototype for displaying model coefficients and trial coefficients. It is not yet a full JavaScript port of the Python pipeline.

## Important Scientific Separation

The application must keep these concepts separate:

1. Theory model

   The theory model uses solar/path features such as:

   - dark fraction;
   - twilight fraction;
   - endpoint twilight score.

2. Empirical validation

   Empirical validation uses directional antenna observations, where available.

   For example, for the Brisbane/QG62LR reference case:

   - Loop 2 at 330 degrees is treated as short-path-to-Europe validation evidence.
   - Loop 3 at 150 degrees is treated as long-path-to-Europe validation evidence.

3. Operator trial coefficients

   Operators without directional antenna pairs may enter trial coefficients manually. These should be clearly labelled as trial values, not validated model coefficients.

## Model And Trial Coefficient Panels

The browser app should preserve the two-column concept in the prototype.

### Model Column

The left column is the Model column.

Purpose:

- show coefficients derived from empirical antenna observations;
- make the source of coefficients transparent;
- prevent accidental editing of published model values.

Behaviour:

- populated when the selected city-to-city path has a known model coefficient record;
- blank when no model coefficient record exists;
- read-only in the browser interface;
- includes source metadata such as call sign, grid, antenna pair, date range, and data source.

### Trial Column

The right column is the Trial column.

Purpose:

- allow operators and reviewers to experiment with coefficients;
- support paths where no validated model coefficients exist;
- allow expert review without overwriting model data.

Behaviour:

- editable by the user;
- optionally pre-filled from the model column when model data exists;
- clearly labelled as trial data;
- never saved as official model coefficients unless deliberately exported or reviewed later.

## Data Files

JSON files are a good fit for browser use.

Recommended JSON data files:

- `data/cities.json`
- `data/path_models.json`
- `data/antenna_pairs.json`
- `data/sample_datasets.json`

### `cities.json`

Suggested fields:

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

Suggested fields:

```json
{
  "path_id": "brisbane_frankfurt",
  "from_city_id": "brisbane",
  "to_city_id": "frankfurt",
  "bands_m": {
    "40": {
      "dark_fraction": 0.72,
      "twilight_fraction": 0.18,
      "endpoint_twilight": 0.10
    },
    "30": {
      "dark_fraction": 0.65,
      "twilight_fraction": 0.25,
      "endpoint_twilight": 0.10
    },
    "20": {
      "dark_fraction": 0.70,
      "twilight_fraction": 0.20,
      "endpoint_twilight": 0.10
    }
  },
  "source": {
    "call_sign": "VK4EMM",
    "receiver_grid": "QG62LR",
    "antenna_pair": "Loop2 330deg / Loop3 150deg",
    "date_range": "2026-05-05",
    "method": "directional antenna regression model"
  }
}
```

The exact schema can be revised after the first working port, but the data should remain transparent and easy to inspect.

## Input Data Modes

The JavaScript app needs to support two deliberately different data modes.

### Mode A: Directional Antenna CSV

Used for empirical validation and coefficient development.

Characteristics:

- local CSV input;
- includes antenna/source fields;
- supports short-path versus long-path validation;
- used to create or review model coefficients.

### Mode B: wspr.live-Style Data

Used for general reviewer/operator path analysis.

Characteristics:

- wspr.live-style rows;
- no directional antenna validation fields;
- useful for activity and theory scoring;
- confidence must be lower unless supported by other validation evidence.

The app should make clear which mode is being used.

## Porting Strategy

The port should be evidence-preserving. The JavaScript app should reproduce known Python results before the scientific method is changed.

Recommended build order:

1. Baseline audit

   Run the Python pipeline on known sample data and save the expected CSV/HTML outputs as comparison references.

2. Schema map

   Document the required input columns for:

   - directional antenna CSV files;
   - wspr.live-style CSV files;
   - JSON city/path/model files.

3. Pure calculation port

   Port and test these functions first:

   - Maidenhead grid to latitude/longitude;
   - haversine distance;
   - bearing calculations;
   - solar altitude;
   - short-path sampling;
   - long-path sampling;
   - dark fraction;
   - twilight fraction;
   - endpoint twilight score.

4. Theory v3 scoring port

   Port:

   - `theory_v3_score()`;
   - `theory_v3_classification()`;
   - confidence labels;
   - flags and witness labels.

5. Data import port

   Add browser support for:

   - local CSV file selection;
   - JSON loading;
   - wspr.live-style data where browser access permits.

6. Coefficient panel wiring

   Connect city-to-city selection to model coefficient lookup.

   Behaviour:

   - if model exists, populate read-only Model column;
   - if no model exists, leave Model column blank;
   - Trial column remains editable.

7. Ledger table

   Display a browser ledger equivalent to the Python reviewer ledger.

8. Reports and exports

   Add export features after calculations are verified:

   - CSV;
   - printable HTML/PDF;
   - possibly JSON export for trial coefficients.

9. Comparison testing

   For each test dataset, compare JavaScript output against Python output.

   Differences should be explained before changing either implementation.

## Testing Principle

The first JavaScript milestone is not visual polish.

The first milestone is numerical trust.

For each known test case, the JavaScript app should match the Python reference for:

- date;
- UTC slot;
- band;
- activity count;
- short dark fraction;
- long dark fraction;
- short twilight fraction;
- long twilight fraction;
- endpoint twilight score;
- short theory score;
- long theory score;
- final path indication;
- confidence.

Only after this comparison is stable should the UI be expanded.

## Git Workflow

Because the project is research-oriented and the working tree may contain experimental files, Git should be used conservatively.

Recommended pattern:

```bash
cd /home/john/Projects/long-path

git status

git add research/wspr_path_pipeline/PORTING_PLAN.md

git commit -m "Add JavaScript porting plan"

git push origin main
```

Before committing code changes, inspect `git status` and only add the files intended for that commit.

## Immediate Next Step

The next technical step should be a baseline audit.

That means:

1. Run the Python pipeline on the known sample input.
2. Record which output files are produced.
3. Choose a small set of reference rows for JavaScript comparison.
4. Create a minimal JavaScript test harness or browser diagnostic table.

After that, the actual JavaScript port can begin with the pure calculation functions.
