"""
Sprint 1 (revised) — build a genuine 24-72hr-AHEAD forecasting dataset, not a nowcast dataset.

Why this file replaces the first version of prepare_data.py:
    The first version computed lag/rolling features and a target from the SAME timestamp.
    That trains a model to answer "given current weather, what's current power?" — useful,
    but not what the ideation report asks for (predict 24-72hrs ahead). It also assumed the
    15-min timeline had no gaps, which is false: there are 107 missing timestamps in 34 days.
    A plain .shift(4) for "1 hour ago" is silently wrong across a gap.

What changed:
    1. Reindex to a continuous 15-min timeline (asfreq) BEFORE any shifting, so "shift by 4
       steps" is always exactly 1 hour of wall-clock time, gap or no gap.
    2. Split every feature into two families:
       - "known-at-issue" features: computed from data at time t (now, when the forecast is
         issued) — current power, recent rolling averages, current weather.
       - "target-time" features: computed at time t+h (the future point being forecast) —
         weather, solar position, time-of-day at that future moment.
    3. horizon_hours becomes an actual feature (1 to 72). One model learns to answer "given
       what's happening now, and the forecast conditions for a point h hours out, what will
       generation be at that point?" — for any h, not one model per horizon.

Important documented assumption ("perfect prog"):
    For target-time weather (AMBIENT_TEMPERATURE, IRRADIATION), we use the actual historical
    sensor reading at the target timestamp as a stand-in for "what the weather forecast said."
    This is a standard backtesting simplification used when historical archived forecasts
    aren't available — it measures how good the MODEL is, assuming a perfect weather forecast.
    At live inference (Sprint 3), these two columns get replaced by Open-Meteo's actual
    forecast values for that future timestamp — everything else about the row is unchanged.
    This is a real limitation to state plainly in the README: reported accuracy will be
    somewhat optimistic versus live performance, because real weather forecasts have their
    own error that this backtest doesn't see.

Output:
    data/plant1_forecast_dataset.csv — one row per (issue_time, horizon_hours) pair.
"""

import pandas as pd
import numpy as np
import pvlib

LAT, LON = 14.5, 78.0
TZ = "Asia/Kolkata"
GEN_PATH = "data/Plant_1_Generation_Data.csv"
WEATHER_PATH = "data/Plant_1_Weather_Sensor_Data.csv"
OUT_PATH = "data/plant1_forecast_dataset.csv"
HORIZONS_HOURS = list(range(1, 73))  # 1..72 hours ahead, hourly


def load_generation(path):
    df = pd.read_csv(path)
    df["DATE_TIME"] = pd.to_datetime(df["DATE_TIME"], format="%d-%m-%Y %H:%M")
    return (
        df.groupby("DATE_TIME")
        .agg(AC_POWER=("AC_POWER", "sum"))
        .reset_index()
    )


def load_weather(path):
    df = pd.read_csv(path)
    df["DATE_TIME"] = pd.to_datetime(df["DATE_TIME"], format="%Y-%m-%d %H:%M:%S")
    return df[["DATE_TIME", "AMBIENT_TEMPERATURE", "IRRADIATION"]]


def build_continuous_timeline(gen, weather):
    df = pd.merge(gen, weather, on="DATE_TIME", how="outer").sort_values("DATE_TIME")
    df = df.set_index("DATE_TIME").asfreq("15min")  # <- introduces explicit NaN for gaps
    return df


def add_solar_position(df):
    times = df.index.tz_localize(TZ)
    solpos = pvlib.solarposition.get_solarposition(times, LAT, LON)
    df["solar_elevation"] = solpos["apparent_elevation"].values
    df["is_daytime"] = (df["solar_elevation"] > 0).astype(int)
    clearsky = pvlib.clearsky.haurwitz(solpos["apparent_zenith"])
    df["clearsky_ghi"] = clearsky.values
    df["clearsky_index"] = np.clip(
        np.where(df["clearsky_ghi"] > 5, df["IRRADIATION"] * 1000 / df["clearsky_ghi"], np.nan), 0, 1.5
    )
    df["hour"] = df.index.hour + df.index.minute / 60
    df["day_of_year"] = df.index.dayofyear
    return df


def add_known_at_issue_features(df):
    # These describe conditions AT the moment the forecast is issued (time t).
    df["issue_ac_power"] = df["AC_POWER"]
    df["issue_ac_power_roll_1hr"] = df["AC_POWER"].shift(1).rolling(4, min_periods=2).mean()
    df["issue_ac_power_roll_1day"] = df["AC_POWER"].shift(1).rolling(96, min_periods=24).mean()
    df["issue_ambient_temp"] = df["AMBIENT_TEMPERATURE"]
    df["issue_clearsky_index"] = df["clearsky_index"]
    return df


def build_horizon_stack(df):
    """For each horizon h, pair 'known-at-issue' columns (at t) with 'target-time'
    columns (at t+h) and the target AC_POWER (at t+h). Stack all horizons."""
    known_cols = [
        "issue_ac_power", "issue_ac_power_roll_1hr", "issue_ac_power_roll_1day",
        "issue_ambient_temp", "issue_clearsky_index", "hour", "day_of_year",
    ]
    frames = []
    for h in HORIZONS_HOURS:
        steps = h * 4  # 15-min steps per hour
        target_time = df.index + pd.Timedelta(hours=h)
        block = pd.DataFrame(index=df.index)
        block["issue_time"] = df.index
        block["target_time"] = target_time
        block["horizon_hours"] = h
        for c in known_cols:
            block[c] = df[c]
        # target-time features: shift the FUTURE value back onto this row
        block["target_ambient_temp"] = df["AMBIENT_TEMPERATURE"].shift(-steps).values
        block["target_irradiation"] = df["IRRADIATION"].shift(-steps).values
        block["target_solar_elevation"] = df["solar_elevation"].shift(-steps).values
        block["target_is_daytime"] = df["is_daytime"].shift(-steps).values
        block["target_ac_power"] = df["AC_POWER"].shift(-steps).values  # <- the label
        frames.append(block)
    stacked = pd.concat(frames, ignore_index=True)
    return stacked


def main():
    gen = load_generation(GEN_PATH)
    weather = load_weather(WEATHER_PATH)
    df = build_continuous_timeline(gen, weather)
    print(f"Continuous timeline: {len(df)} rows ({df['AC_POWER'].isna().sum()} gap rows in AC_POWER)")

    df = add_solar_position(df)
    df = add_known_at_issue_features(df)

    stacked = build_horizon_stack(df)
    before = len(stacked)
    stacked = stacked.dropna(subset=[
        "issue_ac_power", "target_ac_power", "target_ambient_temp", "target_irradiation"
    ])
    after = len(stacked)

    stacked.to_csv(OUT_PATH, index=False)

    print(f"\nRows before dropna: {before}, after: {after} ({before - after} dropped — gaps/edges)")
    print(f"Base (issue) time range: {stacked['issue_time'].min()} -> {stacked['issue_time'].max()}")
    print(f"Horizons: {stacked['horizon_hours'].min()}-{stacked['horizon_hours'].max()} hours, "
          f"{stacked['horizon_hours'].nunique()} distinct values")
    print(f"Columns: {list(stacked.columns)}")
    print(f"\nSaved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
