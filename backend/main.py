from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
import weather_client
import features
import model_service
import decision_engine
import database

app = FastAPI(title="Renewable Forecast Platform API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

database.init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/forecast")
def get_forecast():
    try:
        weather_json = weather_client.fetch_weather(config.LAT, config.LON, config.TIMEZONE)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {e}")

    feature_df, issue_time = features.build_feature_rows(weather_json, config.LAT, config.LON, config.TIMEZONE)
    predictions = model_service.predict(feature_df)

    forecast_rows = []
    for i, row in feature_df.iterrows():
        # Generation can never be physically negative; XGBoost isn't aware of that
        # constraint and occasionally predicts small negative values near zero
        # (e.g. at night) - clip here rather than at training time.
        pred = max(0.0, float(predictions[i]))
        # Nighttime generation is a known physical zero (confirmed in docs/EDA.md) -
        # any nonzero prediction here is regression noise, not signal. A live run
        # showed jitter like 203.4 kW at is_daytime=false hours, which is harmless
        # to the decision engine (it's gated off at night regardless) but looks
        # like a bug on a dashboard chart. Snapping to 0 is enforcing a known
        # ground truth, not hiding a real result.
        if not bool(row["target_is_daytime"]):
            pred = 0.0
        band = model_service.interval_for_horizon(int(row["horizon_hours"]))
        forecast_rows.append({
            "target_time": row["target_time"],
            "horizon_hours": int(row["horizon_hours"]),
            "predicted_ac_power": round(pred, 1),
            "lower_bound": round(max(0.0, pred - band), 1),
            "upper_bound": round(pred + band, 1),
            "is_daytime": bool(row["target_is_daytime"]),
            "decision": decision_engine.decide(pred, row["target_is_daytime"]),
        })

    database.save_run(issue_time.isoformat(), forecast_rows)

    return {
        "issue_time": issue_time.isoformat(),
        "site": {"lat": config.LAT, "lon": config.LON},
        "forecast": forecast_rows,
    }


@app.get("/feature-importance")
def get_feature_importance():
    model = model_service.get_model()
    importance = dict(zip(config.FEATURES, [float(x) for x in model.feature_importances_]))
    return {"feature_importance": dict(sorted(importance.items(), key=lambda kv: -kv[1]))}


@app.get("/history")
def get_history(limit: int = 10):
    return {"runs": database.get_recent_runs(limit)}
