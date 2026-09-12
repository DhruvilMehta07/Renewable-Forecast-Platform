"""
Sprint 2 - linear regression baseline, then XGBoost, on a time-based split.

Split (by issue_time, NOT random - see docs/DECISIONS.md for why random would leak):
    train: everything before (max_issue_time - 12 days)
    val:   the 6 days before test - used ONLY to calibrate prediction intervals,
           never seen during model fitting
    test:  the last 6 days - final reported metrics, touched exactly once

Metric note: target_ac_power is exactly 0 for ~46.6% of rows (nighttime - see
docs/EDA.md). MAPE divides by the actual value, so a naive MAPE over all rows
would divide by zero constantly. MAPE below is computed only over rows where
actual generation is meaningfully non-zero (> 100); the zero-generation subset
is reported separately as MAE (which has no such issue).

Missing values: XGBoost trains on the data as-is (native NaN handling). The
linear baseline drops any row with a NaN feature first - see docs/EDA.md
section 1 for which columns and why.

Outputs:
    ml/models/linear_baseline.joblib
    ml/models/xgboost_model.joblib
    docs/eda/metrics_comparison.csv
    docs/eda/feature_importance.png
    docs/eda/prediction_interval_calibration.csv
"""

import pandas as pd
import numpy as np
import joblib
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor

DATA_PATH = "data/plant1_forecast_dataset.csv"
MODEL_DIR = "ml/models"
OUT_DIR = "docs/eda"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

FEATURES = [
    "issue_ac_power", "issue_ac_power_roll_1hr", "issue_ac_power_roll_1day",
    "issue_ambient_temp", "issue_clearsky_index", "hour", "day_of_year",
    "horizon_hours", "target_ambient_temp", "target_irradiation",
    "target_solar_elevation", "target_is_daytime",
]
TARGET = "target_ac_power"
ZERO_THRESHOLD = 100

def time_based_split(df):
    max_t = df["issue_time"].max()
    cutoff_test = max_t - pd.Timedelta(days=6)
    cutoff_val = cutoff_test - pd.Timedelta(days=6)
    train = df[df["issue_time"] < cutoff_val]
    val = df[(df["issue_time"] >= cutoff_val) & (df["issue_time"] < cutoff_test)]
    test = df[df["issue_time"] >= cutoff_test]
    print(f"Split cutoffs -> val starts {cutoff_val}, test starts {cutoff_test}")
    print(f"train: {len(train)} rows | val: {len(val)} rows | test: {len(test)} rows")
    return train, val, test

def compute_metrics(y_true, y_pred, label):
    err = y_pred - y_true
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))
    nonzero_mask = y_true > ZERO_THRESHOLD
    mape = np.mean(np.abs(err[nonzero_mask]) / y_true[nonzero_mask]) * 100
    zero_mask = ~nonzero_mask
    zero_mae = np.mean(np.abs(err[zero_mask])) if zero_mask.sum() > 0 else np.nan
    print(f"[{label}] MAE={mae:.1f}  RMSE={rmse:.1f}  MAPE(daytime only)={mape:.1f}%  "
          f"MAE(near-zero/night rows, n={zero_mask.sum()})={zero_mae:.1f}")
    return {"model": label, "MAE": mae, "RMSE": rmse, "MAPE_daytime_pct": mape, "MAE_night": zero_mae}

def metrics_by_horizon_bucket(df, y_true_col, y_pred, label):
    d = df.copy()
    d["pred"] = y_pred
    d["bucket"] = pd.cut(d["horizon_hours"], bins=[0, 24, 48, 72],
                          labels=["1-24h", "25-48h", "49-72h"])
    rows = []
    for bucket, g in d.groupby("bucket", observed=True):
        err = g["pred"] - g[y_true_col]
        mae = np.mean(np.abs(err))
        rmse = np.sqrt(np.mean(err ** 2))
        rows.append({"model": label, "horizon_bucket": bucket, "MAE": mae, "RMSE": rmse, "n": len(g)})
    return rows

def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["issue_time", "target_time"])
    train, val, test = time_based_split(df)

    all_metrics = []
    horizon_breakdown = []

    print("\n=== Linear regression baseline ===")
    lin_train = train.dropna(subset=FEATURES)
    lin_test = test.dropna(subset=FEATURES)
    dropped_pct = 100 * (1 - len(lin_train) / len(train))
    print(f"Dropped {dropped_pct:.1f}% of train rows for NaN features (linear model only)")

    lin_model = LinearRegression()
    lin_model.fit(lin_train[FEATURES], lin_train[TARGET])
    lin_pred = lin_model.predict(lin_test[FEATURES])
    all_metrics.append(compute_metrics(lin_test[TARGET].values, lin_pred, "linear_baseline"))
    horizon_breakdown += metrics_by_horizon_bucket(lin_test, TARGET, lin_pred, "linear_baseline")

    print("Coefficients (checking the issue_ac_power / roll_1hr pair flagged in EDA):")
    for f, c in zip(FEATURES, lin_model.coef_):
        print(f"  {f}: {c:.4f}")
    joblib.dump(lin_model, f"{MODEL_DIR}/linear_baseline.joblib")

    print("\n=== XGBoost ===")
    xgb_model = XGBRegressor(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    xgb_model.fit(train[FEATURES], train[TARGET])
    xgb_pred_test = xgb_model.predict(test[FEATURES])
    all_metrics.append(compute_metrics(test[TARGET].values, xgb_pred_test, "xgboost"))
    horizon_breakdown += metrics_by_horizon_bucket(test, TARGET, xgb_pred_test, "xgboost")
    joblib.dump(xgb_model, f"{MODEL_DIR}/xgboost_model.joblib")

    importance = pd.Series(xgb_model.feature_importances_, index=FEATURES).sort_values()
    fig, ax = plt.subplots(figsize=(8, 6))
    importance.plot(kind="barh", ax=ax, color="#534AB7")
    ax.set_title("XGBoost feature importance (gain)")
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/feature_importance.png", dpi=110)
    plt.close()
    print("\nFeature importance:\n", importance.sort_values(ascending=False))

    print("\n=== Prediction interval calibration (on val set, not test) ===")
    xgb_pred_val = xgb_model.predict(val[FEATURES])
    val_resid = val[TARGET].values - xgb_pred_val
    val_df = val.copy()
    val_df["abs_resid"] = np.abs(val_resid)
    val_df["bucket"] = pd.cut(val_df["horizon_hours"], bins=[0, 24, 48, 72],
                               labels=["1-24h", "25-48h", "49-72h"])
    interval_table = val_df.groupby("bucket", observed=True)["abs_resid"].quantile(0.90).reset_index()
    interval_table.columns = ["horizon_bucket", "p90_abs_residual"]
    interval_table.to_csv(f"{OUT_DIR}/prediction_interval_calibration.csv", index=False)
    print(interval_table.to_string(index=False))
    print("(Band = prediction +/- p90_abs_residual for that horizon bucket, applied at inference)")

    pd.DataFrame(all_metrics).to_csv(f"{OUT_DIR}/metrics_comparison.csv", index=False)
    pd.DataFrame(horizon_breakdown).to_csv(f"{OUT_DIR}/metrics_by_horizon.csv", index=False)
    print(f"\nSaved metrics -> {OUT_DIR}/metrics_comparison.csv, {OUT_DIR}/metrics_by_horizon.csv")
    print(f"Saved models -> {MODEL_DIR}/linear_baseline.joblib, {MODEL_DIR}/xgboost_model.joblib")

if __name__ == "__main__":
    main()
