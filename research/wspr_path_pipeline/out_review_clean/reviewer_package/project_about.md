
PROPAGATION PATH PROJECT

### CONTENTS

# Why This Work Is Needed

WSPR reports provide a large and useful record of HF propagation activity. However, current public WSPR spot data generally reports path distance as short-path distance and does not identify likely long-path propagation.

This leaves an important gap. Operators often care not only that a signal was heard, but which path was likely active, when that path tends to open, and how much confidence should be placed in that conclusion.

Our project is building a transparent evidence model that separates:

- Theory: solar illumination, grey-line state, band behaviour, regional activity, and repeatability.
- Validation: independent checks using directional antennas or other suitable methods.
- Review: scrutiny by experienced operators and propagation specialists.

The intention is to indicate times when HF radio propagation is available between two end-points:
- only on the long-path
- only on the short-path
- no propagation on either path
Validated with high confidence on bands 40m, 30m and 20m

## Chapter 1 Visual Story

Chapter 1 is for reviewers, radio operators, and interested users. It uses charts to explain the method of identifying long-path propagation - before asking the reader to inspect the detailed mathematics in chapter 3.

- `Visual_report.html` 

- Summary results with visual charts.

- How to read results

## Chapter 2: Terms And Variables

- `path_dominance_score`: `(Antenna_Loop2_spot_count - Antenna_Loop3_spont_count) / (Antenna_Loop2_count + Antenna_Loop3_count)`.
- `dark_difference`: short-path dark fraction minus long-path dark fraction.
- `greyline_difference`: short-path grey-line fraction minus long-path grey-line fraction.
- `endpoint_twilight`: the strongest endpoint twilight score for the receiver or transmitter endpoint.
- `coefficient`: the regression weight applied to a variable.
- `constant`: the baseline term in the regression equation; scientists may also call this the intercept.
- `R2`: coefficient of determination; a figure of merit for how much variation the model explains.

## Chapter 3: Scientific Notes

The current model uses solar altitude along sampled points on the short and long great-circle paths. Darkness and grey-line fractions are calculated from those sampled solar altitudes. The present model is a research tool, not a finished universal propagation law.

Detailed primary report:

- `visual_report.html`

## Draft Q And A

### Q1. How is share of twilight calculated?

In the current code, path twilight is calculated by sampling points along a great-circle path and counting the share of sampled points whose solar altitude is between -12 and +6 degrees. Endpoint twilight is separate: it scores how close each endpoint is to the horizon and currently uses the stronger endpoint score.

### Q2. Which twilight definition is used?

The current path-twilight band spans -12 to +6 degrees solar altitude. This includes the civil/nautical twilight region and a small daylight shoulder. It is deliberately broad for early research and should be reviewed by subject-matter experts.

### Q3. What does delta mean here?

Delta means difference. For example, `dark_delta = short_path_dark_fraction - long_path_dark_fraction`. `greyline_delta` is similarly `short_path_greyline_fraction - long_path_greyline_fraction`. A positive value favours the short path; a negative value favours the long path. It does not mean movement of the sun during the 30-minute bin.

### Q4. Is R2 calculated as an average across dates, bands, or paths?

No. Useful R2 must be calculated for the specific evidence being tested. The project is designed to support per-date, per-band, per-path, seasonal, and withheld-date validation R2. It does not use signal strength, SNR, or any weak-signal exclusion.

### Q5. Will the same coefficients apply for all paths and all latitudes?

That is not yet fully tested or proven. The current coefficients are fitted to the supplied VK4EMM Europe validation data. Other paths, seasons, latitudes, bands, and antenna systems may require separate validation - we are working on this.

### Q6. Will users be able to set a different radius for each endpoint?

Yes. That is included in the browser app design.

### Q7. What method relates endpoint radius to Maidenhead grids?

That method belongs mainly to the browser app. A practical method is to include stations or grid centres within the selected endpoint radius, and later review whether overlapping grid cells near the circumference should also be included.

### Q8. How do users capture spots per antenna?

The cleanest method is to capture and label spots at the station by antenna. If that is not available, two receiver call signs  can be used, one per directional antenna, provided the metadata remains transparent.

### Q9. Which assumptions have been tested?

Each empirical loop antenna counts whether Loop 2 and Loop 3 observations differ by time and band. The current regression tests whether selected solar/path variables can reproduce those empirical observations for the supplied data.

### Q10. Which assumptions remain unproven?

The universal applicability of coefficients, performance on unseen dates, performance on other paths, and the best twilight thresholds remain open research questions.

### Q11. How is dominance confidence determined as 1, 2, or 3?

Dominance confidence is based on antenna spot-count imbalance within one 30-minute bin. It is not a total activity score and it is not based on SNR.

In plain language, the method asks whether one loop antenna has clearly heard more spots than the other loop antenna in the same time slot. A clean one-sided result gives higher confidence than a nearly balanced result, even when the balanced result has more total spots.

The statistical check behind this is a conservative binomial test. It asks: if both loops were equally likely to hear a spot, how surprising is the observed imbalance? This helps avoid over-claiming path direction when the two antenna counts are too close together. It does not use signal strength, and it does not try to estimate front-to-back ratio.

- Score 3: strong evidence. At least 10 total spots and binomial-tail probability of 0.01 or lower.
- Score 2: moderate evidence. At least 5 total spots and binomial-tail probability of 0.05 or lower.
- Score 1: weak evidence. Binomial-tail probability of 0.25 or lower.
- Score 0: no clear evidence. There are no spots, antenna dominance is below 15 percent, or the imbalance is not statistically persuasive.

This means a smaller but strongly one-sided bin can score higher than a larger but nearly balanced bin.

### Q12. What is `enhanced_model_path_dominance_score`?

This is a diagnostic regression score. It uses the simple model variables plus extra terms such as band indicators, UTC time harmonics, receiver sun altitude, and transmitter sun altitude. It is useful for scientific comparison, but it is not the primary simple model explanation.

### Q13. What is path grey-line overlap?

Path grey-line overlap is a visual guide showing when sampled grey-line support is meaningfully present on the reference path during a 30-minute UTC bin. It is shown as a blue stripe in the sandwich. It is separate from the current regression variable `greyline_delta`, which remains part of the simple model until a revised model is tested.

### Q14. Should the model include overlapping and non-overlapping grey-line behaviour?

Probably, but this needs deliberate testing. A future model can compare overlap, short-path-only grey-line support, and long-path-only grey-line support as separate variables rather than hiding them in one combined term.

---------------------------------------------



