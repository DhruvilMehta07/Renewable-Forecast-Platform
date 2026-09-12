"""
Sprint 1.5 — Exploratory Data Analysis on the horizon-aware forecast dataset.

Standard-procedure checks before modeling:
    1. Summary statistics (numeric + discrete/categorical-like columns)
    2. Missing value re-check
    3. Distributions (target + key features), incl. zero-inflation check
    4. Time series view of raw generation (gaps visible)
    5. Correlation matrix + multicollinearity (VIF) on the actual model input features

Note on the dataset shape: plant1_forecast_dataset.csv has 72 rows per issue_time
(one per horizon). issue_time-level columns (issue_ac_power, issue_ambient_temp, etc.)
are identical across all 72 of those rows, so for "current state" distributions and
time series we de-duplicate to horizon_hours == 1. For target-related analysis
(target_ac_power, target_irradiation, etc.) we use the full dataset since those
genuinely vary by horizon.

Outputs:
    docs/eda/summary_stats.csv
    docs/eda/vif_table.csv
    docs/eda/*.png  (5 figures)
    Console output -> feeds docs/EDA.md findings section
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.stats.outliers_influence import variance_inflation_factor

DATA_PATH = "data/plant1_forecast_dataset.csv"
OUT_DIR = "docs/eda"
import os
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(DATA_PATH, parse_dates=["issue_time", "target_time"])
base = df[df["horizon_hours"] == 1].copy()  # one row per real issue_time (dedup)

print("=" * 60)
print("1. SHAPE & MISSING VALUES")
print("=" * 60)
print(f"Full (horizon-stacked) dataset: {df.shape}")
print(f"De-duplicated (per issue_time) view: {base.shape}")
print(f"Missing values in full dataset:\n{df.isna().sum()[df.isna().sum() > 0]}")
if df.isna().sum().sum() == 0:
    print("No missing values — confirmed clean (dropna already applied at build time).")

print("\n" + "=" * 60)
print("2. SUMMARY STATISTICS")
print("=" * 60)
known_at_issue_cols = ["issue_ac_power", "issue_ac_power_roll_1hr", "issue_ac_power_roll_1day",
                        "issue_ambient_temp", "issue_clearsky_index"]
target_time_cols = ["target_ambient_temp", "target_irradiation", "target_solar_elevation", "target_ac_power"]

issue_stats = base[known_at_issue_cols].describe()
target_stats = df[target_time_cols].describe()
print("Known-at-issue features (de-duplicated):\n", issue_stats)
print("\nTarget-time features + target (full dataset):\n", target_stats)
pd.concat([issue_stats, target_stats], axis=1).to_csv(f"{OUT_DIR}/summary_stats.csv")

print("\n" + "=" * 60)
print("3. DISCRETE / CATEGORICAL-LIKE VARIABLES")
print("=" * 60)
print("is_daytime (target, full dataset):\n", df["target_is_daytime"].value_counts())
print(f"\nhorizon_hours: {df['horizon_hours'].nunique()} distinct values, "
      f"{df['horizon_hours'].value_counts().min()}-{df['horizon_hours'].value_counts().max()} rows each "
      "(should be near-uniform)")
zero_frac = (df["target_ac_power"] == 0).mean()
print(f"\nZero-inflation check: {zero_frac:.1%} of target_ac_power rows are exactly 0 (nighttime — "
      "real physical zeros, not missing data)")

print("\n" + "=" * 60)
print("4. DISTRIBUTIONS")
print("=" * 60)
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
axes[0, 0].hist(df["target_ac_power"], bins=50, color="#1D9E75")
axes[0, 0].set_title("target_ac_power (all horizons)")
axes[0, 1].hist(base["issue_ac_power"], bins=50, color="#378ADD")
axes[0, 1].set_title("issue_ac_power (current state)")
axes[1, 0].hist(df["target_irradiation"], bins=50, color="#EF9F27")
axes[1, 0].set_title("target_irradiation")
axes[1, 1].hist(base["issue_ambient_temp"], bins=50, color="#D85A30")
axes[1, 1].set_title("issue_ambient_temp")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/distributions.png", dpi=110)
plt.close()
print(f"Saved -> {OUT_DIR}/distributions.png")

print("\n" + "=" * 60)
print("5. TIME SERIES VIEW (gaps visible)")
print("=" * 60)
fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(base["issue_time"], base["issue_ac_power"], linewidth=0.7, color="#378ADD")
ax.set_title("Plant 1 AC power over the full 34-day window (gaps = missing sensor readings)")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/timeseries.png", dpi=110)
plt.close()
print(f"Saved -> {OUT_DIR}/timeseries.png")

print("\n" + "=" * 60)
print("6. CORRELATION MATRIX + MULTICOLLINEARITY (VIF)")
print("=" * 60)
model_features = known_at_issue_cols + ["hour", "day_of_year", "horizon_hours"] + \
                  ["target_ambient_temp", "target_irradiation", "target_solar_elevation", "target_is_daytime"]
X = df[model_features].dropna()

corr = X.corr()
fig, ax = plt.subplots(figsize=(9, 7))
im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(model_features)))
ax.set_yticks(range(len(model_features)))
ax.set_xticklabels(model_features, rotation=90, fontsize=8)
ax.set_yticklabels(model_features, fontsize=8)
plt.colorbar(im)
plt.title("Feature correlation matrix (actual model inputs)")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/correlation_heatmap.png", dpi=110)
plt.close()
print(f"Saved -> {OUT_DIR}/correlation_heatmap.png")

vif_data = pd.DataFrame()
vif_data["feature"] = model_features
vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(len(model_features))]
vif_data = vif_data.sort_values("VIF", ascending=False)
vif_data.to_csv(f"{OUT_DIR}/vif_table.csv", index=False)
print(vif_data.to_string(index=False))

print("\nDone. Findings should be written up in docs/EDA.md.")
