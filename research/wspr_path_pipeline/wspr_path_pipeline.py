#!/usr/bin/env python3
"""
Offline WSPR path research pipeline.

Inputs are raw fixed-loop spot CSV files from fixed Loop 2 / Loop 3 receiving
antennas at QG62LR. Outputs are binned feature rows, validation summaries,
and evidence reports.

This script intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import html
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median


RX_GRID = "QG62LR"
EUROPE_REFERENCE_LAT = 50.1109
EUROPE_REFERENCE_LON = 8.6821
LOOP2_BEARING_DEG = 330.0
LOOP3_BEARING_DEG = 150.0
EARTH_RADIUS_KM = 6371.0088
SOLAR_DEG = math.pi / 180.0
SCRIPT_DIR = Path(__file__).resolve().parent
THEORY_V3_DARK_WEIGHT = 0.70
THEORY_V3_TWILIGHT_WEIGHT = 0.20
THEORY_V3_ENDPOINT_WEIGHT = 0.10


def generated_utc_label() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_sig(value: float, digits: int = 3) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if 0.001 <= magnitude < 1_000_000:
        places = max(0, digits - int(math.floor(math.log10(magnitude))) - 1)
        text = f"{value:.{places}f}"
        return text.rstrip("0").rstrip(".") if "." in text else text
    return f"{value:.{digits}g}"


def csv_cell_value(value: object) -> object:
    if isinstance(value, float):
        return format_sig(value)
    return value


def dataclass_csv_row(row: object) -> dict[str, object]:
    return {key: csv_cell_value(value) for key, value in row.__dict__.items()}


def split_header_label(name: str) -> str:
    return "<br>".join(html.escape(part) for part in name.split("_"))


def write_table_html_report(
    rows: list[object],
    fieldnames: list[str],
    path: Path,
    title: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body_rows = []
    for row in rows:
        data = dataclass_csv_row(row)
        body_rows.append(
            "<tr>"
            + "".join(f"<td>{html.escape(str(data.get(field, '')))}</td>" for field in fieldnames)
            + "</tr>"
        )
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 20px; color: #17202a; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  p {{ color: #5d6d7e; margin: 0 0 14px; }}
  .table-wrap {{ max-height: 82vh; overflow: auto; border: 1px solid #d7dde5; }}
  table {{ border-collapse: collapse; font-size: 12px; min-width: 100%; }}
  th, td {{ border: 1px solid #d7dde5; padding: 5px 6px; text-align: right; white-space: nowrap; }}
  th {{ position: sticky; top: 0; background: #edf1f5; z-index: 1; vertical-align: bottom; line-height: 1.1; }}
  td:first-child, th:first-child {{ text-align: left; }}
  tr:nth-child(even) td {{ background: #fafbfc; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>Generated {html.escape(generated_utc_label())}. CSV companion keeps the same rows for spreadsheet or database analysis.</p>
<div class="table-wrap">
<table>
<thead><tr>{''.join(f'<th>{split_header_label(field)}</th>' for field in fieldnames)}</tr></thead>
<tbody>
{''.join(body_rows)}
</tbody>
</table>
</div>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")


@dataclass(frozen=True)
class FeatureRow:
    date_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    continent: str
    country_code: str
    tx_grid: str
    loop2_count: int
    loop3_count: int
    observation_count: int
    loop2_share: float
    path_dominance_score: float
    short_path_km: float
    long_path_km: float
    rx_short_path_bearing: float
    rx_long_path_bearing: float
    loop2_bearing_difference_short: float
    loop2_bearing_difference_long: float
    loop3_bearing_difference_short: float
    loop3_bearing_difference_long: float
    rx_sun_altitude: float
    tx_sun_altitude: float
    short_path_mean_sun_altitude: float
    long_path_mean_sun_altitude: float
    short_path_dark_fraction: float
    long_path_dark_fraction: float
    short_path_greyline_fraction: float
    long_path_greyline_fraction: float


@dataclass(frozen=True)
class EuropeDailyDominanceRow:
    date_utc: str
    month_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    eu_grid_cluster: str
    loop2_count: int
    loop3_count: int
    observation_count: int
    tx_grid_count: int
    absolute_margin: int
    path_dominance_score: float
    empirical_path: str


@dataclass(frozen=True)
class EuropeConfidenceRow:
    month_utc: str
    band_m: int
    utc_slot: str
    slot_index: int
    eu_grid_cluster: str
    days_observed: int
    total_observations: int
    median_margin: float
    mad_margin: float
    median_abs_margin: float
    consistency_rate: float
    confidence_ratio: float | None
    likely_path: str
    confidence: str


@dataclass(frozen=True)
class EuropeTheoryRow:
    date_utc: str
    month_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    eu_grid_cluster: str
    observed_short_path_spots: int
    observed_long_path_spots: int
    observation_count: int
    rx_greyline_score: float
    tx_greyline_score: float
    endpoint_overlap_score: float
    short_path_greyline_fraction: float
    long_path_greyline_fraction: float
    theory_short_score: float
    theory_long_score: float
    theory_short_path_spots: float
    theory_long_path_spots: float
    theory_margin: float
    observed_margin: int


@dataclass(frozen=True)
class EuropeChartRow:
    month_utc: str
    band_m: int
    utc_slot: str
    slot_index: int
    observed_short_path_spots: int
    observed_long_path_spots: int
    theory_short_path_spots: float
    theory_long_path_spots: float
    observed_margin: int
    theory_margin: float


@dataclass(frozen=True)
class EuropeDuskTheoryRow:
    date_utc: str
    month_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    eu_grid_cluster: str
    observed_long_path_spots: int
    observation_count: int
    rx_sun_altitude: float
    australian_dusk_score: float
    long_path_greyline_fraction: float
    theory_raw_score: float
    theory_long_path_spots: float


@dataclass(frozen=True)
class EuropeDuskChartRow:
    month_utc: str
    band_m: int
    utc_slot: str
    slot_index: int
    observed_long_path_spots: int
    theory_long_path_spots: float


@dataclass(frozen=True)
class EuropeEvidenceLedgerRow:
    date_utc: str
    month_utc: str
    band_m: int
    utc_slot: str
    slot_index: int
    eu_grid_cluster: str
    observed_short_path_spots: int
    observed_long_path_spots: int
    observation_count: int
    antenna_margin: int
    validation_short_indication: int
    validation_long_indication: int
    antenna_witness: str
    rx_sun_altitude: float
    tx_sun_altitude: float
    short_path_dark_fraction: float
    long_path_dark_fraction: float
    endpoint_greyline_witness: str
    sun_path_witness: str
    sme_rule_witness: str
    same_month_days_observed: int
    same_month_consistency_rate: float
    repeatability_witness: str
    ambiguity_flags: str
    final_path_indication: str
    confidence: str
    evidence_notes: str


@dataclass(frozen=True)
class ReviewerLedgerRow:
    date_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    region_grid: str
    activity: int
    short_dark_fraction: float
    long_dark_fraction: float
    short_twilight_fraction: float
    long_twilight_fraction: float
    endpoint_twilight_score: float
    short_theory_score: float
    long_theory_score: float
    score_margin: float
    sun_path_witness: str
    endpoint_greyline_witness: str
    repeatability_witness: str
    final_path_indication: str
    confidence: str
    flags: str
    propagation_rule: str
    directional_validation: str


@dataclass(frozen=True)
class EuropeBarTruthRow:
    date_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    loop2_count: int
    loop3_count: int
    observation_count: int
    path_dominance_score: float
    rx_sun_altitude: float
    tx_sun_altitude: float
    short_path_dark_fraction: float
    long_path_dark_fraction: float
    dark_delta: float
    short_path_greyline_fraction: float
    long_path_greyline_fraction: float
    greyline_delta: float
    endpoint_twilight_score: float


@dataclass(frozen=True)
class EuropeRegressionPredictionRow:
    date_utc: str
    utc_slot: str
    slot_index: int
    band_m: int
    loop2_count: int
    loop3_count: int
    observation_count: int
    observed_antenna_path_dominance_score: float
    simple_model_path_dominance_score: float
    enhanced_model_path_dominance_score: float
    simple_residual: float
    enhanced_residual: float
    model_predicted_loop2_count: float
    model_predicted_loop3_count: float

@dataclass(frozen=True)
class PathRegressionResult:
    path_id: str
    beta: list[float] | None
    weighted_r2: float | None
    unweighted_r2: float | None
    rows: list[EuropeBarTruthRow]


@dataclass(frozen=True)
class BandRegressionResult:
    band_m: int
    paths: dict[str, PathRegressionResult]
    rows: list[EuropeBarTruthRow]


def maidenhead_to_latlon(grid: str) -> tuple[float, float]:
    """Return approximate center latitude/longitude for a Maidenhead locator."""
    g = (grid or "").strip().upper()
    if len(g) < 4:
        raise ValueError(f"Maidenhead grid too short: {grid!r}")

    lon = (ord(g[0]) - ord("A")) * 20 - 180
    lat = (ord(g[1]) - ord("A")) * 10 - 90
    lon += int(g[2]) * 2
    lat += int(g[3]) * 1

    lon_size = 2.0
    lat_size = 1.0
    if len(g) >= 6:
        lon += (ord(g[4]) - ord("A")) * (5.0 / 60.0)
        lat += (ord(g[5]) - ord("A")) * (2.5 / 60.0)
        lon_size = 5.0 / 60.0
        lat_size = 2.5 / 60.0
    if len(g) >= 8:
        lon += int(g[6]) * (5.0 / 600.0)
        lat += int(g[7]) * (2.5 / 600.0)
        lon_size = 5.0 / 600.0
        lat_size = 2.5 / 600.0

    return lat + lat_size / 2.0, lon + lon_size / 2.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def bearing_difference_deg(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def interpolate_gc(lat1: float, lon1: float, lat2: float, lon2: float, f: float) -> tuple[float, float]:
    """Spherical interpolation along the short great-circle path."""
    p1 = math.radians(lat1)
    l1 = math.radians(lon1)
    p2 = math.radians(lat2)
    l2 = math.radians(lon2)
    d = 2 * math.asin(math.sqrt(
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2
    ))
    if d == 0:
        return lat1, lon1
    a = math.sin((1 - f) * d) / math.sin(d)
    b = math.sin(f * d) / math.sin(d)
    x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
    y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
    z = a * math.sin(p1) + b * math.sin(p2)
    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))
    return lat, ((lon + 540.0) % 360.0) - 180.0


def ll_to_vector(lat: float, lon: float) -> tuple[float, float, float]:
    p = math.radians(lat)
    l = math.radians(lon)
    return math.cos(p) * math.cos(l), math.cos(p) * math.sin(l), math.sin(p)


def vector_to_ll(v: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = v
    norm = math.sqrt(x * x + y * y + z * z)
    x, y, z = x / norm, y / norm, z / norm
    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))
    return lat, ((lon + 540.0) % 360.0) - 180.0


def cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(dot(v, v))
    if norm == 0:
        return 0.0, 0.0, 0.0
    return v[0] / norm, v[1] / norm, v[2] / norm


def rotate_vector(
    v: tuple[float, float, float],
    axis: tuple[float, float, float],
    angle: float,
) -> tuple[float, float, float]:
    """Rodrigues rotation of vector v around unit axis by angle radians."""
    c = math.cos(angle)
    s = math.sin(angle)
    axv = cross(axis, v)
    adv = dot(axis, v)
    return (
        v[0] * c + axv[0] * s + axis[0] * adv * (1 - c),
        v[1] * c + axv[1] * s + axis[1] * adv * (1 - c),
        v[2] * c + axv[2] * s + axis[2] * adv * (1 - c),
    )


def interpolate_long_gc(lat1: float, lon1: float, lat2: float, lon2: float, f: float) -> tuple[float, float]:
    """Interpolate along the complementary long great-circle arc."""
    u = ll_to_vector(lat1, lon1)
    v = ll_to_vector(lat2, lon2)
    normal = normalize(cross(u, v))
    central = math.acos(min(1.0, max(-1.0, dot(u, v))))
    if central == 0:
        return lat1, lon1
    angle = -f * (2.0 * math.pi - central)
    return vector_to_ll(rotate_vector(u, normal, angle))


def day_of_year(dt: datetime) -> int:
    return int(dt.strftime("%j"))


def sun_declination_and_eqtime(dt: datetime) -> tuple[float, float]:
    """NOAA-style approximate declination in radians and equation of time in minutes."""
    n = day_of_year(dt)
    minutes = dt.hour * 60 + dt.minute + dt.second / 60.0
    gamma = 2.0 * math.pi / 365.0 * (n - 1 + (minutes - 720.0) / 1440.0)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    return decl, eqtime


def solar_altitude_deg(lat: float, lon: float, dt: datetime) -> float:
    decl, eqtime = sun_declination_and_eqtime(dt)
    minutes = dt.hour * 60 + dt.minute + dt.second / 60.0
    true_solar_time = (minutes + eqtime + 4.0 * lon) % 1440.0
    hour_angle = true_solar_time / 4.0 - 180.0
    lat_rad = math.radians(lat)
    ha_rad = math.radians(hour_angle)
    cos_zenith = (
        math.sin(lat_rad) * math.sin(decl)
        + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    )
    cos_zenith = min(1.0, max(-1.0, cos_zenith))
    return 90.0 - math.degrees(math.acos(cos_zenith))


def path_solar_features(
    rx_lat: float,
    rx_lon: float,
    tx_lat: float,
    tx_lon: float,
    dt: datetime,
    long_path: bool,
    samples: int = 25,
) -> tuple[float, float, float]:
    alts: list[float] = []
    for i in range(samples):
        f = i / (samples - 1)
        if long_path:
            lat, lon = interpolate_long_gc(rx_lat, rx_lon, tx_lat, tx_lon, f)
        else:
            lat, lon = interpolate_gc(rx_lat, rx_lon, tx_lat, tx_lon, f)
        alts.append(solar_altitude_deg(lat, lon, dt))
    dark_fraction = sum(1 for a in alts if a < 0.0) / len(alts)
    greyline_fraction = sum(1 for a in alts if -6.0 <= a <= 6.0) / len(alts)
    return mean(alts), dark_fraction, greyline_fraction


def path_darkness_theory_features(
    rx_lat: float,
    rx_lon: float,
    tx_lat: float,
    tx_lon: float,
    dt: datetime,
    long_path: bool,
    samples: int = 25,
) -> tuple[float, float]:
    alts: list[float] = []
    for i in range(samples):
        f = i / (samples - 1)
        if long_path:
            lat, lon = interpolate_long_gc(rx_lat, rx_lon, tx_lat, tx_lon, f)
        else:
            lat, lon = interpolate_gc(rx_lat, rx_lon, tx_lat, tx_lon, f)
        alts.append(solar_altitude_deg(lat, lon, dt))
    dark_fraction = sum(1 for alt in alts if alt < -6.0) / len(alts)
    twilight_fraction = sum(1 for alt in alts if -12.0 <= alt <= 6.0) / len(alts)
    return dark_fraction, twilight_fraction


def slot_from_dt(dt: datetime) -> tuple[int, str]:
    slot = dt.hour * 2 + (1 if dt.minute >= 30 else 0)
    return slot, f"{slot // 2:02d}:{(slot % 2) * 30:02d}"


def dt_from_wspr_live_time(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def dt_from_ms(ms: str) -> datetime:
    return datetime.fromtimestamp(int(float(ms)) / 1000.0, tz=timezone.utc)


def read_raw_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                row["_source_file"] = path.name
                rows.append(row)
    return rows


def build_feature_rows(raw_rows: list[dict[str, str]]) -> list[FeatureRow]:
    rx_lat, rx_lon = maidenhead_to_latlon(RX_GRID)
    grouped: dict[tuple[str, int, str, int, str, str, str], Counter[str]] = defaultdict(Counter)
    dt_by_key: dict[tuple[str, int, str, int, str, str, str], datetime] = {}

    for row in raw_rows:
        antenna = row.get("antenna", "").strip()
        if antenna not in {"Loop 2", "Loop 3"}:
            continue
        band = int(float(row["band"]))
        if band not in {20, 30, 40}:
            continue
        dt = dt_from_ms(row["utc_timestamp"])
        slot_index, slot_label = slot_from_dt(dt)
        key = (
            dt.date().isoformat(),
            slot_index,
            slot_label,
            band,
            row.get("continent", "").strip() or "Unknown",
            row.get("country_code", "").strip() or "Unknown",
            row.get("tx_grid", "").strip().upper(),
        )
        grouped[key][antenna] += 1
        dt_by_key[key] = dt.replace(minute=0 if slot_index % 2 == 0 else 30, second=0, microsecond=0)

    feature_rows: list[FeatureRow] = []
    for key, counts in sorted(grouped.items()):
        date_utc, slot_index, slot_label, band, continent, country_code, tx_grid = key
        loop2 = counts["Loop 2"]
        loop3 = counts["Loop 3"]
        total = loop2 + loop3
        if total == 0:
            continue
        try:
            tx_lat, tx_lon = maidenhead_to_latlon(tx_grid)
        except ValueError:
            continue
        dt = dt_by_key[key]
        sp_km = haversine_km(rx_lat, rx_lon, tx_lat, tx_lon)
        lp_km = 2.0 * math.pi * EARTH_RADIUS_KM - sp_km
        sp_bearing = initial_bearing_deg(rx_lat, rx_lon, tx_lat, tx_lon)
        lp_bearing = (sp_bearing + 180.0) % 360.0
        rx_alt = solar_altitude_deg(rx_lat, rx_lon, dt)
        tx_alt = solar_altitude_deg(tx_lat, tx_lon, dt)
        sp_mean_alt, sp_dark, sp_gl = path_solar_features(rx_lat, rx_lon, tx_lat, tx_lon, dt, False)
        lp_mean_alt, lp_dark, lp_gl = path_solar_features(rx_lat, rx_lon, tx_lat, tx_lon, dt, True)

        feature_rows.append(FeatureRow(
            date_utc=date_utc,
            utc_slot=slot_label,
            slot_index=slot_index,
            band_m=band,
            continent=continent,
            country_code=country_code,
            tx_grid=tx_grid,
            loop2_count=loop2,
            loop3_count=loop3,
            observation_count=total,
            loop2_share=loop2 / total,
            path_dominance_score=(loop2 - loop3) / total,
            short_path_km=sp_km,
            long_path_km=lp_km,
            rx_short_path_bearing=sp_bearing,
            rx_long_path_bearing=lp_bearing,
            loop2_bearing_difference_short=bearing_difference_deg(LOOP2_BEARING_DEG, sp_bearing),
            loop2_bearing_difference_long=bearing_difference_deg(LOOP2_BEARING_DEG, lp_bearing),
            loop3_bearing_difference_short=bearing_difference_deg(LOOP3_BEARING_DEG, sp_bearing),
            loop3_bearing_difference_long=bearing_difference_deg(LOOP3_BEARING_DEG, lp_bearing),
            rx_sun_altitude=rx_alt,
            tx_sun_altitude=tx_alt,
            short_path_mean_sun_altitude=sp_mean_alt,
            long_path_mean_sun_altitude=lp_mean_alt,
            short_path_dark_fraction=sp_dark,
            long_path_dark_fraction=lp_dark,
            short_path_greyline_fraction=sp_gl,
            long_path_greyline_fraction=lp_gl,
        ))
    return feature_rows


def write_feature_csv(rows: list[FeatureRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(FeatureRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dataclass_csv_row(row))
    write_table_html_report(rows, fieldnames, path.with_name(f"{path.stem}_table.html"), "WSPR Path Features")


def write_continent_summary_csv(rows: list[FeatureRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str, int, int, str], Counter[str]] = defaultdict(Counter)
    for row in rows:
        key = (row.date_utc, row.utc_slot, row.slot_index, row.band_m, row.continent)
        grouped[key]["loop2_count"] += row.loop2_count
        grouped[key]["loop3_count"] += row.loop3_count
        grouped[key]["observation_count"] += row.observation_count
        grouped[key]["tx_grid_count"] += 1

    fieldnames = [
        "date_utc",
        "utc_slot",
        "slot_index",
        "band_m",
        "continent",
        "loop2_count",
        "loop3_count",
        "observation_count",
        "tx_grid_count",
        "loop2_share",
        "path_dominance_score",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key, counts in sorted(grouped.items()):
            date_utc, utc_slot, slot_index, band_m, continent = key
            loop2 = counts["loop2_count"]
            loop3 = counts["loop3_count"]
            total = counts["observation_count"]
            writer.writerow({
                "date_utc": date_utc,
                "utc_slot": utc_slot,
                "slot_index": slot_index,
                "band_m": band_m,
                "continent": continent,
                "loop2_count": loop2,
                "loop3_count": loop3,
                "observation_count": total,
                "tx_grid_count": counts["tx_grid_count"],
                "loop2_share": f"{loop2 / total:.6f}" if total else "",
                "path_dominance_score": f"{(loop2 - loop3) / total:.6f}" if total else "",
            })


def eu_grid_cluster(tx_grid: str) -> str:
    """Broad Europe grid cluster. First two Maidenhead characters are intentional for v1."""
    g = (tx_grid or "").strip().upper()
    return g[:2] if len(g) >= 2 else "UNKNOWN"


def empirical_path_from_margin(margin: int) -> str:
    if margin > 0:
        return "short_path_loop2"
    if margin < 0:
        return "long_path_loop3"
    return "mixed"


def build_europe_daily_dominance_rows(rows: list[FeatureRow]) -> list[EuropeDailyDominanceRow]:
    grouped: dict[tuple[str, str, int, int, str], Counter[str]] = defaultdict(Counter)
    for row in rows:
        if row.continent != "Europe":
            continue
        key = (row.date_utc, row.utc_slot, row.slot_index, row.band_m, eu_grid_cluster(row.tx_grid))
        grouped[key]["loop2_count"] += row.loop2_count
        grouped[key]["loop3_count"] += row.loop3_count
        grouped[key]["observation_count"] += row.observation_count
        grouped[key]["tx_grid_count"] += 1

    out: list[EuropeDailyDominanceRow] = []
    for key, counts in sorted(grouped.items()):
        date_utc, utc_slot, slot_index, band_m, grid_cluster = key
        loop2 = counts["loop2_count"]
        loop3 = counts["loop3_count"]
        total = counts["observation_count"]
        if total == 0:
            continue
        margin = loop2 - loop3
        out.append(EuropeDailyDominanceRow(
            date_utc=date_utc,
            month_utc=date_utc[:7],
            utc_slot=utc_slot,
            slot_index=slot_index,
            band_m=band_m,
            eu_grid_cluster=grid_cluster,
            loop2_count=loop2,
            loop3_count=loop3,
            observation_count=total,
            tx_grid_count=counts["tx_grid_count"],
            absolute_margin=margin,
            path_dominance_score=margin / total,
            empirical_path=empirical_path_from_margin(margin),
        ))
    return out


def write_europe_daily_dominance_csv(rows: list[EuropeDailyDominanceRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeDailyDominanceRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            data["path_dominance_score"] = f"{row.path_dominance_score:.6f}"
            writer.writerow(data)


def median_absolute_deviation(values: list[float], med: float | None = None) -> float:
    if not values:
        return 0.0
    center = median(values) if med is None else med
    return float(median([abs(v - center) for v in values]))


def confidence_label(
    likely_path: str,
    days_observed: int,
    median_abs_margin: float,
    mad_margin: float,
    consistency_rate: float,
) -> tuple[str, float | None]:
    if likely_path == "mixed" or days_observed == 0:
        return "No clear indication", None

    if mad_margin == 0:
        ratio = None if median_abs_margin == 0 else math.inf
    else:
        ratio = median_abs_margin / mad_margin

    ratio_ok_high = ratio == math.inf or (ratio is not None and ratio >= 3.0)
    ratio_ok_medium = ratio == math.inf or (ratio is not None and ratio >= 2.0)
    ratio_ok_low = ratio == math.inf or (ratio is not None and ratio >= 1.0)

    if days_observed >= 3 and consistency_rate >= 0.75 and median_abs_margin >= 5 and ratio_ok_high:
        return "High confidence", ratio
    if days_observed >= 2 and consistency_rate >= 0.75 and median_abs_margin >= 3 and ratio_ok_medium:
        return "Medium confidence", ratio
    if consistency_rate >= 0.50 and median_abs_margin >= 1 and ratio_ok_low:
        return "Low confidence", ratio
    return "No clear indication", ratio


def build_europe_confidence_rows(
    daily_rows: list[EuropeDailyDominanceRow],
    by_month: bool = False,
) -> list[EuropeConfidenceRow]:
    grouped: dict[tuple[str, int, str, int, str], list[EuropeDailyDominanceRow]] = defaultdict(list)
    for row in daily_rows:
        month = row.month_utc if by_month else "all"
        grouped[(month, row.band_m, row.utc_slot, row.slot_index, row.eu_grid_cluster)].append(row)

    out: list[EuropeConfidenceRow] = []
    for key, group in sorted(grouped.items()):
        month_utc, band_m, utc_slot, slot_index, grid_cluster = key
        margins = [float(r.absolute_margin) for r in group]
        med_margin = float(median(margins))
        mad = median_absolute_deviation(margins, med_margin)
        med_abs = abs(med_margin)
        if med_margin > 0:
            likely_path = "short_path_loop2"
            consistent = sum(1 for m in margins if m > 0)
        elif med_margin < 0:
            likely_path = "long_path_loop3"
            consistent = sum(1 for m in margins if m < 0)
        else:
            likely_path = "mixed"
            consistent = sum(1 for m in margins if m == 0)
        consistency_rate = consistent / len(group)
        confidence, ratio = confidence_label(likely_path, len(group), med_abs, mad, consistency_rate)
        out.append(EuropeConfidenceRow(
            month_utc=month_utc,
            band_m=band_m,
            utc_slot=utc_slot,
            slot_index=slot_index,
            eu_grid_cluster=grid_cluster,
            days_observed=len({r.date_utc for r in group}),
            total_observations=sum(r.observation_count for r in group),
            median_margin=med_margin,
            mad_margin=mad,
            median_abs_margin=med_abs,
            consistency_rate=consistency_rate,
            confidence_ratio=ratio,
            likely_path=likely_path,
            confidence=confidence,
        ))
    return out


def write_europe_confidence_csv(rows: list[EuropeConfidenceRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeConfidenceRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            for key in ["median_margin", "mad_margin", "median_abs_margin", "consistency_rate"]:
                data[key] = f"{data[key]:.6f}"
            ratio = row.confidence_ratio
            if ratio is None:
                data["confidence_ratio"] = ""
            elif ratio == math.inf:
                data["confidence_ratio"] = "inf"
            else:
                data["confidence_ratio"] = f"{ratio:.6f}"
            writer.writerow(data)


def write_europe_validation_report(
    daily_rows: list[EuropeDailyDominanceRow],
    confidence_rows: list[EuropeConfidenceRow],
    monthly_confidence_rows: list[EuropeConfidenceRow],
    theory_rows: list[EuropeTheoryRow],
    chart_rows: list[EuropeChartRow],
    path: Path,
) -> None:
    by_band = Counter(r.band_m for r in daily_rows)
    by_month_band = Counter((r.month_utc, r.band_m) for r in daily_rows)
    obs_by_band = Counter()
    obs_by_month_band = Counter()
    obs_by_band_slot = Counter()
    for row in daily_rows:
        obs_by_band[row.band_m] += row.observation_count
        obs_by_month_band[(row.month_utc, row.band_m)] += row.observation_count
        obs_by_band_slot[(row.band_m, row.slot_index, row.utc_slot)] += row.observation_count
    by_conf = Counter(r.confidence for r in confidence_rows)
    by_month_conf = Counter((r.month_utc, r.confidence) for r in monthly_confidence_rows)
    path_counts = Counter(r.likely_path for r in confidence_rows)
    dates = sorted({r.date_utc for r in daily_rows})
    months = sorted({r.month_utc for r in daily_rows})

    lines: list[str] = []
    lines.append("# Europe Summary Report")
    lines.append("")
    lines.append(f"Generated: {generated_utc_label()}")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append("This validation summary uses only Europe spots received at QG62LR by the two fixed validation loops.")
    lines.append("")
    lines.append("- Loop 2, 330 deg: validation evidence for short-path-to-Europe activity")
    lines.append("- Loop 3, 150 deg: validation evidence for long-path-to-Europe activity")
    lines.append("- Bands: 20m, 30m, 40m")
    lines.append("- Time resolution: 30-minute UTC bins")
    lines.append("- Europe area grouping: first two Maidenhead grid characters")
    lines.append("")
    lines.append("## Dataset")
    lines.append(f"- Dates: {', '.join(dates)}")
    lines.append(f"- Daily dominance rows: {len(daily_rows):,}")
    lines.append(f"- Confidence rows: {len(confidence_rows):,}")
    lines.append(f"- Europe loop observations represented: {sum(r.observation_count for r in daily_rows):,}")
    lines.append("")
    lines.append("## Europe Observations By Band")
    for band in sorted(by_band):
        lines.append(f"- {band}m: {by_band[band]:,} daily rows, {obs_by_band[band]:,} observations")
    lines.append("")
    lines.append("## Europe Observations By Month And Band")
    for month in months:
        parts = []
        for band in sorted(by_band):
            rows = by_month_band[(month, band)]
            obs = obs_by_month_band[(month, band)]
            if rows or obs:
                parts.append(f"{band}m: {rows:,} rows / {obs:,} obs")
        lines.append(f"- {month}: " + "; ".join(parts))
    lines.append("")
    lines.append("## Validation Confidence Summary")
    for label in ["High confidence", "Medium confidence", "Low confidence", "No clear indication"]:
        lines.append(f"- {label}: {by_conf[label]:,} rows")
    lines.append("")
    lines.append("## Monthly Validation Confidence Summary")
    for month in months:
        parts = []
        for label in ["High confidence", "Medium confidence", "Low confidence", "No clear indication"]:
            parts.append(f"{label}: {by_month_conf[(month, label)]:,}")
        lines.append(f"- {month}: " + "; ".join(parts))
    lines.append("")
    lines.append("## Europe Activity By UTC Slot And Band")
    lines.append("")
    lines.append("Activity is the total Europe loop observations in the raw validation files for each UTC slot and band.")
    for band in sorted(by_band):
        lines.append("")
        lines.append(f"### {band}m")
        lines.append("")
        lines.append("| UTC | Observations |")
        lines.append("| --- | ---: |")
        for band_m, _slot_index, utc_slot in sorted(obs_by_band_slot):
            if band_m != band:
                continue
            lines.append(f"| {utc_slot} | {obs_by_band_slot[(band_m, _slot_index, utc_slot)]} |")
    lines.append("")
    lines.append("## Likely Path Summary")
    for label in ["short_path_loop2", "long_path_loop3", "mixed"]:
        lines.append(f"- {label}: {path_counts[label]:,} rows")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("For each date, band, UTC slot, and Europe grid cluster:")
    lines.append("")
    lines.append("- More Loop 2 spots favour short-path evidence.")
    lines.append("- More Loop 3 spots favour long-path evidence.")
    lines.append("- Similar Loop 2 and Loop 3 spot counts are mixed.")
    lines.append("")
    lines.append("Across days, the pipeline calculates median margin, MAD of margin, consistency rate, and a confidence label.")
    lines.append("No Europe bins are excluded for low observation count.")
    lines.append("")
    lines.append("## Strongest Current Indications By Band")
    strong_rows = [
        r for r in confidence_rows
        if r.confidence in {"High confidence", "Medium confidence"}
    ]
    if not strong_rows:
        lines.append("")
        lines.append("No rows yet exceed the medium-confidence threshold.")
    for band in sorted({r.band_m for r in strong_rows}):
        band_rows = sorted(
            [r for r in strong_rows if r.band_m == band],
            key=lambda r: (
                r.slot_index,
                r.eu_grid_cluster,
                0 if r.confidence == "High confidence" else 1,
                -r.median_abs_margin,
            ),
        )
        lines.append("")
        lines.append(f"### {band}m")
        lines.append("")
        lines.append("| # | UTC | EU Grid | Likely path | Confidence | Median margin | MAD | Consistency | Days | Observations |")
        lines.append("| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for line_no, row in enumerate(band_rows, 1):
            lines.append(
                f"| {line_no} | {row.utc_slot} | {row.eu_grid_cluster} | {row.likely_path} | "
                f"{row.confidence} | {row.median_margin:.1f} | {row.mad_margin:.1f} | "
                f"{row.consistency_rate:.2f} | {row.days_observed} | {row.total_observations} |"
            )
    lines.append("")
    lines.append("## Next Step")
    lines.append("")
    lines.append("Inspect these validation rows before treating the grey-line theory-v1 output as explanatory.")
    lines.append("")
    lines.append("## Theory V1: Grey-Line Diagnostic")
    lines.append("")
    lines.append("Theory v1 is deliberately primitive. It compares observed loop spots with a broad grey-line score.")
    lines.append("It uses sampled short-path and long-path grey-line fractions plus a small endpoint-overlap boost.")
    lines.append("")
    lines.append("Generated files:")
    lines.append("")
    lines.append("- `europe_theory_v1_greyline.csv`")
    lines.append("- `europe_chart_by_band.csv`")
    lines.append("- `europe_theory_v1_charts.html`")
    lines.append("- `europe_theory_v2_dusk.csv`")
    lines.append("- `europe_dusk_chart_by_band.csv`")
    lines.append("- `europe_theory_v2_dusk_charts.html`")
    lines.append("")
    lines.append("The chart file is aggregated by band and UTC slot, including an `all` month row and separate month rows.")
    lines.append("Columns are ready for side-by-side observed/theory bar charts for short-path and long-path activity.")
    lines.append("")
    lines.append(f"- Theory rows: {len(theory_rows):,}")
    lines.append(f"- Chart rows: {len(chart_rows):,}")
    lines.append("")
    lines.append("Theory V2 focuses on long-path receiver-side dusk illumination at QG62LR. Review 30m first; 40m is included as a reference band with fewer spots.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def one_hot(value: str, choices: list[str]) -> list[float]:
    return [1.0 if value == c else 0.0 for c in choices]


def model_matrix(rows: list[FeatureRow]) -> tuple[list[str], list[list[float]], list[float], list[float]]:
    continents = sorted({r.continent for r in rows})
    bands = [30, 40]  # 20m is the constant-term baseline.
    names = [
        "constant",
        "short_path_km",
        "long_path_km",
        "loop2_error_short",
        "loop2_error_long",
        "loop3_error_short",
        "loop3_error_long",
        "rx_sun_alt",
        "tx_sun_alt",
        "short_dark",
        "long_dark",
        "short_greyline",
        "long_greyline",
        "band_30m",
        "band_40m",
        *[f"continent_{c}" for c in continents[1:]],
    ]
    x: list[list[float]] = []
    y: list[float] = []
    w: list[float] = []
    for r in rows:
        x.append([
            1.0,
            r.short_path_km / 10000.0,
            r.long_path_km / 10000.0,
            r.loop2_bearing_difference_short / 180.0,
            r.loop2_bearing_difference_long / 180.0,
            r.loop3_bearing_difference_short / 180.0,
            r.loop3_bearing_difference_long / 180.0,
            r.rx_sun_altitude / 90.0,
            r.tx_sun_altitude / 90.0,
            r.short_path_dark_fraction,
            r.long_path_dark_fraction,
            r.short_path_greyline_fraction,
            r.long_path_greyline_fraction,
            *[1.0 if r.band_m == b else 0.0 for b in bands],
            *one_hot(r.continent, continents)[1:],
        ])
        y.append(r.path_dominance_score)
        w.append(float(r.observation_count))
    return names, x, y, w


def solve_linear(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            aug[col][col] += 1e-8
            pivot = col
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [v / div for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            aug[r] = [v - factor * aug[col][c] for c, v in enumerate(aug[r])]
    return [aug[i][-1] for i in range(n)]


def fit_wls(x: list[list[float]], y: list[float], weights: list[float] | None = None) -> list[float]:
    rows = len(x)
    cols = len(x[0])
    weights = weights or [1.0] * rows
    xtx = [[0.0] * cols for _ in range(cols)]
    xty = [0.0] * cols
    ridge = 1e-8
    for row, target, weight in zip(x, y, weights):
        for i in range(cols):
            xty[i] += weight * row[i] * target
            for j in range(cols):
                xtx[i][j] += weight * row[i] * row[j]
    for i in range(1, cols):
        xtx[i][i] += ridge
    return solve_linear(xtx, xty)


def predict(x: list[list[float]], beta: list[float]) -> list[float]:
    return [sum(v * b for v, b in zip(row, beta)) for row in x]


def r2_score(y: list[float], pred: list[float], weights: list[float] | None = None) -> float:
    weights = weights or [1.0] * len(y)
    wsum = sum(weights)
    ybar = sum(v * w for v, w in zip(y, weights)) / wsum
    ss_res = sum(w * (v - p) ** 2 for v, p, w in zip(y, pred, weights))
    ss_tot = sum(w * (v - ybar) ** 2 for v, w in zip(y, weights))
    return 1.0 - ss_res / ss_tot if ss_tot else 0.0


def binomial_tail_equal_probability(total: int, dominant_count: int) -> float:
    if total <= 0 or dominant_count <= total / 2:
        return 1.0
    probability = 0.0
    for k in range(dominant_count, total + 1):
        probability += math.comb(total, k) * (0.5 ** total)
    return probability


def clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def build_europe_bar_truth_rows(rows: list[FeatureRow]) -> list[EuropeBarTruthRow]:
    grouped: dict[tuple[str, str, int, int], list[FeatureRow]] = defaultdict(list)
    for row in rows:
        if row.continent == "Europe":
            grouped[(row.date_utc, row.utc_slot, row.slot_index, row.band_m)].append(row)

    out: list[EuropeBarTruthRow] = []
    for key, group in sorted(grouped.items()):
        date_utc, utc_slot, slot_index, band_m = key
        loop2 = sum(row.loop2_count for row in group)
        loop3 = sum(row.loop3_count for row in group)
        total = loop2 + loop3
        if total <= 0:
            continue
        rx_alt = weighted_average([(row.rx_sun_altitude, row.observation_count) for row in group])
        tx_alt = weighted_average([(row.tx_sun_altitude, row.observation_count) for row in group])
        short_dark = weighted_average([(row.short_path_dark_fraction, row.observation_count) for row in group])
        long_dark = weighted_average([(row.long_path_dark_fraction, row.observation_count) for row in group])
        short_greyline = weighted_average([(row.short_path_greyline_fraction, row.observation_count) for row in group])
        long_greyline = weighted_average([(row.long_path_greyline_fraction, row.observation_count) for row in group])
        endpoint_twilight = max(greyline_altitude_score(rx_alt), greyline_altitude_score(tx_alt))
        out.append(EuropeBarTruthRow(
            date_utc=date_utc,
            utc_slot=utc_slot,
            slot_index=slot_index,
            band_m=band_m,
            loop2_count=loop2,
            loop3_count=loop3,
            observation_count=total,
            path_dominance_score=(loop2 - loop3) / total,
            rx_sun_altitude=rx_alt,
            tx_sun_altitude=tx_alt,
            short_path_dark_fraction=short_dark,
            long_path_dark_fraction=long_dark,
            dark_delta=short_dark - long_dark,
            short_path_greyline_fraction=short_greyline,
            long_path_greyline_fraction=long_greyline,
            greyline_delta=short_greyline - long_greyline,
            endpoint_twilight_score=endpoint_twilight,
        ))
    return out


def write_europe_bar_truth_csv(rows: list[EuropeBarTruthRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeBarTruthRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dataclass_csv_row(row))
    write_table_html_report(rows, fieldnames, path.with_name(f"{path.stem}_table.html"), "Europe Bar Truth")


def simple_europe_regression_names() -> list[str]:
    return ["constant", "dark_delta", "greyline_delta", "endpoint_twilight"]


def simple_europe_regression_vector(row: EuropeBarTruthRow) -> list[float]:
    return [
        1.0,
        row.dark_delta,
        row.greyline_delta,
        row.endpoint_twilight_score,
    ]


def enhanced_europe_regression_names() -> list[str]:
    return [
        "constant",
        "band_30m",
        "band_40m",
        "dark_delta",
        "greyline_delta",
        "endpoint_twilight",
        "utc_sin_1",
        "utc_cos_1",
        "utc_sin_2",
        "utc_cos_2",
        "utc_sin_3",
        "utc_cos_3",
        "rx_sun_alt",
        "tx_sun_alt",
    ]


def enhanced_europe_regression_vector(row: EuropeBarTruthRow) -> list[float]:
    phase = row.slot_index / 48.0 * 2.0 * math.pi
    return [
        1.0,
        1.0 if row.band_m == 30 else 0.0,
        1.0 if row.band_m == 40 else 0.0,
        row.dark_delta,
        row.greyline_delta,
        row.endpoint_twilight_score,
        math.sin(phase),
        math.cos(phase),
        math.sin(2.0 * phase),
        math.cos(2.0 * phase),
        math.sin(3.0 * phase),
        math.cos(3.0 * phase),
        row.rx_sun_altitude / 90.0,
        row.tx_sun_altitude / 90.0,
    ]


def fit_europe_bar_regression(
    rows: list[EuropeBarTruthRow],
    vector_fn,
) -> tuple[list[float], list[float], list[float], list[float]]:
    x = [vector_fn(row) for row in rows]
    y = [row.path_dominance_score for row in rows]
    weights = [float(row.observation_count) for row in rows]
    beta = fit_wls(x, y, weights)
    pred = predict(x, beta)
    return beta, pred, y, weights


def truth_row_key(row: EuropeBarTruthRow) -> tuple[str, int]:
    return row.date_utc, row.slot_index


def path_training_rows(rows: list[EuropeBarTruthRow], path_id: str) -> list[EuropeBarTruthRow]:
    if path_id not in {"short", "long"}:
        raise ValueError(f"Unknown path_id: {path_id}")
    return [row for row in rows if row.observation_count > 0]


def path_target_share(row: EuropeBarTruthRow, path_id: str) -> float:
    if path_id == "short":
        return row.loop2_count / row.observation_count
    if path_id == "long":
        return row.loop3_count / row.observation_count
    raise ValueError(f"Unknown path_id: {path_id}")


def fit_path_regression(rows: list[EuropeBarTruthRow], path_id: str) -> PathRegressionResult:
    training_rows = path_training_rows(rows, path_id)
    if len(training_rows) < len(simple_europe_regression_names()):
        return PathRegressionResult(path_id, None, None, None, training_rows)
    x = [simple_europe_regression_vector(row) for row in training_rows]
    y = [path_target_share(row, path_id) for row in training_rows]
    weights = [float(row.observation_count) for row in training_rows]
    beta = fit_wls(x, y, weights)
    pred = predict(x, beta)
    return PathRegressionResult(
        path_id=path_id,
        beta=beta,
        weighted_r2=r2_score(y, pred, weights),
        unweighted_r2=r2_score(y, pred),
        rows=training_rows,
    )


def fit_band_simple_regressions(rows: list[EuropeBarTruthRow]) -> dict[int, BandRegressionResult]:
    results: dict[int, BandRegressionResult] = {}
    for band in sorted({row.band_m for row in rows}):
        band_rows = [row for row in rows if row.band_m == band]
        results[band] = BandRegressionResult(
            band_m=band,
            paths={
                "short": fit_path_regression(band_rows, "short"),
                "long": fit_path_regression(band_rows, "long"),
            },
            rows=band_rows,
        )
    return results


def predict_path_share(row: EuropeBarTruthRow, beta: list[float] | None) -> float:
    if not beta:
        return 0.0
    return clamp(sum(value * beta[i] for i, value in enumerate(simple_europe_regression_vector(row))), 0.0, 1.0)


def band_prediction_list(rows: list[EuropeBarTruthRow], band_models: dict[int, BandRegressionResult]) -> list[float]:
    out: list[float] = []
    for row in rows:
        model = band_models[row.band_m]
        predicted_loop2 = row.observation_count * predict_path_share(row, model.paths["short"].beta)
        predicted_loop3 = row.observation_count * predict_path_share(row, model.paths["long"].beta)
        out.append((predicted_loop2 - predicted_loop3) / row.observation_count if row.observation_count else 0.0)
    return out


def build_europe_regression_prediction_rows(
    rows: list[EuropeBarTruthRow],
    band_models: dict[int, BandRegressionResult],
    simple_pred: list[float],
    enhanced_pred: list[float],
) -> list[EuropeRegressionPredictionRow]:
    out: list[EuropeRegressionPredictionRow] = []
    for row, simple, enhanced in zip(rows, simple_pred, enhanced_pred):
        model = band_models[row.band_m]
        predicted_loop2 = row.observation_count * predict_path_share(row, model.paths["short"].beta)
        predicted_loop3 = row.observation_count * predict_path_share(row, model.paths["long"].beta)
        out.append(EuropeRegressionPredictionRow(
            date_utc=row.date_utc,
            utc_slot=row.utc_slot,
            slot_index=row.slot_index,
            band_m=row.band_m,
            loop2_count=row.loop2_count,
            loop3_count=row.loop3_count,
            observation_count=row.observation_count,
            observed_antenna_path_dominance_score=row.path_dominance_score,
            simple_model_path_dominance_score=simple,
            enhanced_model_path_dominance_score=enhanced,
            simple_residual=row.path_dominance_score - simple,
            enhanced_residual=row.path_dominance_score - enhanced,
            model_predicted_loop2_count=predicted_loop2,
            model_predicted_loop3_count=predicted_loop3,
        ))
    return out


def write_europe_regression_predictions_csv(rows: list[EuropeRegressionPredictionRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeRegressionPredictionRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dataclass_csv_row(row))
    write_table_html_report(rows, fieldnames, path.with_name(f"{path.stem}_table.html"), "Europe Regression Predictions")


def write_europe_regression_report(
    truth_rows: list[EuropeBarTruthRow],
    band_models: dict[int, BandRegressionResult],
    simple_pred: list[float],
    enhanced_beta: list[float],
    enhanced_pred: list[float],
    path: Path,
) -> None:
    y = [row.path_dominance_score for row in truth_rows]
    weights = [float(row.observation_count) for row in truth_rows]
    by_band = Counter(row.band_m for row in truth_rows)
    dates = sorted({row.date_utc for row in truth_rows})
    obs_by_band = Counter()
    for row in truth_rows:
        obs_by_band[row.band_m] += row.observation_count

    lines: list[str] = []
    lines.append("# Europe Bar-Truth Regression Report")
    lines.append("")
    lines.append(f"Generated: {generated_utc_label()}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This report focuses on the empirical truth shown in the side-by-side bar charts.")
    lines.append("Loop 2 at 330 degrees is treated as short-path evidence and Loop 3 at 150 degrees is treated as long-path evidence.")
    lines.append("")
    lines.append("The antenna observations are the validation evidence.")
    lines.append("More Loop 2 spots favour short-path evidence. More Loop 3 spots favour long-path evidence. Similar spot counts on both antennas mean the evidence is not dominant enough for validation.")
    lines.append("The model tries to reproduce that observed path direction using calculated path conditions. Good agreement means the model may be useful. Poor agreement means the model needs more work.")
    lines.append("")
    lines.append("## Dataset")
    lines.append("")
    lines.append(f"- Bar-truth rows: {len(truth_rows):,}")
    lines.append(f"- Dates: {', '.join(dates)}")
    lines.append(f"- Total Europe observations: {sum(row.observation_count for row in truth_rows):,}")
    for band in sorted(by_band):
        lines.append(f"- {band}m: {by_band[band]:,} UTC bins, {obs_by_band[band]:,} observations")
    lines.append("")
    lines.append("Rows are aggregated by date, band, and 30-minute UTC slot to match the bar-chart evidence.")
    lines.append("")
    lines.append("## Figure Of Merit")
    lines.append("")
    lines.append("R2 is the coefficient of determination. The weighted value gives larger spot-count bins more influence.")
    lines.append("The weighting is by number of decoded spots in the 30-minute bin only. SNR is not used, and no decoded spot is excluded for being weak.")
    lines.append("Unweighted R2 is also reported so reviewers can see how much the weighting changes the figure of merit.")
    lines.append("")
    lines.append("### Simple Interpretable Model")
    lines.append("")
    lines.append("- Features: dark-delta, greyline-delta, endpoint-twilight.")
    lines.append("- Coefficients are fitted independently for each band and each path.")
    lines.append("- Combined all-band or combined-path coefficient sets are not reported.")
    lines.append("")
    lines.append("### Enhanced Diagnostic Model")
    lines.append("")
    lines.append("- Features: simple model features plus band indicators, UTC harmonic terms, receiver sun altitude, and transmitter sun altitude.")
    lines.append(f"- Weighted R2: {format_review_r2(r2_score(y, enhanced_pred, weights))}")
    lines.append(f"- Unweighted R2: {format_review_r2(r2_score(y, enhanced_pred))}")
    lines.append("")
    lines.append("Important caution: this is an in-sample fit. A high R2 means the model can reproduce the known bar-chart truth for the supplied files; it is not yet proof of predictive performance on withheld dates.")
    lines.append("")
    lines.append("## Band And Path Simple Model Coefficients")
    lines.append("")
    for band in sorted(by_band):
        result = band_models[band]
        lines.append(f"### {band}m")
        for path_id, label in [("short", "Short-path model"), ("long", "Long-path model")]:
            path_result = result.paths[path_id]
            lines.append(f"#### {label}")
            if path_result.beta is None:
                lines.append(f"- Insufficient bins: {len(path_result.rows)}")
                continue
            lines.append(f"- Weighted R2: {format_review_r2(path_result.weighted_r2 or 0.0)}")
            lines.append(f"- Unweighted R2: {format_review_r2(path_result.unweighted_r2 or 0.0)}")
            for name, coef in zip(simple_europe_regression_names(), path_result.beta):
                lines.append(f"- `{name}`: {format_sig(coef)}")
        lines.append("")
    lines.append("## Enhanced Model Coefficients")
    for name, coef in zip(enhanced_europe_regression_names(), enhanced_beta):
        lines.append(f"- `{name}`: {format_sig(coef)}")
    lines.append("")
    lines.append("## Band And Path Simple Model Check")
    lines.append("")
    for band in sorted(by_band):
        band_rows = [row for row in truth_rows if row.band_m == band]
        lines.append(f"### {band}m")
        for path_id, label in [("short", "Short-path evidence"), ("long", "Long-path evidence")]:
            path_rows = path_training_rows(band_rows, path_id)
            if len(path_rows) < 2:
                lines.append(f"- {label}: insufficient bins ({len(path_rows)})")
                continue
            path_result = band_models[band].paths[path_id]
            pred_path = [row.observation_count * predict_path_share(row, path_result.beta) for row in path_rows]
            y_path = [row.loop2_count if path_id == "short" else row.loop3_count for row in path_rows]
            weights_path = [float(row.observation_count) for row in path_rows]
            spots_path = sum((row.loop2_count if path_id == "short" else row.loop3_count) for row in path_rows)
            lines.append(f"- {label}: {len(path_rows):,} bins, {spots_path:,} path spots, weighted R2 {format_review_r2(r2_score(y_path, pred_path, weights_path))}")
        lines.append("")
    lines.append("## Output Files")
    lines.append("")
    lines.append("- `europe_bar_truth.csv`")
    lines.append("- `europe_regression_predictions.csv`")
    lines.append("- `europe_regression_report.md`")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def slot_time_label(slot_index: int) -> str:
    return f"{slot_index // 2:02d}:{(slot_index % 2) * 30:02d}"


def describe_delta(value: float) -> str:
    if value >= 0.15:
        return "short path favoured"
    if value <= -0.15:
        return "long path favoured"
    return "balanced"


def aggregate_regression_visual_rows(
    truth_rows: list[EuropeBarTruthRow],
    prediction_rows: list[EuropeRegressionPredictionRow],
) -> dict[int, dict[int, dict[str, float]]]:
    grouped: dict[int, dict[int, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    prediction_by_key = {
        (row.date_utc, row.band_m, row.slot_index): row
        for row in prediction_rows
    }
    for row in truth_rows:
        pred = prediction_by_key[(row.date_utc, row.band_m, row.slot_index)]
        item = grouped[row.band_m][row.slot_index]
        item["loop2"] += row.loop2_count
        item["loop3"] += row.loop3_count
        item["observation_count"] += row.observation_count
        dominant_model = max(pred.model_predicted_loop2_count, pred.model_predicted_loop3_count)
        item["model_dominant"] += dominant_model
        item["model_short_dominant"] += pred.model_predicted_loop2_count
        item["model_long_dominant"] += pred.model_predicted_loop3_count
        item["dark_delta_sum"] += row.dark_delta * row.observation_count
        item["greyline_delta_sum"] += row.greyline_delta * row.observation_count
        item["endpoint_twilight_sum"] += row.endpoint_twilight_score * row.observation_count
        item["rx_sun_altitude_sum"] += row.rx_sun_altitude * row.observation_count
        item["tx_sun_altitude_sum"] += row.tx_sun_altitude * row.observation_count
        item["confidence"] = max(item["confidence"], float(empirical_bar_confidence_score(row)))

    for band_slots in grouped.values():
        for item in band_slots.values():
            total = item["observation_count"]
            if total <= 0:
                continue
            item["dark_delta"] = item["dark_delta_sum"] / total
            item["greyline_delta"] = item["greyline_delta_sum"] / total
            item["endpoint_twilight"] = item["endpoint_twilight_sum"] / total
            item["rx_sun_altitude"] = item["rx_sun_altitude_sum"] / total
            item["tx_sun_altitude"] = item["tx_sun_altitude_sum"] / total
            item["observed_path_dominance_score"] = (item["loop2"] - item["loop3"]) / total
            item["predicted_path_dominance_score"] = (
                item["model_short_dominant"] - item["model_long_dominant"]
            ) / total
    return grouped


def greyline_overlap_color(value: float) -> str:
    if value >= 0.25:
        return "#1d4f91"
    if value >= 0.15:
        return "#7eb6e8"
    return "#ffffff"


def reference_greyline_overlap(dt: datetime) -> float:
    rx_lat, rx_lon = maidenhead_to_latlon(RX_GRID)
    _sp_mean, _sp_dark, short_greyline = path_solar_features(
        rx_lat,
        rx_lon,
        EUROPE_REFERENCE_LAT,
        EUROPE_REFERENCE_LON,
        dt,
        False,
    )
    _lp_mean, _lp_dark, long_greyline = path_solar_features(
        rx_lat,
        rx_lon,
        EUROPE_REFERENCE_LAT,
        EUROPE_REFERENCE_LON,
        dt,
        True,
    )
    return min(short_greyline, long_greyline)


def endpoint_strip_color(value: float) -> str:
    if value >= 0.70:
        return "#2e7d32"
    if value >= 0.40:
        return "#8bc34a"
    if value >= 0.15:
        return "#cfe8b0"
    return "#edf2f7"


def confidence_strip_color(score: float) -> str:
    if score >= 3:
        return "#2e7d32"
    if score >= 2:
        return "#e3b505"
    if score >= 1:
        return "#d95f02"
    return "#eceff4"


def endpoint_illumination_color(sun_altitude: float) -> str:
    if sun_altitude < -6.0:
        return "#666666"
    if sun_altitude <= 6.0:
        return "#b8b8b8"
    return "#fff7d6"


def report_date_label(dates: list[str]) -> str:
    if not dates:
        return "selected dates"
    if len(dates) == 1:
        return dates[0]
    return f"{dates[0]} to {dates[-1]}"


def representative_slot_dt(dates: list[str], slot: int) -> datetime | None:
    if not dates:
        return None
    hour = slot // 2
    minute = 30 if slot % 2 else 0
    return datetime.strptime(dates[0], "%Y-%m-%d").replace(
        hour=hour,
        minute=minute,
        tzinfo=timezone.utc,
    )


def fmt_sig(value: float, digits: int = 3) -> str:
    text = f"{value:.{digits}g}"
    if "e" in text or "E" in text:
        return text
    return text


def theory_dominance_class(value: float) -> str:
    if value >= 0.15:
        return "model-short"
    if value <= -0.15:
        return "model-long"
    return "model-neutral"


def format_review_r2(value: float) -> str:
    return f"{max(0.0, value):.2f}"


def svg_regression_story_chart(
    band_m: int,
    slots: dict[int, dict[str, float]],
    band_beta: list[float],
    dates: list[str],
) -> str:
    width = 1320
    height = 530
    left = 172
    right = 24
    top = 36
    plot_h = 250
    timeline_h = 18
    timeline_gap = 10
    bottom = 44
    plot_w = width - left - right
    slot_w = plot_w / 48
    bar_w = max(2.0, slot_w * 0.16)
    max_value = 1.0
    for item in slots.values():
        max_value = max(
            max_value,
            item["loop2"],
            item["loop3"],
            item["model_dominant"],
        )

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{band_m}m regression visual story">',
        f'<text x="{left}" y="22" class="chart-title">{band_m}m observed loop evidence versus simple regression model for {html.escape(report_date_label(dates))}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>',
        f'<text x="8" y="{top + 14}" class="axis-label">spots</text>',
    ]
    tick_step = max(1, int(math.ceil(max_value / 4)))
    for tick in range(0, int(math.ceil(max_value)) + 1, tick_step):
        y = top + plot_h - (tick / max_value) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" class="tick">{tick}</text>')

    for slot in range(48):
        item = slots.get(slot, {})
        x = left + slot * slot_w
        model_is_short = item.get("predicted_path_dominance_score", 0.0) >= 0.0
        values = [
            ("obs-short", item.get("loop2", 0.0), "Loop 2", "short-path", False),
            (
                theory_dominance_class(item.get("predicted_path_dominance_score", 0.0)),
                item.get("model_dominant", 0.0),
                "model",
                "short-path" if model_is_short else "long-path",
                True,
            ),
            ("obs-long", item.get("loop3", 0.0), "Loop 3", "long-path", False),
        ]
        for offset, (klass, value, source, path_label, is_model) in enumerate(values):
            h = (value / max_value) * plot_h
            spot_label = str(round(value)) if is_model else fmt_sig(value)
            parts.append(
                f'<rect x="{x + slot_w * 0.18 + offset * bar_w * 1.26:.2f}" '
                f'y="{top + plot_h - h:.2f}" width="{bar_w:.2f}" height="{h:.2f}" class="{klass}">'
                f'<title>{slot_time_label(slot)}, {source}, {path_label}, {spot_label} spots</title></rect>'
            )
        if slot % 2 == 0:
            parts.append(f'<text x="{x + slot_w / 2:.2f}" y="{top + plot_h + 18}" text-anchor="middle" class="tick">{slot // 2:02d}</text>')

    timeline_y = top + plot_h + 86
    timeline_specs = [
        ("Dominance confidence", "confidence", confidence_strip_color),
        ("Receiver Brisbane", "rx_sun_altitude", endpoint_illumination_color),
        ("Beacon Europe", "tx_sun_altitude", endpoint_illumination_color),
        ("Path grey-line overlap", "greyline_overlap", greyline_overlap_color),
    ]
    for line_no, (label, key, color_fn) in enumerate(timeline_specs):
        y = timeline_y + line_no * (timeline_h + timeline_gap)
        parts.append(f'<text x="{left - 8}" y="{y + 13}" text-anchor="end" class="strip-label">{html.escape(label)}</text>')
        for slot in range(48):
            item = slots.get(slot)
            if key == "rx_sun_altitude":
                dt = representative_slot_dt(dates, slot)
                color_value = solar_altitude_deg(*maidenhead_to_latlon(RX_GRID), dt) if dt else 0.0
                color = color_fn(float(color_value))
                title = f"{slot_time_label(slot)} UTC, receiver solar altitude {color_value:.1f} deg"
            elif key == "tx_sun_altitude":
                dt = representative_slot_dt(dates, slot)
                color_value = solar_altitude_deg(EUROPE_REFERENCE_LAT, EUROPE_REFERENCE_LON, dt) if dt else 0.0
                color = color_fn(float(color_value))
                title = f"{slot_time_label(slot)} UTC, Europe reference solar altitude {color_value:.1f} deg"
            elif key == "greyline_overlap":
                dt = representative_slot_dt(dates, slot)
                color_value = reference_greyline_overlap(dt) if dt else 0.0
                color = color_fn(float(color_value))
                title = f"{slot_time_label(slot)} UTC, {label}: {fmt_sig(color_value)}"
            elif not item:
                color = "#f5f7fa" if key != "greyline_overlap" else "#ffffff"
                title = f"{slot_time_label(slot)} UTC, no Europe observations in this bin"
            else:
                color_value = float(item.get(key, 0.0))
                color = color_fn(color_value)
                if key == "confidence":
                    title = f"{slot_time_label(slot)}, Confidence {round(color_value)}"
                else:
                    title = f"{slot_time_label(slot)} UTC, {label}: {fmt_sig(color_value)}"
            x = left + slot * slot_w
            parts.append(
                f'<rect x="{x:.2f}" y="{y}" width="{slot_w + 0.2:.2f}" height="{timeline_h}" fill="{color}">'
                f'<title>{html.escape(title)}</title></rect>'
            )

    parts.append(f'<text x="{left + plot_w / 2:.2f}" y="{top + plot_h + 34}" text-anchor="middle" class="axis-label">UTC</text>')
    parts.append(
        f'<text x="{left}" y="{timeline_y - 14}" class="equation">'
        f'The model calculates path conditions with attempt to reproduce the observed antenna direction.</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def write_europe_regression_visual_report_html(
    truth_rows: list[EuropeBarTruthRow],
    band_models: dict[int, BandRegressionResult],
    prediction_rows: list[EuropeRegressionPredictionRow],
    path: Path,
) -> None:
    grouped = aggregate_regression_visual_rows(truth_rows, prediction_rows)
    dates = sorted({row.date_utc for row in truth_rows})
    y = [row.path_dominance_score for row in truth_rows]
    weights = [float(row.observation_count) for row in truth_rows]
    sections = []
    for band in [40, 30, 20]:
        if band not in grouped:
            continue
        band_rows = [row for row in truth_rows if row.band_m == band]
        short_beta = band_models[band].paths["short"].beta
        long_beta = band_models[band].paths["long"].beta

        def path_r2_summary(path_id: str) -> tuple[str, int, int]:
            items = path_training_rows(band_rows, path_id)
            spots_path = sum((row.loop2_count if path_id == "short" else row.loop3_count) for row in items)
            if len(items) < 2:
                return "-", len(items), spots_path
            beta = band_models[band].paths[path_id].beta
            y_path = [row.loop2_count if path_id == "short" else row.loop3_count for row in items]
            pred_path = [row.observation_count * predict_path_share(row, beta) for row in items]
            weights_path = [float(row.observation_count) for row in items]
            return format_review_r2(r2_score(y_path, pred_path, weights_path)), len(items), spots_path

        short_r2, short_bins, short_spots = path_r2_summary("short")
        long_r2, long_bins, long_spots = path_r2_summary("long")
        sections.append(f"<section><h2>{band}m Band</h2>")
        sections.append(
            "<table><thead><tr><th>Evidence set</th><th>Bins</th><th>Spots</th><th>Weighted R2</th></tr></thead><tbody>"
            f"<tr><td>Short-path evidence</td><td>{short_bins:,}</td><td>{short_spots:,}</td><td>{short_r2}</td></tr>"
            f"<tr><td>Long-path evidence</td><td>{long_bins:,}</td><td>{long_spots:,}</td><td>{long_r2}</td></tr>"
            "</tbody></table>"
        )
        for label, beta in [("Short-path coefficients", short_beta), ("Long-path coefficients", long_beta)]:
            if beta is None:
                sections.append(f"<p><strong>{label}:</strong> insufficient path bins.</p>")
            else:
                sections.append(
                    f"<p><strong>{label}:</strong> "
                    + ", ".join(
                        f"{html.escape(name)} {format_sig(coef)}"
                        for name, coef in zip(simple_europe_regression_names(), beta)
                    )
                    + ".</p>"
                )
        sections.append(svg_regression_story_chart(band, grouped[band], [], dates))
        sections.append("</section>")

    example = ""


    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Europe Regression Visual Report</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; color: #202124; background: #fff; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 32px; border-top: 1px solid #d5dbe3; padding-top: 18px; }}
  p, li {{ line-height: 1.45; max-width: 980px; }}
  svg {{ width: 100%; max-width: 1320px; height: auto; display: block; margin: 14px 0 10px; }}
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; max-width: 980px; }}
  .panel {{ border: 1px solid #d8dee8; border-radius: 6px; padding: 12px 14px; background: #fafbfc; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 16px; margin: 18px 0; align-items: center; }}
  .key {{ display: inline-block; width: 18px; height: 12px; margin-right: 6px; vertical-align: middle; }}
  .obs-short, .key.obs-short-key {{ fill: #1f77b4; background: #1f77b4; }}
  .obs-long, .key.obs-long-key {{ fill: #ff7f0e; background: #ff7f0e; }}
  .model-short, .key.model-short-key {{ fill: #9ecae1; background: #9ecae1; }}
  .model-long, .key.model-long-key {{ fill: #fdd0a2; background: #fdd0a2; }}
  .model-neutral, .key.model-neutral-key {{ fill: #cfd6df; background: #cfd6df; }}
  .axis {{ stroke: #333; stroke-width: 1; }}
  .grid {{ stroke: #dfe3e8; stroke-width: 1; }}
  .tick {{ fill: #4a5568; font-size: 10px; }}
  .axis-label, .strip-label {{ fill: #3b4652; font-size: 12px; }}
  .chart-title {{ fill: #1d2733; font-weight: 700; font-size: 14px; }}
  .equation {{ fill: #1d2733; font-size: 13px; font-weight: 700; }}
  .example {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #f6f8fa; border: 1px solid #d8dee8; border-radius: 6px; padding: 12px; max-width: 980px; overflow-x: auto; }}
</style>
</head>
<body>
<h1>Europe Regression Visual Report</h1>
<p>Generated: {generated_utc_label()}</p>
<p>Dates: {html.escape(', '.join(dates))}</p>
<p>End-points: Brisbane &lt;&gt; Frankfurt reference path.</p>
<div class="summary">
  <div class="panel"><strong>Purpose</strong><br>Show how the simple regression model follows empirical Loop 2 and Loop 3 observations.</div>
  <div class="panel"><strong>Model</strong><br>Calculated path conditions are fitted to antenna evidence.</div>
</div>
<h2>How To Read This Report</h2>
<ul>
  <li>Dark blue bars are observed Loop 2 spots, treated as short-path evidence.</li>
  <li>Orange bars are observed Loop 3 spots, treated as long-path evidence.</li>
  <li>The single model bar estimates the dominant path only. Light blue favours short path, light orange favours long path, and grey means no clear spot count.</li>
  <li>The sandwich strips show dominance confidence, receiver light/dark, beacon-area light/dark, and path grey-line overlap.</li>
  <li>Each coloured sandwich square represents one 30-minute UTC bin. Blank squares mean no data or no clear condition in that bin.</li>
</ul>
<p>The antenna data is the observed evidence. The model tries to reproduce that evidence using calculated path conditions. Good agreement means the model may be useful. Poor agreement means the model needs more work.</p>
<div class="legend">
  <span><span class="key obs-short-key"></span>Observed Loop 2 / short</span>
  <span><span class="key obs-long-key"></span>Observed Loop 3 / long</span>
  <span><span class="key model-short-key"></span>Model dominant short</span>
  <span><span class="key model-long-key"></span>Model dominant long</span>
  <span><span class="key model-neutral-key"></span>No clear spot count</span>
</div>
{''.join(sections)}
<h2>Sandwich Colour Guide</h2>
<ul>
  <li>Dominance confidence: green is high, yellow is medium, orange is low, light grey is no clear evidence. This row is based on antenna dominance and spot count for each 30-minute bin.</li>
  <li>Receiver and beacon rows: medium grey is night, light grey is twilight, light cream is daylight. Blank beacon squares mean no Europe observations in that bin.</li>
  <li>Path grey-line overlap: blue highlights time periods when sampled grey-line support overlaps along the reference path. White means no meaningful overlap in that 30-minute bin.</li>
</ul>
{example}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def write_export_manifest(
    out_dir: Path,
    truth_rows: list[EuropeBarTruthRow],
    feature_rows: list[FeatureRow],
    prediction_rows: list[EuropeRegressionPredictionRow],
) -> None:
    dates = sorted({row.date_utc for row in truth_rows})
    bands = sorted({row.band_m for row in truth_rows}, reverse=True)
    lines = [
        "# Long-Path Export Manifest",
        "",
        f"Generated: {generated_utc_label()}",
        f"Dates: {', '.join(dates) if dates else 'none'}",
        f"Bands: {', '.join(str(band) + 'm' for band in bands) if bands else 'none'}",
        "",
        "## Current Reviewer Files",
        "",
        "- `reviewer_package/visual_report.html`: visual reviewer report with band/path R2, charts, and sandwich strips.",
        "- `reviewer_package/project_about.md`: project explanation and Q&A.",
        "- `reviewer_package/report_index.html`: simple landing page linking the reviewer files and data files.",
        "",
        "## Data Files",
        "",
        f"- `wspr_path_features.csv`: Europe-only calculated feature rows, {len(feature_rows):,} rows.",
        "- `wspr_path_features_table.html`: human-readable feature table with sticky headings.",
        f"- `europe_bar_truth.csv`: Europe observed loop evidence aggregated by date, band, and UTC slot, {len(truth_rows):,} rows.",
        "- `europe_bar_truth_table.html`: human-readable bar-truth table with sticky headings.",
        f"- `europe_regression_predictions.csv`: simple and enhanced model prediction rows, {len(prediction_rows):,} rows.",
        "- `europe_regression_predictions_table.html`: human-readable prediction table with sticky headings.",
        "",
        "## Important Terms",
        "",
        "- `path_dominance_score = (Loop2_count - Loop3_count) / (Loop2_count + Loop3_count)`.",
        "- `simple_model_path_dominance_score`: prediction from the simple transparent model.",
        "- `enhanced_model_path_dominance_score`: diagnostic regression score using extra terms such as band indicators, UTC harmonics, receiver sun altitude, and transmitter sun altitude.",
        "- R2 is reviewed separately by band and path. A blended R2 made by merging short-path and long-path evidence is not used.",
    ]
    (out_dir / "export_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reviewer_package_index_html(out_dir: Path) -> None:
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Long-Path Reviewer Package</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #17202a; line-height: 1.45; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 24px; border-top: 1px solid #d7dde5; padding-top: 14px; }}
  li {{ margin: 6px 0; }}
  code {{ background: #f2f4f7; padding: 1px 4px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Long-Path Reviewer Package</h1>
<p>Generated {html.escape(generated_utc_label())}.</p>
<h2>Start Here</h2>
<ul>
  <li><a href="visual_report.html">visual_report.html</a>: visual report, charts, sandwich strips, and band/path R2.</li>
  <li><a href="project_about.md">project_about.md</a>: project explanation and Q&A.</li>
  <li><a href="../export_manifest.md">export_manifest.md</a>: file list and data definitions.</li>
</ul>
<h2>Data Tables</h2>
<ul>
  <li><a href="../europe_bar_truth_table.html">europe_bar_truth_table.html</a> and <a href="../europe_bar_truth.csv">europe_bar_truth.csv</a></li>
  <li><a href="../europe_regression_predictions_table.html">europe_regression_predictions_table.html</a> and <a href="../europe_regression_predictions.csv">europe_regression_predictions.csv</a></li>
  <li><a href="../wspr_path_features_table.html">wspr_path_features_table.html</a> and <a href="../wspr_path_features.csv">wspr_path_features.csv</a></li>
</ul>
<h2>Review Principle</h2>
<p>Short-path evidence and long-path evidence are reviewed separately. A blended R2 made by merging both paths is not used.</p>
</body>
</html>
"""
    (out_dir / "reviewer_package" / "report_index.html").write_text(doc, encoding="utf-8")


def filter_training_rows(rows: list[FeatureRow]) -> list[FeatureRow]:
    # Keep usable non-unknown rows for legacy diagnostic helpers.
    return [r for r in rows if r.observation_count > 0 and r.continent not in {"Unknown"}]


def write_report(rows: list[FeatureRow], path: Path) -> None:
    train_rows = filter_training_rows(rows)
    names, x, y, weights = model_matrix(train_rows)
    beta_unweighted = fit_wls(x, y)
    pred_unweighted = predict(x, beta_unweighted)
    beta_weighted = fit_wls(x, y, weights)
    pred_weighted = predict(x, beta_weighted)

    by_date = Counter(r.date_utc for r in rows)
    by_band = Counter(r.band_m for r in rows)
    by_cont = Counter(r.continent for r in rows)
    obs_by_band = Counter()
    obs_by_cont = Counter()
    for r in rows:
        obs_by_band[r.band_m] += r.observation_count
        obs_by_cont[r.continent] += r.observation_count

    lines: list[str] = []
    lines.append("# WSPR Path Research Baseline Report")
    lines.append("")
    lines.append("## Dataset")
    lines.append(f"- Feature rows: {len(rows):,}")
    lines.append(f"- Model rows: {len(train_rows):,}")
    lines.append(f"- Raw loop observations represented: {sum(r.observation_count for r in rows):,}")
    lines.append(f"- Dates: {', '.join(sorted(by_date))}")
    lines.append("")
    lines.append("Rows are 30-minute UTC bins by date, band, continent, country, and transmitter grid.")
    lines.append("No low-count bins are excluded from the feature output.")
    lines.append("")
    lines.append("## Row Counts By Band")
    for band in sorted(by_band):
        lines.append(f"- {band}m: {by_band[band]:,} feature rows, {obs_by_band[band]:,} observations")
    lines.append("")
    lines.append("## Row Counts By Continent")
    for cont, count in by_cont.most_common():
        lines.append(f"- {cont}: {count:,} feature rows, {obs_by_cont[cont]:,} observations")
    lines.append("")
    lines.append("## Target")
    lines.append("")
    lines.append("The antenna observations are the validation evidence.")
    lines.append("More Loop 2 spots favour short-path evidence. More Loop 3 spots favour long-path evidence. Similar counts are balanced.")
    lines.append("")
    lines.append("## Baseline Linear Regression")
    lines.append("")
    lines.append(f"- Unweighted R^2: {r2_score(y, pred_unweighted):.4f}")
    lines.append(f"- Observation-weighted R^2: {r2_score(y, pred_weighted, weights):.4f}")
    lines.append("")
    lines.append("The weighted fit keeps every row but gives larger bins proportionally more influence.")
    lines.append("This is a first diagnostic model, not a production classifier.")
    lines.append("")
    lines.append("## Weighted Coefficients")
    for name, coef in sorted(zip(names, beta_weighted), key=lambda item: abs(item[1]), reverse=True):
        lines.append(f"- `{name}`: {coef:.4f}")
    lines.append("")
    lines.append("## Next Checks")
    lines.append("")
    lines.append("- Compare predicted direction score against the bar-chart truth by band and continent.")
    lines.append("- Run leave-one-date-out validation once the first plots are acceptable.")
    lines.append("- Inspect collinearity between solar path fractions and grey-line fractions.")
    lines.append("- Decide whether country/grid rows should be rolled up to continent-level for the first app-facing model.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def greyline_altitude_score(altitude_deg: float, width_deg: float = 12.0) -> float:
    """Broad endpoint grey-line score: 1 at horizon, 0 outside +/- width_deg."""
    return max(0.0, 1.0 - abs(altitude_deg) / width_deg)


def weighted_average(values: list[tuple[float, int]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in values) / total_weight


def build_europe_theory_rows(rows: list[FeatureRow]) -> list[EuropeTheoryRow]:
    grouped: dict[tuple[str, str, int, int, str], list[FeatureRow]] = defaultdict(list)
    for row in rows:
        if row.continent != "Europe":
            continue
        key = (row.date_utc, row.utc_slot, row.slot_index, row.band_m, eu_grid_cluster(row.tx_grid))
        grouped[key].append(row)

    out: list[EuropeTheoryRow] = []
    for key, group in sorted(grouped.items()):
        date_utc, utc_slot, slot_index, band_m, grid_cluster = key
        loop2 = sum(row.loop2_count for row in group)
        loop3 = sum(row.loop3_count for row in group)
        total = loop2 + loop3
        if total <= 0:
            continue

        rx_score = weighted_average([
            (greyline_altitude_score(row.rx_sun_altitude), row.observation_count)
            for row in group
        ])
        tx_score = weighted_average([
            (greyline_altitude_score(row.tx_sun_altitude), row.observation_count)
            for row in group
        ])
        endpoint_overlap = min(rx_score, tx_score)
        short_fraction = weighted_average([
            (row.short_path_greyline_fraction, row.observation_count)
            for row in group
        ])
        long_fraction = weighted_average([
            (row.long_path_greyline_fraction, row.observation_count)
            for row in group
        ])

        # Theory v1 deliberately stays primitive: path grey-line fraction is the
        # primary term, endpoint overlap is a small common boost when both ends
        # are near the broad grey-line band.
        short_score = short_fraction + 0.25 * endpoint_overlap
        long_score = long_fraction + 0.25 * endpoint_overlap
        score_total = short_score + long_score
        if score_total > 0:
            theory_short = total * short_score / score_total
            theory_long = total * long_score / score_total
        else:
            theory_short = 0.0
            theory_long = 0.0

        out.append(EuropeTheoryRow(
            date_utc=date_utc,
            month_utc=date_utc[:7],
            utc_slot=utc_slot,
            slot_index=slot_index,
            band_m=band_m,
            eu_grid_cluster=grid_cluster,
            observed_short_path_spots=loop2,
            observed_long_path_spots=loop3,
            observation_count=total,
            rx_greyline_score=rx_score,
            tx_greyline_score=tx_score,
            endpoint_overlap_score=endpoint_overlap,
            short_path_greyline_fraction=short_fraction,
            long_path_greyline_fraction=long_fraction,
            theory_short_score=short_score,
            theory_long_score=long_score,
            theory_short_path_spots=theory_short,
            theory_long_path_spots=theory_long,
            theory_margin=theory_short - theory_long,
            observed_margin=loop2 - loop3,
        ))
    return out


def write_europe_theory_csv(rows: list[EuropeTheoryRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeTheoryRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            for key, value in data.items():
                if isinstance(value, float):
                    data[key] = f"{value:.6f}"
            writer.writerow(data)


def build_europe_chart_rows(theory_rows: list[EuropeTheoryRow]) -> list[EuropeChartRow]:
    grouped: dict[tuple[str, int, str, int], list[EuropeTheoryRow]] = defaultdict(list)
    for row in theory_rows:
        grouped[("all", row.band_m, row.utc_slot, row.slot_index)].append(row)
        grouped[(row.month_utc, row.band_m, row.utc_slot, row.slot_index)].append(row)

    out: list[EuropeChartRow] = []
    for key, group in sorted(grouped.items()):
        month_utc, band_m, utc_slot, slot_index = key
        observed_short = sum(row.observed_short_path_spots for row in group)
        observed_long = sum(row.observed_long_path_spots for row in group)
        theory_short = sum(row.theory_short_path_spots for row in group)
        theory_long = sum(row.theory_long_path_spots for row in group)
        out.append(EuropeChartRow(
            month_utc=month_utc,
            band_m=band_m,
            utc_slot=utc_slot,
            slot_index=slot_index,
            observed_short_path_spots=observed_short,
            observed_long_path_spots=observed_long,
            theory_short_path_spots=theory_short,
            theory_long_path_spots=theory_long,
            observed_margin=observed_short - observed_long,
            theory_margin=theory_short - theory_long,
        ))
    return out


def write_europe_chart_csv(rows: list[EuropeChartRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeChartRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            for key in ["theory_short_path_spots", "theory_long_path_spots", "theory_margin"]:
                data[key] = f"{data[key]:.6f}"
            writer.writerow(data)


def chart_slot_label(slot_index: int) -> str:
    return f"{slot_index // 2:02d}:{(slot_index % 2) * 30:02d}"


def svg_bar_chart(
    rows: list[EuropeChartRow],
    band_m: int,
    path_label: str,
    observed_attr: str,
    theory_attr: str,
    date_label: str,
) -> str:
    by_slot = {row.slot_index: row for row in rows if row.month_utc == "all" and row.band_m == band_m}
    values = []
    for slot in range(48):
        row = by_slot.get(slot)
        values.append(float(getattr(row, observed_attr)) if row else 0.0)
        values.append(float(getattr(row, theory_attr)) if row else 0.0)
    max_value = max(values) if values else 0.0
    max_value = max(1.0, max_value)

    width = 1180
    height = 280
    left = 54
    right = 18
    top = 24
    bottom = 44
    plot_w = width - left - right
    plot_h = height - top - bottom
    slot_w = plot_w / 48
    bar_w = max(2.0, slot_w * 0.36)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{band_m}m {html.escape(path_label)} chart">',
        f'<text x="{left}" y="16" class="chart-title">{band_m}m {html.escape(path_label)}</text>',
        f'<text x="{left + 370}" y="16" class="chart-subtitle">{html.escape(date_label)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>',
        f'<text x="6" y="{top + 12}" class="axis-label">spots</text>',
    ]
    for tick in range(0, int(math.ceil(max_value)) + 1, max(1, int(math.ceil(max_value / 4)))):
        y = top + plot_h - (tick / max_value) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" class="tick">{tick}</text>')

    for slot in range(48):
        row = by_slot.get(slot)
        observed = float(getattr(row, observed_attr)) if row else 0.0
        theory = float(getattr(row, theory_attr)) if row else 0.0
        x = left + slot * slot_w
        observed_h = (observed / max_value) * plot_h
        theory_h = (theory / max_value) * plot_h
        parts.append(
            f'<rect x="{x + slot_w * 0.13:.2f}" y="{top + plot_h - observed_h:.2f}" '
            f'width="{bar_w:.2f}" height="{observed_h:.2f}" class="observed"/>'
        )
        parts.append(
            f'<rect x="{x + slot_w * 0.51:.2f}" y="{top + plot_h - theory_h:.2f}" '
            f'width="{bar_w:.2f}" height="{theory_h:.2f}" class="theory"/>'
        )
        if slot % 2 == 0:
            parts.append(f'<text x="{x + slot_w / 2:.2f}" y="{height - 20}" text-anchor="middle" class="tick">{slot // 2:02d}</text>')
    parts.append(f'<text x="{left + plot_w / 2:.2f}" y="{height - 4}" text-anchor="middle" class="axis-label">UTC hour</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_europe_chart_html(rows: list[EuropeChartRow], path: Path, date_label: str) -> None:
    bands = sorted({row.band_m for row in rows})
    sections: list[str] = []
    for band in bands:
        sections.append(f"<section><h2>{band}m</h2>")
        sections.append(svg_bar_chart(
            rows,
            band,
            "Short path: observed Loop 2 vs theory v1",
            "observed_short_path_spots",
            "theory_short_path_spots",
            date_label,
        ))
        sections.append(svg_bar_chart(
            rows,
            band,
            "Long path: observed Loop 3 vs theory v1",
            "observed_long_path_spots",
            "theory_long_path_spots",
            date_label,
        ))
        sections.append("</section>")

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Europe Theory V1 Charts</title>
<style>
  body {{
    font-family: Arial, sans-serif;
    margin: 24px;
    color: #202124;
    background: #fff;
  }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 32px; border-top: 1px solid #ddd; padding-top: 18px; }}
  p {{ color: #555; max-width: 900px; line-height: 1.5; }}
  svg {{ width: 100%; max-width: 1180px; height: auto; display: block; margin: 12px 0 24px; }}
  .observed {{ fill: #2ca25f; }}
  .theory {{ fill: #e78ac3; }}
  .axis {{ stroke: #333; stroke-width: 1; }}
  .grid {{ stroke: #ddd; stroke-width: 1; }}
  .tick {{ fill: #555; font-size: 10px; }}
  .axis-label {{ fill: #444; font-size: 12px; }}
  .chart-title {{ fill: #222; font-weight: 700; font-size: 14px; }}
  .chart-subtitle {{ fill: #666; font-size: 12px; }}
  .legend {{ display: flex; gap: 18px; margin: 18px 0; align-items: center; }}
  .key {{ display: inline-block; width: 18px; height: 12px; margin-right: 6px; vertical-align: middle; }}
  .key.observed-key {{ background: #2ca25f; }}
  .key.theory-key {{ background: #e78ac3; }}
</style>
</head>
<body>
<h1>Europe Theory V1 Charts</h1>
<p>Observed bars use the fixed-loop validation data. Theory bars use the primitive grey-line diagnostic from <code>europe_theory_v1_greyline.csv</code>. These charts are for comparison and criticism, not final classification.</p>
<div class="legend">
  <span><span class="key observed-key"></span>Observed spots</span>
  <span><span class="key theory-key"></span>Theory v1 spots</span>
</div>
{''.join(sections)}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def australian_dusk_score(rx_sun_altitude: float) -> float:
    """Receiver-side dusk illumination score for Australian East Coast long-path review.

    The window is intentionally broad for this early theory cut:
    - 0 above +35 deg sun altitude
    - ramps to full strength by +15 deg
    - remains strong through sunset
    - fades out by -12 deg
    """
    alt = rx_sun_altitude
    if alt >= 35.0 or alt <= -12.0:
        return 0.0
    if alt >= 15.0:
        return (35.0 - alt) / 20.0
    if alt >= -3.0:
        return 1.0
    return (alt + 12.0) / 9.0


def build_europe_dusk_theory_rows(rows: list[FeatureRow]) -> list[EuropeDuskTheoryRow]:
    grouped: dict[tuple[str, str, int, int, str], list[FeatureRow]] = defaultdict(list)
    for row in rows:
        if row.continent != "Europe":
            continue
        key = (row.date_utc, row.utc_slot, row.slot_index, row.band_m, eu_grid_cluster(row.tx_grid))
        grouped[key].append(row)

    prelim: list[dict[str, object]] = []
    score_totals: Counter[tuple[str, int]] = Counter()
    observed_long_totals: Counter[tuple[str, int]] = Counter()
    for key, group in sorted(grouped.items()):
        date_utc, utc_slot, slot_index, band_m, grid_cluster = key
        observed_long = sum(row.loop3_count for row in group)
        total = sum(row.observation_count for row in group)
        if total <= 0:
            continue
        rx_alt = weighted_average([(row.rx_sun_altitude, row.observation_count) for row in group])
        long_fraction = weighted_average([(row.long_path_greyline_fraction, row.observation_count) for row in group])
        dusk = australian_dusk_score(rx_alt)
        raw_score = dusk * (0.5 + long_fraction)
        prelim.append({
            "date_utc": date_utc,
            "month_utc": date_utc[:7],
            "utc_slot": utc_slot,
            "slot_index": slot_index,
            "band_m": band_m,
            "eu_grid_cluster": grid_cluster,
            "observed_long_path_spots": observed_long,
            "observation_count": total,
            "rx_sun_altitude": rx_alt,
            "australian_dusk_score": dusk,
            "long_path_greyline_fraction": long_fraction,
            "theory_raw_score": raw_score,
        })
        scale_key = (date_utc, band_m)
        score_totals[scale_key] += raw_score
        observed_long_totals[scale_key] += observed_long

    out: list[EuropeDuskTheoryRow] = []
    for item in prelim:
        scale_key = (str(item["date_utc"]), int(item["band_m"]))
        raw_score = float(item["theory_raw_score"])
        score_total = score_totals[scale_key]
        observed_total = observed_long_totals[scale_key]
        theory_long = observed_total * raw_score / score_total if score_total > 0 else 0.0
        out.append(EuropeDuskTheoryRow(
            date_utc=str(item["date_utc"]),
            month_utc=str(item["month_utc"]),
            utc_slot=str(item["utc_slot"]),
            slot_index=int(item["slot_index"]),
            band_m=int(item["band_m"]),
            eu_grid_cluster=str(item["eu_grid_cluster"]),
            observed_long_path_spots=int(item["observed_long_path_spots"]),
            observation_count=int(item["observation_count"]),
            rx_sun_altitude=float(item["rx_sun_altitude"]),
            australian_dusk_score=float(item["australian_dusk_score"]),
            long_path_greyline_fraction=float(item["long_path_greyline_fraction"]),
            theory_raw_score=raw_score,
            theory_long_path_spots=theory_long,
        ))
    return out


def write_europe_dusk_theory_csv(rows: list[EuropeDuskTheoryRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeDuskTheoryRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            for key, value in data.items():
                if isinstance(value, float):
                    data[key] = f"{value:.6f}"
            writer.writerow(data)


def build_europe_dusk_chart_rows(rows: list[EuropeDuskTheoryRow]) -> list[EuropeDuskChartRow]:
    grouped: dict[tuple[str, int, str, int], list[EuropeDuskTheoryRow]] = defaultdict(list)
    for row in rows:
        grouped[("all", row.band_m, row.utc_slot, row.slot_index)].append(row)
        grouped[(row.month_utc, row.band_m, row.utc_slot, row.slot_index)].append(row)

    out: list[EuropeDuskChartRow] = []
    for key, group in sorted(grouped.items()):
        month_utc, band_m, utc_slot, slot_index = key
        out.append(EuropeDuskChartRow(
            month_utc=month_utc,
            band_m=band_m,
            utc_slot=utc_slot,
            slot_index=slot_index,
            observed_long_path_spots=sum(row.observed_long_path_spots for row in group),
            theory_long_path_spots=sum(row.theory_long_path_spots for row in group),
        ))
    return out


def write_europe_dusk_chart_csv(rows: list[EuropeDuskChartRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeDuskChartRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            data["theory_long_path_spots"] = f"{row.theory_long_path_spots:.6f}"
            writer.writerow(data)


def svg_dusk_bar_chart(rows: list[EuropeDuskChartRow], band_m: int, date_label: str, month_utc: str = "all") -> str:
    by_slot = {row.slot_index: row for row in rows if row.month_utc == month_utc and row.band_m == band_m}
    values = []
    for slot in range(48):
        row = by_slot.get(slot)
        values.append(float(row.observed_long_path_spots) if row else 0.0)
        values.append(float(row.theory_long_path_spots) if row else 0.0)
    max_value = max(1.0, max(values) if values else 0.0)

    width = 1180
    height = 280
    left = 54
    right = 18
    top = 24
    bottom = 44
    plot_w = width - left - right
    plot_h = height - top - bottom
    slot_w = plot_w / 48
    bar_w = max(2.0, slot_w * 0.36)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{band_m}m long path dusk theory chart">',
        f'<text x="{left}" y="16" class="chart-title">{band_m}m Long path: observed Loop 3 vs theory v2 dusk</text>',
        f'<text x="{left + 440}" y="16" class="chart-subtitle">{html.escape(date_label)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>',
        f'<text x="6" y="{top + 12}" class="axis-label">spots</text>',
    ]
    for tick in range(0, int(math.ceil(max_value)) + 1, max(1, int(math.ceil(max_value / 4)))):
        y = top + plot_h - (tick / max_value) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" class="tick">{tick}</text>')
    for slot in range(48):
        row = by_slot.get(slot)
        observed = float(row.observed_long_path_spots) if row else 0.0
        theory = float(row.theory_long_path_spots) if row else 0.0
        x = left + slot * slot_w
        observed_h = (observed / max_value) * plot_h
        theory_h = (theory / max_value) * plot_h
        parts.append(f'<rect x="{x + slot_w * 0.13:.2f}" y="{top + plot_h - observed_h:.2f}" width="{bar_w:.2f}" height="{observed_h:.2f}" class="observed"/>')
        parts.append(f'<rect x="{x + slot_w * 0.51:.2f}" y="{top + plot_h - theory_h:.2f}" width="{bar_w:.2f}" height="{theory_h:.2f}" class="theory"/>')
        if slot % 2 == 0:
            parts.append(f'<text x="{x + slot_w / 2:.2f}" y="{height - 20}" text-anchor="middle" class="tick">{slot // 2:02d}</text>')
    parts.append(f'<text x="{left + plot_w / 2:.2f}" y="{height - 4}" text-anchor="middle" class="axis-label">UTC hour</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_europe_dusk_chart_html(rows: list[EuropeDuskChartRow], path: Path, date_label: str) -> None:
    bands = sorted({row.band_m for row in rows})
    sections = []
    for band in bands:
        heading = "30m focus band" if band == 30 else f"{band}m reference"
        sections.append(f"<section><h2>{heading}</h2>")
        sections.append(svg_dusk_bar_chart(rows, band, date_label))
        sections.append("</section>")
    if any(row.month_utc == "2026-04" and row.band_m == 30 for row in rows):
        sections.append("<section><h2>30m April focus: 2026-04-01</h2>")
        sections.append(svg_dusk_bar_chart(rows, 30, "Date: 2026-04-01", month_utc="2026-04"))
        sections.append("</section>")
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Europe Theory V2 Dusk Charts</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; color: #202124; background: #fff; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 32px; border-top: 1px solid #ddd; padding-top: 18px; }}
  p {{ color: #555; max-width: 920px; line-height: 1.5; }}
  svg {{ width: 100%; max-width: 1180px; height: auto; display: block; margin: 12px 0 24px; }}
  .observed {{ fill: #2ca25f; }}
  .theory {{ fill: #e78ac3; }}
  .axis {{ stroke: #333; stroke-width: 1; }}
  .grid {{ stroke: #ddd; stroke-width: 1; }}
  .tick {{ fill: #555; font-size: 10px; }}
  .axis-label {{ fill: #444; font-size: 12px; }}
  .chart-title {{ fill: #222; font-weight: 700; font-size: 14px; }}
  .chart-subtitle {{ fill: #666; font-size: 12px; }}
  .legend {{ display: flex; gap: 18px; margin: 18px 0; align-items: center; }}
  .key {{ display: inline-block; width: 18px; height: 12px; margin-right: 6px; vertical-align: middle; }}
  .key.observed-key {{ background: #2ca25f; }}
  .key.theory-key {{ background: #e78ac3; }}
</style>
</head>
<body>
<h1>Europe Theory V2 Dusk Charts</h1>
<p>Observed bars are Loop 3 long-path spots. Theory V2 is based on receiver-side Australian East Coast dusk illumination at QG62LR, with the 30m band as the primary review target.</p>
<div class="legend">
  <span><span class="key observed-key"></span>Observed Loop 3 spots</span>
  <span><span class="key theory-key"></span>Theory V2 dusk spots</span>
</div>
{''.join(sections)}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def confidence_score(label: str) -> int:
    return {
        "No clear indication": 0,
        "Low confidence": 1,
        "Medium confidence": 2,
        "High confidence": 3,
    }.get(label, 0)


def build_summary_confidence_slots(confidence_rows: list[EuropeConfidenceRow]) -> dict[int, dict[int, dict[str, int]]]:
    slots: dict[int, dict[int, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"short": 0, "long": 0}))
    for row in confidence_rows:
        if row.month_utc != "all":
            continue
        score = confidence_score(row.confidence)
        if row.likely_path == "short_path_loop2":
            slots[row.band_m][row.slot_index]["short"] = max(slots[row.band_m][row.slot_index]["short"], score)
        elif row.likely_path == "long_path_loop3":
            slots[row.band_m][row.slot_index]["long"] = max(slots[row.band_m][row.slot_index]["long"], score)
    return slots


def empirical_bar_confidence_score(row: EuropeBarTruthRow) -> int:
    total = row.observation_count
    dominant = max(row.loop2_count, row.loop3_count)
    share = abs(row.path_dominance_score)
    if total <= 0 or share < 0.15:
        return 0
    probability = binomial_tail_equal_probability(total, dominant)
    if total >= 10 and probability <= 0.01:
        return 3
    if total >= 5 and probability <= 0.05:
        return 2
    if probability <= 0.25:
        return 1
    return 0


def build_bar_truth_summary_confidence_slots(rows: list[EuropeBarTruthRow]) -> dict[int, dict[int, dict[str, int]]]:
    slots: dict[int, dict[int, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"short": 0, "long": 0}))
    for row in rows:
        score = empirical_bar_confidence_score(row)
        if score <= 0:
            continue
        if row.path_dominance_score > 0:
            slots[row.band_m][row.slot_index]["short"] = max(slots[row.band_m][row.slot_index]["short"], score)
        elif row.path_dominance_score < 0:
            slots[row.band_m][row.slot_index]["long"] = max(slots[row.band_m][row.slot_index]["long"], score)
    return slots


def svg_confidence_chart(band_m: int, slot_scores: dict[int, dict[str, int]], date_label: str) -> str:
    width = 1180
    height = 260
    left = 58
    right = 18
    top = 24
    bottom = 44
    plot_w = width - left - right
    plot_h = height - top - bottom
    slot_w = plot_w / 48
    bar_w = max(2.0, slot_w * 0.36)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{band_m}m summary confidence chart">',
        f'<text x="{left}" y="16" class="chart-title">{band_m}m Evidence summary confidence</text>',
        f'<text x="{left + 300}" y="16" class="chart-subtitle">{html.escape(date_label)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>',
    ]
    labels = ["None", "Low", "Med", "High"]
    for score, label in enumerate(labels):
        y = top + plot_h - (score / 3.0) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_w}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" class="tick">{label}</text>')
    for slot in range(48):
        scores = slot_scores.get(slot, {"short": 0, "long": 0})
        x = left + slot * slot_w
        short_h = (scores["short"] / 3.0) * plot_h
        long_h = (scores["long"] / 3.0) * plot_h
        parts.append(
            f'<rect x="{x + slot_w * 0.13:.2f}" y="{top + plot_h - short_h:.2f}" '
            f'width="{bar_w:.2f}" height="{short_h:.2f}" class="short"/>'
        )
        parts.append(
            f'<rect x="{x + slot_w * 0.51:.2f}" y="{top + plot_h - long_h:.2f}" '
            f'width="{bar_w:.2f}" height="{long_h:.2f}" class="long"/>'
        )
        if slot % 2 == 0:
            parts.append(f'<text x="{x + slot_w / 2:.2f}" y="{height - 20}" text-anchor="middle" class="tick">{slot // 2:02d}</text>')
    parts.append(f'<text x="{left + plot_w / 2:.2f}" y="{height - 4}" text-anchor="middle" class="axis-label">UTC hour</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_summary_visuals_html_from_slots(
    slot_scores_by_band: dict[int, dict[int, dict[str, int]]],
    path: Path,
    title: str,
    description: str,
    date_label: str,
) -> None:
    sections = []
    for band in sorted(slot_scores_by_band):
        sections.append(f"<section><h2>{band}m</h2>")
        sections.append(svg_confidence_chart(band, slot_scores_by_band[band], date_label))
        sections.append("</section>")
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; color: #202124; background: #fff; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 30px; border-top: 1px solid #ddd; padding-top: 18px; }}
  p {{ color: #555; max-width: 940px; line-height: 1.5; }}
  a {{ color: #0b57d0; }}
  svg {{ width: 100%; max-width: 1180px; height: auto; display: block; margin: 12px 0 24px; }}
  .short {{ fill: #2b6cb0; }}
  .long {{ fill: #c53030; }}
  .axis {{ stroke: #333; stroke-width: 1; }}
  .grid {{ stroke: #ddd; stroke-width: 1; }}
  .tick {{ fill: #555; font-size: 10px; }}
  .axis-label {{ fill: #444; font-size: 12px; }}
  .chart-title {{ fill: #222; font-weight: 700; font-size: 14px; }}
  .chart-subtitle {{ fill: #666; font-size: 12px; }}
  .legend {{ display: flex; gap: 18px; margin: 18px 0; align-items: center; }}
  .key {{ display: inline-block; width: 18px; height: 12px; margin-right: 6px; vertical-align: middle; }}
  .key.short-key {{ background: #2b6cb0; }}
  .key.long-key {{ background: #c53030; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>Generated: {generated_utc_label()}</p>
<p>{html.escape(date_label)}</p>
<p>{html.escape(description)}</p>
<div class="legend">
  <span><span class="key short-key"></span>Short-path confidence</span>
  <span><span class="key long-key"></span>Long-path confidence</span>
</div>
{''.join(sections)}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def write_europe_summary_visuals_html(
    confidence_rows: list[EuropeConfidenceRow],
    path: Path,
    date_label: str,
) -> None:
    write_summary_visuals_html_from_slots(
        build_summary_confidence_slots(confidence_rows),
        path,
        "Europe Legacy Repeatability Summary Visuals",
        "These charts summarize the legacy repeatability confidence table. This is not the regression bar-truth output.",
        date_label,
    )


def write_europe_bar_truth_summary_visuals_html(
    rows: list[EuropeBarTruthRow],
    path: Path,
    date_label: str,
) -> None:
    write_summary_visuals_html_from_slots(
        build_bar_truth_summary_confidence_slots(rows),
        path,
        "Europe Bar-Truth Confidence Visuals",
        "These charts summarize the empirical loop evidence used by the regression stage. Confidence is based on loop dominance and spot count within each UTC slot and band.",
        date_label,
    )


def antenna_witness(loop2: int, loop3: int) -> str:
    total = loop2 + loop3
    margin = loop2 - loop3
    if total <= 0 or margin == 0:
        return "mixed"
    share_margin = abs(margin) / total
    if margin > 0:
        if abs(margin) >= 5 and share_margin >= 0.35:
            return "strong_short_path_loop2"
        return "weak_short_path_loop2"
    if abs(margin) >= 5 and share_margin >= 0.35:
        return "strong_long_path_loop3"
    return "weak_long_path_loop3"


def endpoint_greyline_witness(rx_score: float, tx_score: float) -> str:
    if rx_score >= 0.55 and tx_score >= 0.55:
        return "both_endpoints_near_greyline"
    if rx_score >= 0.55:
        return "receiver_near_greyline"
    if tx_score >= 0.55:
        return "europe_endpoint_near_greyline"
    if rx_score >= 0.25 or tx_score >= 0.25:
        return "weak_endpoint_greyline"
    return "no_endpoint_greyline"


def sun_path_witness(band_m: int, rx_alt: float, short_dark: float, long_dark: float) -> str:
    if band_m in {30, 40}:
        if long_dark >= 0.55 or australian_dusk_score(rx_alt) >= 0.45:
            return "supports_long_path_dark_or_dusk"
        if short_dark >= 0.55:
            return "supports_short_path_dark"
        return "neutral_or_daylight_for_low_band"
    if long_dark >= 0.45 and short_dark < 0.30:
        return "weak_support_long_path"
    if short_dark >= 0.45 and long_dark < 0.30:
        return "weak_support_short_path"
    return "20m_permissive_neutral"


def sme_rule_witness(band_m: int, slot_index: int, antenna: str, rx_alt: float, long_dark: float) -> str:
    if band_m in {30, 40}:
        if antenna.endswith("long_path_loop3"):
            if australian_dusk_score(rx_alt) >= 0.35 or long_dark >= 0.55:
                return "draft_rule_supports_low_band_long_path"
            return "draft_rule_questions_low_band_long_path"
        if antenna.endswith("short_path_loop2"):
            return "draft_rule_supports_low_band_short_path_when_loop2_dominates"
        return "draft_rule_low_band_mixed"
    return "draft_rule_20m_day_night_paths_possible"


def propagation_rule_witness(band_m: int, sun_witness: str) -> str:
    if band_m in {30, 40}:
        if "long_path" in sun_witness:
            return "draft_rule_low_band_dark_or_dusk_supports_long_path"
        if "short_path" in sun_witness:
            return "draft_rule_low_band_dark_supports_short_path"
        return "draft_rule_low_band_no_clear_path"
    if "long_path" in sun_witness:
        return "draft_rule_20m_weak_long_path_support"
    if "short_path" in sun_witness:
        return "draft_rule_20m_weak_short_path_support"
    return "draft_rule_20m_day_night_paths_possible"


def theory_v3_score(dark_fraction: float, twilight_fraction: float, endpoint_twilight_score: float) -> float:
    return (
        THEORY_V3_DARK_WEIGHT * dark_fraction
        + THEORY_V3_TWILIGHT_WEIGHT * twilight_fraction
        + THEORY_V3_ENDPOINT_WEIGHT * endpoint_twilight_score
    )


def theory_v3_classification(
    band_m: int,
    activity: int,
    short_score: float,
    long_score: float,
    short_dark: float,
    long_dark: float,
) -> tuple[str, str, str, str, str, float]:
    score_margin = abs(short_score - long_score)
    if short_score > long_score:
        path = "short_path"
        winning_dark = short_dark
    elif long_score > short_score:
        path = "long_path"
        winning_dark = long_dark
    else:
        path = "unclear"
        winning_dark = 0.0

    flags: list[str] = []
    if activity < 3:
        flags.append("low_activity")

    if path == "unclear" or score_margin < 0.15:
        final = "no_clear_indication"
        confidence = "No clear indication" if activity >= 3 else "Low confidence"
    elif band_m == 20:
        final = f"{path}_possible_20m_mixed_path"
        if score_margin >= 0.45 and winning_dark >= 0.70 and activity >= 5:
            confidence = "Medium confidence"
        else:
            confidence = "Low confidence"
        flags.append("20m_may_support_multiple_paths")
    else:
        final = f"{path}_likely"
        if score_margin >= 0.45 and winning_dark >= 0.70 and activity >= 5:
            confidence = "High confidence"
        elif score_margin >= 0.30 and activity >= 3:
            confidence = "Medium confidence"
        elif score_margin >= 0.15:
            confidence = "Low confidence"
        else:
            confidence = "No clear indication"

    if path == "short_path":
        witness = "v3_supports_short_path_darkness_score"
        rule = "v3_low_band_prefers_stronger_path_darkness"
    elif path == "long_path":
        witness = "v3_supports_long_path_darkness_score"
        rule = "v3_low_band_prefers_stronger_path_darkness"
    else:
        witness = "v3_no_clear_path_darkness_margin"
        rule = "v3_no_clear_path_darkness_margin"

    if band_m == 20:
        rule = "v3_20m_darkness_is_context_not_standalone_proof"

    return final, confidence, ";".join(flags), witness, rule, score_margin


def repeatability_witness(days_observed: int, consistency_rate: float) -> str:
    if days_observed < 2:
        return "not_enough_same_month_days"
    if consistency_rate >= 0.75:
        return "supports_same_month_repeatability"
    if consistency_rate >= 0.50:
        return "weak_same_month_repeatability"
    return "contradicts_same_month_repeatability"


def path_from_witness(value: str) -> str:
    if "short_path" in value:
        return "short_path"
    if "long_path" in value:
        return "long_path"
    return "unclear"


def classify_evidence(
    band_m: int,
    observation_count: int,
    margin: int,
    antenna: str,
    sun_witness: str,
    greyline_witness: str,
    sme_witness: str,
    repeat_witness: str,
    flags: list[str],
) -> tuple[str, str, str]:
    antenna_path = path_from_witness(antenna)
    sun_path = path_from_witness(sun_witness)
    sme_path = path_from_witness(sme_witness)
    votes = [p for p in [antenna_path, sun_path, sme_path] if p != "unclear"]
    short_votes = votes.count("short_path")
    long_votes = votes.count("long_path")

    if antenna_path == "unclear":
        final = "no_clear_indication"
    elif "possible_back_of_antenna" in flags:
        final = f"{antenna_path}_with_antenna_caution"
    elif short_votes > long_votes:
        final = "short_path_likely"
    elif long_votes > short_votes:
        final = "long_path_likely"
    else:
        final = f"{antenna_path}_antenna_only_tie"

    agreement = max(short_votes, long_votes)
    strong_antenna = antenna.startswith("strong")
    greyline_support = greyline_witness in {
        "both_endpoints_near_greyline",
        "receiver_near_greyline",
        "europe_endpoint_near_greyline",
    }
    if observation_count < 3:
        confidence = "Low confidence"
    elif "possible_back_of_antenna" in flags:
        confidence = "Low confidence"
    elif strong_antenna and agreement >= 3 and greyline_support:
        confidence = "High confidence"
    elif strong_antenna and agreement >= 2:
        confidence = "Medium confidence"
    elif abs(margin) >= 2 and agreement >= 2:
        confidence = "Low confidence"
    else:
        confidence = "No clear indication"

    notes = [
        f"votes short={short_votes} long={long_votes}",
        f"antenna={antenna}",
        f"sun={sun_witness}",
        f"greyline={greyline_witness}",
        f"sme={sme_witness}",
        f"repeatability={repeat_witness}",
    ]
    return final, confidence, "; ".join(notes)


def classify_theory(activity: int, sun_witness: str, greyline_witness: str, propagation_rule: str) -> tuple[str, str, str]:
    sun_path = path_from_witness(sun_witness)
    rule_path = path_from_witness(propagation_rule)
    greyline_support = greyline_witness in {
        "both_endpoints_near_greyline",
        "receiver_near_greyline",
        "europe_endpoint_near_greyline",
    }
    flags: list[str] = []
    if activity < 3:
        flags.append("low_activity")

    if sun_path != "unclear" and sun_path == rule_path:
        final = f"{sun_path}_likely"
    elif sun_path != "unclear":
        final = f"{sun_path}_possible"
    else:
        final = "no_clear_indication"

    if activity < 3:
        confidence = "Low confidence"
    elif final == "no_clear_indication":
        confidence = "No clear indication"
    elif activity >= 12 and greyline_support:
        confidence = "High confidence"
    elif activity >= 5:
        confidence = "Medium confidence"
    else:
        confidence = "Low confidence"
    return final, confidence, ";".join(flags)


def build_europe_evidence_ledger_rows(rows: list[FeatureRow]) -> list[EuropeEvidenceLedgerRow]:
    grouped: dict[tuple[str, str, int, int, str], list[FeatureRow]] = defaultdict(list)
    for row in rows:
        if row.continent != "Europe":
            continue
        key = (row.date_utc, row.utc_slot, row.slot_index, row.band_m, eu_grid_cluster(row.tx_grid))
        grouped[key].append(row)

    monthly_margins: dict[tuple[str, int, int, str], list[int]] = defaultdict(list)
    for key, group in grouped.items():
        date_utc, _utc_slot, slot_index, band_m, grid_cluster = key
        loop2 = sum(row.loop2_count for row in group)
        loop3 = sum(row.loop3_count for row in group)
        monthly_margins[(date_utc[:7], band_m, slot_index, grid_cluster)].append(loop2 - loop3)

    out: list[EuropeEvidenceLedgerRow] = []
    for key, group in sorted(grouped.items()):
        date_utc, utc_slot, slot_index, band_m, grid_cluster = key
        loop2 = sum(row.loop2_count for row in group)
        loop3 = sum(row.loop3_count for row in group)
        total = loop2 + loop3
        if total <= 0:
            continue
        margin = loop2 - loop3
        rx_alt = weighted_average([(row.rx_sun_altitude, row.observation_count) for row in group])
        tx_alt = weighted_average([(row.tx_sun_altitude, row.observation_count) for row in group])
        short_dark = weighted_average([(row.short_path_dark_fraction, row.observation_count) for row in group])
        long_dark = weighted_average([(row.long_path_dark_fraction, row.observation_count) for row in group])
        rx_gl = greyline_altitude_score(rx_alt)
        tx_gl = greyline_altitude_score(tx_alt)
        ant = antenna_witness(loop2, loop3)
        endpoint = endpoint_greyline_witness(rx_gl, tx_gl)
        sun = sun_path_witness(band_m, rx_alt, short_dark, long_dark)
        sme = sme_rule_witness(band_m, slot_index, ant, rx_alt, long_dark)
        repeat_margins = monthly_margins[(date_utc[:7], band_m, slot_index, grid_cluster)]
        repeat_days = len(repeat_margins)
        if margin > 0:
            repeat_consistent = sum(1 for value in repeat_margins if value > 0)
        elif margin < 0:
            repeat_consistent = sum(1 for value in repeat_margins if value < 0)
        else:
            repeat_consistent = sum(1 for value in repeat_margins if value == 0)
        repeat_rate = repeat_consistent / repeat_days if repeat_days else 0.0
        repeat = repeatability_witness(repeat_days, repeat_rate)
        flags: list[str] = []
        if total < 3:
            flags.append("low_observation_count")
        if band_m in {30, 40} and loop2 > 0 and loop3 > 0 and min(loop2, loop3) / total >= 0.25:
            flags.append("both_loops_active_low_band")
        final, confidence, notes = classify_evidence(
            band_m,
            total,
            margin,
            ant,
            sun,
            endpoint,
            sme,
            repeat,
            flags,
        )
        out.append(EuropeEvidenceLedgerRow(
            date_utc=date_utc,
            month_utc=date_utc[:7],
            band_m=band_m,
            utc_slot=utc_slot,
            slot_index=slot_index,
            eu_grid_cluster=grid_cluster,
            observed_short_path_spots=loop2,
            observed_long_path_spots=loop3,
            observation_count=total,
            antenna_margin=margin,
            validation_short_indication=max(margin, 0),
            validation_long_indication=max(-margin, 0),
            antenna_witness=ant,
            rx_sun_altitude=rx_alt,
            tx_sun_altitude=tx_alt,
            short_path_dark_fraction=short_dark,
            long_path_dark_fraction=long_dark,
            endpoint_greyline_witness=endpoint,
            sun_path_witness=sun,
            sme_rule_witness=sme,
            same_month_days_observed=repeat_days,
            same_month_consistency_rate=repeat_rate,
            repeatability_witness=repeat,
            ambiguity_flags=";".join(flags) if flags else "",
            final_path_indication=final,
            confidence=confidence,
            evidence_notes=notes,
        ))
    return out


def write_europe_evidence_ledger_csv(rows: list[EuropeEvidenceLedgerRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EuropeEvidenceLedgerRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            for key, value in data.items():
                if isinstance(value, float):
                    data[key] = f"{value:.6f}"
            writer.writerow(data)


def write_europe_evidence_ledger_date_csv(rows: list[EuropeEvidenceLedgerRow], date_utc: str, path: Path) -> None:
    write_europe_evidence_ledger_csv([row for row in rows if row.date_utc == date_utc], path)


def write_europe_evidence_report(
    rows: list[EuropeEvidenceLedgerRow],
    path: Path,
    title: str = "Europe Evidence Ledger Report",
) -> None:
    by_conf = Counter(row.confidence for row in rows)
    by_final = Counter(row.final_path_indication for row in rows)
    by_band = Counter(row.band_m for row in rows)
    dates = sorted({row.date_utc for row in rows})
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Generated: {generated_utc_label()}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This report is an inspectable evidence ledger. It is not a curve fit.")
    lines.append("Theory/context witnesses are kept separate from validation evidence.")
    lines.append("The fixed-loop directional antennas are validation instruments, not part of the propagation theory.")
    lines.append("")
    lines.append(f"- Dates: {', '.join(dates)}")
    lines.append(f"- Evidence rows: {len(rows):,}")
    lines.append("")
    lines.append("## Rows By Band")
    for band in sorted(by_band):
        lines.append(f"- {band}m: {by_band[band]:,}")
    lines.append("")
    lines.append("## Confidence")
    for label in ["High confidence", "Medium confidence", "Low confidence", "No clear indication"]:
        lines.append(f"- {label}: {by_conf[label]:,}")
    lines.append("")
    lines.append("## Final Indications")
    for label, count in by_final.most_common():
        lines.append(f"- {label}: {count:,}")
    lines.append("")
    lines.append("## High And Medium Confidence Rows By Band")
    for band in sorted(by_band):
        band_rows = [
            row for row in rows
            if row.band_m == band and row.confidence in {"High confidence", "Medium confidence"}
        ]
        band_rows.sort(key=lambda row: (row.slot_index, row.eu_grid_cluster, row.date_utc))
        lines.append("")
        lines.append(f"### {band}m")
        if not band_rows:
            lines.append("")
            lines.append("No high or medium confidence rows.")
            continue
        lines.append("")
        lines.append("| # | Date | Time | Region Grid | Activity | Sun/path | Grey-line | Repeatability | Final indication | Confidence | Flags | Propagation rule | Directional validation |")
        lines.append("| ---: | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |")
        for line_no, row in enumerate(band_rows, 1):
            lines.append(
                f"| {line_no} | {row.date_utc} | {row.utc_slot} | {row.eu_grid_cluster} | "
                f"{row.observation_count} | {row.sun_path_witness} | {row.endpoint_greyline_witness} | "
                f"{row.repeatability_witness} "
                f"({row.same_month_days_observed}d, {row.same_month_consistency_rate:.2f}) | "
                f"{row.final_path_indication} | {row.confidence} | "
                f"{row.ambiguity_flags or '-'} | {row.sme_rule_witness} | "
                f"{row.antenna_witness}; short_ind={row.validation_short_indication}; long_ind={row.validation_long_indication} |"
            )
    lines.append("")
    lines.append("## Review Notes")
    lines.append("")
    lines.append("- Activity is the total Europe loop observations in the raw validation files for that row.")
    lines.append("- Short and long indication columns show the validation margin only; they are not a partition of total activity.")
    lines.append("- Low-count rows are retained but marked with lower confidence.")
    lines.append("- Repeatability is scoped to matching rows across days in the same month. Current one-day-per-month data will mostly show the placeholder `not_enough_same_month_days`.")
    lines.append("- The daily WSPR matrix is intentionally not included in this ledger; it remains a separate context report in the grey-line app.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compact_label(value: str) -> str:
    return value.replace("_", " ")


def confidence_class(value: str) -> str:
    return {
        "High confidence": "conf-high",
        "Medium confidence": "conf-med",
        "Low confidence": "conf-low",
        "No clear indication": "conf-none",
    }.get(value, "conf-none")


def write_europe_evidence_report_html(
    rows: list[EuropeEvidenceLedgerRow],
    path: Path,
    title: str = "Europe Evidence Ledger Report",
) -> None:
    by_conf = Counter(row.confidence for row in rows)
    by_final = Counter(row.final_path_indication for row in rows)
    by_band = Counter(row.band_m for row in rows)
    dates = sorted({row.date_utc for row in rows})
    sections: list[str] = []
    for band in sorted(by_band):
        band_rows = [
            row for row in rows
            if row.band_m == band and row.confidence in {"High confidence", "Medium confidence"}
        ]
        band_rows.sort(key=lambda row: (row.slot_index, row.eu_grid_cluster, row.date_utc))
        row_html = []
        for line_no, row in enumerate(band_rows, 1):
            row_html.append(
                "<tr>"
                f"<td class=\"num\">{line_no}</td>"
                f"<td>{html.escape(row.date_utc)}</td>"
                f"<td>{html.escape(row.utc_slot)}</td>"
                f"<td>{html.escape(row.eu_grid_cluster)}</td>"
                f"<td class=\"num\">{row.observation_count}</td>"
                f"<td>{html.escape(compact_label(row.sun_path_witness))}</td>"
                f"<td>{html.escape(compact_label(row.endpoint_greyline_witness))}</td>"
                f"<td>{html.escape(compact_label(row.repeatability_witness))}"
                f"<br><span class=\"subtle\">{row.same_month_days_observed}d, "
                f"{row.same_month_consistency_rate:.2f}</span></td>"
                f"<td>{html.escape(compact_label(row.final_path_indication))}</td>"
                f"<td class=\"{confidence_class(row.confidence)}\">{html.escape(row.confidence)}</td>"
                f"<td>{html.escape(compact_label(row.ambiguity_flags or '-'))}</td>"
                f"<td>{html.escape(compact_label(row.sme_rule_witness))}</td>"
                f"<td>{html.escape(compact_label(row.antenna_witness))}"
                f"<br><span class=\"subtle\">short ind. {row.validation_short_indication}; "
                f"long ind. {row.validation_long_indication}</span></td>"
                "</tr>"
            )
        if not row_html:
            body = "<p>No high or medium confidence rows.</p>"
        else:
            body = (
                "<div class=\"table-wrap\"><table>"
                "<thead>"
                "<tr class=\"group-head\">"
                "<th colspan=\"4\">Time and area</th>"
                "<th colspan=\"6\">Theory</th>"
                "<th colspan=\"3\">Review and validation</th>"
                "</tr>"
                "<tr class=\"column-head\">"
                "<th>#</th><th>Date</th><th>Time</th><th>Region grid</th>"
                "<th>Activity</th><th>Sun/path</th><th>Grey-line</th><th>Repeatability</th>"
                "<th>Final</th><th>Confidence</th><th>Flags</th>"
                "<th>Propagation rule</th><th>Directional validation</th>"
                "</tr>"
                "</thead><tbody>"
                + "".join(row_html)
                + "</tbody></table></div>"
            )
        sections.append(f"<section><h2>{band}m</h2>{body}</section>")

    conf_summary = "".join(
        f"<li>{html.escape(label)}: {by_conf[label]:,}</li>"
        for label in ["High confidence", "Medium confidence", "Low confidence", "No clear indication"]
    )
    final_summary = "".join(
        f"<li>{html.escape(compact_label(label))}: {count:,}</li>"
        for label, count in by_final.most_common()
    )
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; color: #202124; background: #fff; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 28px; border-top: 1px solid #d9d9d9; padding-top: 16px; }}
  p, li {{ line-height: 1.45; }}
  .meta {{ color: #555; margin: 2px 0; }}
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; max-width: 980px; }}
  .panel {{ border: 1px solid #d7dce2; border-radius: 6px; padding: 12px 14px; background: #fafbfc; }}
  .table-wrap {{ max-width: 100%; max-height: 78vh; overflow: auto; border: 1px solid #cfd6df; border-radius: 6px; }}
  table {{ width: max-content; min-width: 100%; border-collapse: separate; border-spacing: 0; font-size: 12px; table-layout: fixed; }}
  th, td {{ border-right: 1px solid #d7dce2; border-bottom: 1px solid #d7dce2; padding: 5px 6px; vertical-align: top; overflow-wrap: anywhere; }}
  th:last-child, td:last-child {{ border-right: 0; }}
  thead th {{ background: #eef2f6; font-weight: 700; text-align: left; }}
  thead .group-head th {{ position: sticky; top: 0; z-index: 3; text-align: center; border-bottom: 3px double #8793a1; }}
  thead .column-head th {{ position: sticky; top: 29px; z-index: 3; border-bottom: 2px solid #8793a1; }}
  tbody tr:nth-child(even) td {{ background: #f7f7f7; }}
  tbody tr:hover td {{ background: #fff7d6; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .subtle {{ color: #667085; font-size: 11px; }}
  .conf-high {{ background: #d8f3dc !important; font-weight: 700; }}
  .conf-med {{ background: #fff3bf !important; font-weight: 700; }}
  .conf-low {{ background: #ffe5d9 !important; }}
  .conf-none {{ color: #666; }}
  th:nth-child(1), td:nth-child(1) {{ width: 38px; }}
  th:nth-child(2), td:nth-child(2) {{ width: 86px; }}
  th:nth-child(3), td:nth-child(3) {{ width: 52px; }}
  th:nth-child(4), td:nth-child(4) {{ width: 58px; }}
  th:nth-child(5), td:nth-child(5) {{ width: 58px; max-width: 58px; }}
  th:nth-child(6), td:nth-child(6), th:nth-child(7), td:nth-child(7) {{ width: 46px; max-width: 46px; }}
  th:nth-child(8), td:nth-child(8) {{ width: 154px; }}
  th:nth-child(9), td:nth-child(9) {{ width: 172px; }}
  th:nth-child(10), td:nth-child(10) {{ width: 150px; }}
  th:nth-child(11), td:nth-child(11) {{ width: 180px; }}
  th:nth-child(12), td:nth-child(12) {{ width: 156px; }}
  th:nth-child(13), td:nth-child(13) {{ width: 150px; }}
  th:nth-child(14), td:nth-child(14) {{ width: 112px; }}
  th:nth-child(15), td:nth-child(15) {{ width: 132px; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">Generated: {generated_utc_label()}</p>
<p class="meta">Dates: {html.escape(', '.join(dates))}</p>
<p>This HTML report is the polished review version of the evidence ledger. Theory/context witnesses are kept separate from validation evidence. The fixed-loop directional antennas are validation instruments, not part of the propagation theory. The CSV remains the audit source.</p>
<div class="summary">
  <div class="panel"><h3>Confidence</h3><ul>{conf_summary}</ul></div>
  <div class="panel"><h3>Final indications</h3><ul>{final_summary}</ul></div>
</div>
{''.join(sections)}
<h2>Review Notes</h2>
<ul>
  <li>Activity is the total Europe loop observations in the raw validation files for that row.</li>
  <li>Short and long indication columns show the validation margin only; they are not a partition of total activity.</li>
  <li>Low-count rows are retained but marked with lower confidence.</li>
  <li>Repeatability is scoped to matching rows across days in the same month. Current one-day-per-month data will mostly show the placeholder not enough same month days.</li>
  <li>The daily WSPR matrix is intentionally not included in this ledger; it remains a separate context report in the grey-line app.</li>
</ul>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def band_m_from_wspr_live_band(value: str) -> int:
    band = int(float(value))
    return {7: 40, 10: 30, 14: 20}.get(band, band)


def reviewer_endpoint_labels(
    row: dict[str, str],
    endpoint_clusters: tuple[tuple[str, float, float, float], ...] | None,
) -> list[str]:
    if endpoint_clusters is None:
        tx_grid = row.get("tx_loc", "").strip().upper()
        if len(tx_grid) < 4:
            return []
        return [eu_grid_cluster(tx_grid)]
    try:
        tx_lat = float(row["tx_lat"])
        tx_lon = float(row["tx_lon"])
    except (KeyError, ValueError):
        return []
    labels = []
    for label, center_lat, center_lon, radius_km in endpoint_clusters:
        if haversine_km(tx_lat, tx_lon, center_lat, center_lon) <= radius_km:
            labels.append(label)
    return labels


def build_reviewer_ledger_rows(
    path: Path,
    endpoint_clusters: tuple[tuple[str, float, float, float], ...] | None = None,
) -> list[ReviewerLedgerRow]:
    grouped: dict[tuple[str, int, str, int, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            band_m = band_m_from_wspr_live_band(row["band"])
            if band_m not in {20, 30, 40}:
                continue
            dt = dt_from_wspr_live_time(row["time"])
            slot_index, utc_slot = slot_from_dt(dt)
            for endpoint_label in reviewer_endpoint_labels(row, endpoint_clusters):
                key = (dt.date().isoformat(), slot_index, utc_slot, band_m, endpoint_label)
                grouped[key].append(row)

    out: list[ReviewerLedgerRow] = []
    for key, group in sorted(grouped.items()):
        date_utc, slot_index, utc_slot, band_m, region_grid = key
        activity = len(group)
        rx_alt_values: list[tuple[float, int]] = []
        tx_alt_values: list[tuple[float, int]] = []
        short_dark_values: list[tuple[float, int]] = []
        long_dark_values: list[tuple[float, int]] = []
        short_twilight_values: list[tuple[float, int]] = []
        long_twilight_values: list[tuple[float, int]] = []
        for row in group:
            try:
                rx_lat = float(row["rx_lat"])
                rx_lon = float(row["rx_lon"])
                tx_lat = float(row["tx_lat"])
                tx_lon = float(row["tx_lon"])
                dt = dt_from_wspr_live_time(row["time"]).replace(
                    minute=0 if slot_index % 2 == 0 else 30,
                    second=0,
                    microsecond=0,
                )
            except (KeyError, ValueError):
                continue
            rx_alt = solar_altitude_deg(rx_lat, rx_lon, dt)
            tx_alt = solar_altitude_deg(tx_lat, tx_lon, dt)
            sp_dark, sp_twilight = path_darkness_theory_features(rx_lat, rx_lon, tx_lat, tx_lon, dt, False)
            lp_dark, lp_twilight = path_darkness_theory_features(rx_lat, rx_lon, tx_lat, tx_lon, dt, True)
            rx_alt_values.append((rx_alt, 1))
            tx_alt_values.append((tx_alt, 1))
            short_dark_values.append((sp_dark, 1))
            long_dark_values.append((lp_dark, 1))
            short_twilight_values.append((sp_twilight, 1))
            long_twilight_values.append((lp_twilight, 1))
        if not rx_alt_values:
            continue
        rx_alt = weighted_average(rx_alt_values)
        tx_alt = weighted_average(tx_alt_values)
        short_dark = weighted_average(short_dark_values)
        long_dark = weighted_average(long_dark_values)
        short_twilight = weighted_average(short_twilight_values)
        long_twilight = weighted_average(long_twilight_values)
        endpoint_twilight = max(greyline_altitude_score(rx_alt), greyline_altitude_score(tx_alt))
        short_score = theory_v3_score(short_dark, short_twilight, endpoint_twilight)
        long_score = theory_v3_score(long_dark, long_twilight, endpoint_twilight)
        endpoint = endpoint_greyline_witness(greyline_altitude_score(rx_alt), greyline_altitude_score(tx_alt))
        repeat = repeatability_witness(1, 1.0)
        final, confidence, flags, sun, rule, score_margin = theory_v3_classification(
            band_m,
            activity,
            short_score,
            long_score,
            short_dark,
            long_dark,
        )
        out.append(ReviewerLedgerRow(
            date_utc=date_utc,
            utc_slot=utc_slot,
            slot_index=slot_index,
            band_m=band_m,
            region_grid=region_grid,
            activity=activity,
            short_dark_fraction=short_dark,
            long_dark_fraction=long_dark,
            short_twilight_fraction=short_twilight,
            long_twilight_fraction=long_twilight,
            endpoint_twilight_score=endpoint_twilight,
            short_theory_score=short_score,
            long_theory_score=long_score,
            score_margin=score_margin,
            sun_path_witness=sun,
            endpoint_greyline_witness=endpoint,
            repeatability_witness=repeat,
            final_path_indication=final,
            confidence=confidence,
            flags=flags,
            propagation_rule=rule,
            directional_validation="not_provided",
        ))
    return out


def write_reviewer_ledger_csv(rows: list[ReviewerLedgerRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ReviewerLedgerRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.__dict__.copy()
            for key, value in data.items():
                if isinstance(value, float):
                    data[key] = f"{value:.6f}"
            writer.writerow(data)


def write_reviewer_ledger_html(rows: list[ReviewerLedgerRow], path: Path, title: str, source_note: str) -> None:
    by_conf = Counter(row.confidence for row in rows)
    by_final = Counter(row.final_path_indication for row in rows)
    dates = sorted({row.date_utc for row in rows})
    sections: list[str] = []
    for band in sorted({row.band_m for row in rows}):
        band_rows = [row for row in rows if row.band_m == band and row.activity >= 3]
        band_rows.sort(key=lambda row: (row.slot_index, row.region_grid))
        body_rows = []
        for line_no, row in enumerate(band_rows, 1):
            body_rows.append(
                "<tr>"
                f"<td class=\"num\">{line_no}</td>"
                f"<td>{html.escape(row.date_utc)}</td>"
                f"<td>{html.escape(row.utc_slot)}</td>"
                f"<td>{html.escape(row.region_grid)}</td>"
                f"<td class=\"num\">{row.activity}</td>"
                f"<td class=\"num\">{row.short_theory_score:.2f}</td>"
                f"<td class=\"num\">{row.long_theory_score:.2f}</td>"
                f"<td class=\"num\">{row.score_margin:.2f}</td>"
                f"<td>{html.escape(compact_label(row.sun_path_witness))}</td>"
                f"<td>{html.escape(compact_label(row.endpoint_greyline_witness))}</td>"
                f"<td>{html.escape(compact_label(row.repeatability_witness))}</td>"
                f"<td>{html.escape(compact_label(row.final_path_indication))}</td>"
                f"<td class=\"{confidence_class(row.confidence)}\">{html.escape(row.confidence)}</td>"
                f"<td>{html.escape(compact_label(row.flags or '-'))}</td>"
                f"<td>{html.escape(compact_label(row.propagation_rule))}</td>"
                f"<td>{html.escape(compact_label(row.directional_validation))}</td>"
                "</tr>"
            )
        sections.append(
            f"<section><h2>{band}m</h2><div class=\"table-wrap\"><table>"
            "<thead><tr class=\"group-head\"><th colspan=\"4\">Time and area</th>"
            "<th colspan=\"9\">Theory</th><th colspan=\"3\">Review and validation</th></tr>"
            "<tr class=\"column-head\"><th>#</th><th>Date</th><th>Time</th><th>Region grid</th>"
            "<th>Activity</th><th>Short score</th><th>Long score</th><th>Margin</th>"
            "<th>Sun/path</th><th>Grey-line</th><th>Repeatability</th>"
            "<th>Final</th><th>Confidence</th><th>Flags</th><th>Propagation rule</th>"
            "<th>Directional validation</th></tr></thead><tbody>"
            + "".join(body_rows)
            + "</tbody></table></div></section>"
        )

    conf_summary = "".join(f"<li>{html.escape(k)}: {v:,}</li>" for k, v in by_conf.most_common())
    final_summary = "".join(f"<li>{html.escape(compact_label(k))}: {v:,}</li>" for k, v in by_final.most_common())
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; color: #202124; background: #fff; }}
  h1 {{ margin-bottom: 4px; }}
  h2 {{ margin-top: 28px; border-top: 1px solid #d9d9d9; padding-top: 16px; }}
  p, li {{ line-height: 1.45; }}
  .meta {{ color: #555; margin: 2px 0; }}
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; max-width: 980px; }}
  .panel {{ border: 1px solid #d7dce2; border-radius: 6px; padding: 12px 14px; background: #fafbfc; }}
  .table-wrap {{ max-width: 100%; max-height: 78vh; overflow: auto; border: 1px solid #cfd6df; border-radius: 6px; }}
  table {{ width: max-content; min-width: 100%; border-collapse: separate; border-spacing: 0; font-size: 12px; table-layout: fixed; }}
  th, td {{ border-right: 1px solid #d7dce2; border-bottom: 1px solid #d7dce2; padding: 5px 6px; vertical-align: top; overflow-wrap: anywhere; }}
  thead th {{ background: #eef2f6; font-weight: 700; text-align: left; }}
  thead .group-head th {{ position: sticky; top: 0; z-index: 3; text-align: center; border-bottom: 3px double #8793a1; }}
  thead .column-head th {{ position: sticky; top: 29px; z-index: 3; border-bottom: 2px solid #8793a1; }}
  tbody tr:nth-child(even) td {{ background: #f7f7f7; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .conf-high {{ background: #d8f3dc !important; font-weight: 700; }}
  .conf-med {{ background: #fff3bf !important; font-weight: 700; }}
  .conf-low {{ background: #ffe5d9 !important; }}
  .conf-none {{ color: #666; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="meta">Generated: {generated_utc_label()}</p>
<p class="meta">Dates: {html.escape(', '.join(dates))}</p>
<p>{html.escape(source_note)}</p>
<div class="summary">
  <div class="panel"><h3>Confidence</h3><ul>{conf_summary}</ul></div>
  <div class="panel"><h3>Final indications</h3><ul>{final_summary}</ul></div>
</div>
{''.join(sections)}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def path_category(value: str) -> str:
    if "short_path" in value:
        return "short"
    if "long_path" in value:
        return "long"
    return "unclear"


def build_ledger_chart_scores(rows: list[object]) -> dict[int, dict[int, dict[str, int]]]:
    scores: dict[int, dict[int, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"short": 0, "long": 0, "unclear": 0}))
    for row in rows:
        cat = path_category(getattr(row, "final_path_indication"))
        score = confidence_score(getattr(row, "confidence"))
        scores[getattr(row, "band_m")][getattr(row, "slot_index")][cat] = max(
            scores[getattr(row, "band_m")][getattr(row, "slot_index")][cat],
            score,
        )
    return scores


def svg_ledger_confidence_chart(band_m: int, slot_scores: dict[int, dict[str, int]], date_label: str) -> str:
    width = 1120
    height = 260
    left = 52
    right = 20
    top = 34
    bottom = 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    slot_w = plot_w / 48
    max_score = 3
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{band_m}m likely path confidence chart">',
        f'<text x="{left}" y="16" class="chart-title">{band_m}m Likely path confidence</text>',
        f'<text x="{width - right}" y="16" class="chart-subtitle" text-anchor="end">{html.escape(date_label)}</text>',
    ]
    for score, label in [(0, "None"), (1, "Low"), (2, "Med"), (3, "High")]:
        y = top + plot_h - (score / max_score) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="8" y="{y + 4:.2f}" class="axis-label">{label}</text>')
    for slot in range(0, 49, 2):
        x = left + slot * slot_w
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_h}" class="tick"/>')
        if slot < 48:
            parts.append(f'<text x="{x + 2:.2f}" y="{height - 10}" class="axis-label">{slot // 2:02d}</text>')
    colors = {"short": "short-bar", "long": "long-bar", "unclear": "unclear-bar"}
    offsets = {"short": 0.12, "long": 0.40, "unclear": 0.68}
    bar_w = slot_w * 0.20
    for slot in range(48):
        values = slot_scores.get(slot, {})
        for cat in ["short", "long", "unclear"]:
            score = values.get(cat, 0)
            if score <= 0:
                continue
            h = (score / max_score) * plot_h
            x = left + slot * slot_w + slot_w * offsets[cat]
            parts.append(
                f'<rect x="{x:.2f}" y="{top + plot_h - h:.2f}" width="{bar_w:.2f}" '
                f'height="{h:.2f}" class="{colors[cat]}"/>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def write_ledger_summary_visuals_html(rows: list[object], path: Path, title: str, date_label: str) -> None:
    scores = build_ledger_chart_scores(rows)
    sections = [svg_ledger_confidence_chart(band, scores[band], date_label) for band in sorted(scores)]
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; color: #202124; background: #fff; }}
  svg {{ width: 100%; max-width: 1120px; height: auto; display: block; margin: 22px 0 34px; }}
  .chart-title {{ font-size: 16px; font-weight: 700; }}
  .chart-subtitle {{ fill: #666; font-size: 12px; }}
  .axis-label {{ fill: #555; font-size: 11px; }}
  .grid {{ stroke: #e3e6eb; stroke-width: 1; }}
  .tick {{ stroke: #f0f1f4; stroke-width: 1; }}
  .short-bar {{ fill: #2b6cb0; }}
  .long-bar {{ fill: #c53030; }}
  .unclear-bar {{ fill: #888; }}
  .legend {{ display: flex; gap: 18px; margin: 18px 0; align-items: center; }}
  .key {{ display: inline-block; width: 18px; height: 12px; margin-right: 6px; vertical-align: middle; }}
  .short-key {{ background: #2b6cb0; }}
  .long-key {{ background: #c53030; }}
  .unclear-key {{ background: #888; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p>Generated: {generated_utc_label()}</p>
<p>{html.escape(date_label)}</p>
<div class="legend">
  <span><span class="key short-key"></span>Short-path indication</span>
  <span><span class="key long-key"></span>Long-path indication</span>
  <span><span class="key unclear-key"></span>No clear indication</span>
</div>
{''.join(sections)}
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def write_predictions_csv(rows: list[FeatureRow], path: Path) -> None:
    train_rows = filter_training_rows(rows)
    names, x, y, weights = model_matrix(train_rows)
    beta_weighted = fit_wls(x, y, weights)
    preds = predict(x, beta_weighted)
    fieldnames = [
        "date_utc",
        "utc_slot",
        "band_m",
        "continent",
        "country_code",
        "tx_grid",
        "observation_count",
        "path_dominance_score",
        "predicted_path_dominance_score",
        "residual",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row, pred in zip(train_rows, preds):
            writer.writerow({
                "date_utc": row.date_utc,
                "utc_slot": row.utc_slot,
                "band_m": row.band_m,
                "continent": row.continent,
                "country_code": row.country_code,
                "tx_grid": row.tx_grid,
                "observation_count": row.observation_count,
                "path_dominance_score": f"{row.path_dominance_score:.6f}",
                "predicted_path_dominance_score": f"{pred:.6f}",
                "residual": f"{row.path_dominance_score - pred:.6f}",
            })


def natural_key(path: Path) -> list[object]:
    return [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", path.name)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build WSPR path research features and evidence reports.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Raw fixed-loop spot CSV files")
    parser.add_argument("--out-dir", type=Path, default=SCRIPT_DIR / "out")
    args = parser.parse_args()

    input_paths = sorted(args.inputs, key=natural_key)
    raw_rows = read_raw_rows(input_paths)
    feature_rows = build_feature_rows(raw_rows)
    europe_bar_truth_rows = build_europe_bar_truth_rows(feature_rows)
    band_simple_models = fit_band_simple_regressions(europe_bar_truth_rows)
    simple_pred = band_prediction_list(europe_bar_truth_rows, band_simple_models)
    enhanced_beta, enhanced_pred, _enhanced_y, _enhanced_weights = fit_europe_bar_regression(
        europe_bar_truth_rows,
        enhanced_europe_regression_vector,
    )
    europe_regression_prediction_rows = build_europe_regression_prediction_rows(
        europe_bar_truth_rows,
        band_simple_models,
        simple_pred,
        enhanced_pred,
    )
    europe_feature_rows = [row for row in feature_rows if row.continent == "Europe"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_feature_csv(europe_feature_rows, args.out_dir / "wspr_path_features.csv")
    write_europe_bar_truth_csv(europe_bar_truth_rows, args.out_dir / "europe_bar_truth.csv")
    write_europe_regression_predictions_csv(
        europe_regression_prediction_rows,
        args.out_dir / "europe_regression_predictions.csv",
    )
    write_europe_regression_report(
        europe_bar_truth_rows,
        band_simple_models,
        simple_pred,
        enhanced_beta,
        enhanced_pred,
        args.out_dir / "europe_regression_report.md",
    )
    write_europe_regression_visual_report_html(
        europe_bar_truth_rows,
        band_simple_models,
        europe_regression_prediction_rows,
        args.out_dir / "reviewer_package" / "visual_report.html",
    )
    write_export_manifest(
        args.out_dir,
        europe_bar_truth_rows,
        europe_feature_rows,
        europe_regression_prediction_rows,
    )
    write_reviewer_package_index_html(args.out_dir)
    print(f"raw rows read: {len(raw_rows):,}")
    print(f"Europe feature rows written: {len(europe_feature_rows):,}")
    print(f"Europe bar-truth rows written: {len(europe_bar_truth_rows):,}")
    print("regression reports written")
    print(f"outputs: {args.out_dir}")


if __name__ == "__main__":
    main()
