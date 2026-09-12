"""
Loads the trained XGBoost model once (module-level cache) and exposes
prediction + interval lookup. See docs/MODELING.md for why these specific
values and why this specific model was chosen over the linear baseline.
"""

import joblib
import config

_model = None


def get_model():
    global _model
    if _model is None:
        _model = joblib.load(config.MODEL_PATH)
    return _model


def predict(feature_df):
    model = get_model()
    return model.predict(feature_df[config.FEATURES])


def interval_for_horizon(h: int) -> float:
    if h <= 24:
        return config.PREDICTION_INTERVALS["1-24h"]
    elif h <= 48:
        return config.PREDICTION_INTERVALS["25-48h"]
    return config.PREDICTION_INTERVALS["49-72h"]
