"""
Central config for the backend. Values here are pulled directly from earlier
sprints - nothing invented fresh:
- LAT/LON: the approximate site location used throughout ml/ (docs/DECISIONS.md)
- FEATURES: must exactly match the column order ml/train_models.py trained on,
  or the model will silently misinterpret which number means what
- PREDICTION_INTERVALS: the val-set calibration from docs/MODELING.md (Sprint 2)
- SITE_CAPACITY_KW: no real nameplate/grid-demand data is available for this
  dataset (out of scope - see docs/DECISIONS.md future scope). Using the max
  observed generation in the training data as a practical proxy for "capacity"
  is a documented limitation, not a real grid-operations figure.
"""

import os

LAT = 14.5
LON = 78.0
TIMEZONE = "Asia/Kolkata"

# Paths resolved relative to this file, not the working directory - so the
# app behaves the same whether it's launched from the repo root or from
# inside backend/ (both are common: `uvicorn backend.main:app` vs `cd backend
# && uvicorn main:app`).
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)

# LightGBM is the selected live model; xgboost_model.joblib remains available
# as the retained benchmark/fallback artifact.
MODEL_PATH = os.path.join(_REPO_ROOT, "ml", "models", "lightgbm_model.joblib")
DB_PATH = os.path.join(_BACKEND_DIR, "forecast.db")

FEATURES = [
    "issue_ambient_temp", "issue_clearsky_index", "hour", "day_of_year",
    "horizon_hours", "target_ambient_temp", "target_irradiation",
    "target_solar_elevation", "target_is_daytime",
]

# LightGBM validation-set p90 absolute residual, by horizon bucket
PREDICTION_INTERVALS = {
  "1-24h": 692.1,
  "25-48h": 766.5,
  "49-72h": 895.5,
}

SITE_CAPACITY_KW = 29150  # max observed AC_POWER in training data - see docstring above
CURTAIL_THRESHOLD_PCT = 0.90
UNDERPERFORM_THRESHOLD_PCT = 0.10
