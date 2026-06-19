# Longitudinal WSPR Path Activity Study

## Purpose And Reader Requirements

### Purpose

The study will create a reproducible longitudinal atlas of **observed WSPR activity** between defined geographic endpoint areas. It will show how activity varies by path, amateur band, 30-minute UTC bin, day, month, season, year, solar-cycle phase, and relevant space-weather conditions.

The study will answer questions about when WSPR activity was observed. Ordinary WSPR records do not identify whether a signal travelled by short path or long path. Observed activity, independently validated path-direction evidence, and unknown or incomplete coverage must remain separate datasets and separate claims.

### Why The Study Is Worth Doing

Published research demonstrates that automated amateur-radio reporting networks can act as distributed ionospheric sounders and reveal large-scale ionospheric behaviour, including eclipse responses and travelling ionospheric disturbances. WSPR is designed to probe weak-signal propagation paths and provides a long historical record with time, band, transmitter, reporter, grid, and power information.

Most published studies concentrate on particular events or limited periods. The WSPR archive creates an opportunity to study repeatable path activity over much longer periods. The principal scientific challenge is separating propagation behaviour from changes in network participation, station availability, equipment, and data completeness.

### Potential Readers And Their Requirements

| Reader | What They Want To Learn | Required Output |
|---|---|---|
| Radio operators | When particular geographic paths and bands have historically shown activity | Daily matrices, typical opening/closing periods, seasonal comparisons |
| WSPR station operators | How their observations compare across time and with other stations or regions | Station/path summaries with completeness and metadata warnings |
| Propagation and ionospheric researchers | Which patterns repeat, change with season or solar activity, or differ by latitude and path geometry | Reproducible datasets, documented definitions, SQL-ready exports, uncertainty and coverage measures |
| Emergency communications groups | When activity has historically been observed between regions | Conservative availability summaries that do not imply a contact guarantee |
| Educators and reviewers | How time, geography, band, solar illumination, and space weather relate to observed activity | Clear visual reports, worked examples, definitions, and traceable source data |
| Future validation teams | Which paths and periods are suitable for targeted directional or scientific validation | Candidate-event lists kept separate from general observed activity |

### Literature-Informed Research Questions

1. What are the typical observed opening and closing periods for a defined endpoint pair on each band?
2. How stable are those periods across consecutive days, months, seasons, years, and solar-cycle phases?
3. How do path distance, endpoint latitude, path orientation, and local-time relationship affect observed activity?
4. Which activity patterns follow solar illumination and twilight, and which remain unexplained?
5. How does activity change during geomagnetic disturbances, solar flares, eclipses, and travelling ionospheric disturbances?
6. Which paths show repeatable multi-band transitions through a UTC day?
7. How much apparent change is caused by transmitter/reporter participation, outages, equipment changes, archive gaps, or query truncation?
8. Which findings reproduce across independent reporters and endpoint radii?
9. Where do observed activity patterns disagree with established propagation predictions or climatologies?
10. Which recurring or unusual periods justify a separate study using independent path-direction validation?

### Reader Trust Requirements

- Preserve original monthly source archives unchanged and record source URL, checksum, file size, and ingest date.
- Label every result as **observed activity**, **validated path evidence**, or **unknown/incomplete coverage**.
- Define “observed active”, “no observed activity”, and “unknown” before producing summaries.
- Record station participation, known outages, grid changes, and major equipment changes where available.
- Report source coverage, duplicate removal, rejected rows, schema changes, and result truncation.
- Never interpret no observed spots as proof that propagation was closed.
- Keep bands, dates, paths, endpoint areas, and validation methods separate unless a documented comparison explicitly requires them.
- Make calculations reproducible from archived source data and published query definitions.

### Initial Deliverables

1. Two-path Daily WSPR Path Matrix using imported WSPRnet data.
2. Data-completeness and station-metadata records.
3. Reproducible monthly archive ingestion and normalisation.
4. Daily, monthly, seasonal, annual, and solar-cycle activity summaries.
5. Documented candidate questions for later independent long-path validation research.

### Selected Literature

- Frissell et al., *Ionospheric Sounding Using Real-Time Amateur Radio Reporting Networks*, Space Weather (2014), DOI: [10.1002/2014SW001132](https://doi.org/10.1002/2014SW001132).
- Frissell et al., *Modeling Amateur Radio Soundings of the Ionospheric Response to the 2017 Great American Eclipse*, Geophysical Research Letters (2018), DOI: [10.1029/2018GL077324](https://doi.org/10.1029/2018GL077324).
- Frissell et al., *First Observations of Large Scale Traveling Ionospheric Disturbances Using Automated Amateur Radio Receiving Networks*, Geophysical Research Letters (2022), DOI: [10.1029/2022GL097879](https://doi.org/10.1029/2022GL097879).
- WSPR was designed for probing weak-signal propagation paths; protocol and software background: [WSJT-X documentation](https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main.html).
