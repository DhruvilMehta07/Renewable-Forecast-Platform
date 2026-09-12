"""
Assembles the 72 feature rows (one per horizon, 1-72h ahead) for a single
forecast request. This is the live-inference counterpart to
ml/build_forecast_dataset.py - the column set and meaning must match exactly,
or the model receives inputs shaped differently than it was trained on.

known-at-issue power features (issue_ac_power, roll_1hr, roll_1day):
    No live SCADA feed exists for this dataset, so "current output" can't be
    read from a real sensor. Sprint 2's feature importance analysis
    (docs/MODELING.md) showed these three features carry ~0.1% combined
    importance - so rather than build a self-prediction bootstrap to
    approximate them, they're set to 0 here. This is a documented
    simplification, not an oversight: the evidence says it doesn't matter.

issue_ambient_temp / issue_clearsky_index:
    Unlike the power features, these DO have a live source (Open-Meteo's
    `current` block) and are computed properly, not placeholdered.
"""

from datetime import timedelta
import numpy as np
import pandas as pd
import pvlib


def build_feature_rows(weather_json: dict, lat: float, lon: float, timezone: str) -> tuple[pd.DataFrame, pd.Timestamp]:
    issue_time = pd.Timestamp.now(tz="UTC").tz_convert(timezone).tz_localize(None).floor("h")

    current = weather_json["current"]
    issue_ambient_temp = current["temperature_2m"]
    issue_irradiation_kw = current["shortwave_radiation"] / 1000.0  # Open-Meteo: W/m^2 -> training scale: kW/m^2

    issue_time_tz = pd.DatetimeIndex([issue_time]).tz_localize(timezone)
    solpos_now = pvlib.solarposition.get_solarposition(issue_time_tz, lat, lon)
    # haurwitz returns a DataFrame with a "ghi" column, not a bare Series -
    # a bug caught by the test suite before this ever reached the API.
    clearsky_now = float(pvlib.clearsky.haurwitz(solpos_now["apparent_zenith"])["ghi"].iloc[0])
    issue_clearsky_index = (
        float(np.clip(issue_irradiation_kw * 1000 / clearsky_now, 0, 1.5)) if clearsky_now > 5 else 0.0
    )

    hourly = weather_json["hourly"]
    hourly_times = pd.to_datetime(hourly["time"])
    weather_lookup = {
        t: (temp, rad) for t, temp, rad in zip(hourly_times, hourly["temperature_2m"], hourly["shortwave_radiation"])
    }

    target_times = [issue_time + timedelta(hours=h) for h in range(1, 73)]
    target_times_tz = pd.DatetimeIndex(target_times).tz_localize(timezone)
    solpos_targets = pvlib.solarposition.get_solarposition(target_times_tz, lat, lon)
    elevations = solpos_targets["apparent_elevation"].values

    rows = []
    for h, target_dt, elevation in zip(range(1, 73), target_times, elevations):
        if target_dt not in weather_lookup:
            raise ValueError(
                f"Open-Meteo response doesn't cover target time {target_dt} (horizon {h}h) - "
                "check forecast_days is large enough."
            )
        temp, rad_w = weather_lookup[target_dt]
        rows.append({
            "issue_ac_power": 0.0,
            "issue_ac_power_roll_1hr": 0.0,
            "issue_ac_power_roll_1day": 0.0,
            "issue_ambient_temp": issue_ambient_temp,
            "issue_clearsky_index": issue_clearsky_index,
            "hour": target_dt.hour + target_dt.minute / 60,
            "day_of_year": target_dt.dayofyear,
            "horizon_hours": h,
            "target_ambient_temp": temp,
            "target_irradiation": rad_w / 1000.0,
            "target_solar_elevation": elevation,
            "target_is_daytime": int(elevation > 0),
            "target_time": target_dt.isoformat(),
        })

    return pd.DataFrame(rows), issue_time
