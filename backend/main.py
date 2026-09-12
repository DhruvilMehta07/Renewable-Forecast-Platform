from fastapi import FastAPI, HTTPException, Query
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


@app.get("/geocode")
def geocode(query: str = Query(..., min_length=2, max_length=120)):
    query = query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Location query must contain at least 2 characters")
    try:
        results = weather_client.geocode_place(query)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {e}")
    if not results:
        raise HTTPException(status_code=404, detail="No matching location found")
    return {
        "results": [
            {
                "name": result.get("name"),
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude"),
                "country": result.get("country"),
                "admin1": result.get("admin1"),
                "timezone": result.get("timezone"),
            }
            for result in results
        ]
    }


def build_forecast_response(lat, lon, timezone, capacity_kw, approximate):
    try:
        weather_json = weather_client.fetch_weather(lat, lon, timezone)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {e}")

    resolved_timezone = weather_json.get(
        "timezone", timezone if timezone != "auto" else config.TIMEZONE
    )
    feature_df, issue_time = features.build_feature_rows(
        weather_json, lat, lon, resolved_timezone
    )
    predictions = model_service.predict(feature_df)
    scale = capacity_kw / config.SITE_CAPACITY_KW

    forecast_rows = []
    for i, row in feature_df.iterrows():
        prediction = max(0.0, float(predictions[i]))
        if approximate:
            prediction *= scale
        prediction = min(prediction, capacity_kw)
        if not bool(row["target_is_daytime"]):
            prediction = 0.0
        band = model_service.interval_for_horizon(int(row["horizon_hours"]))
        if approximate:
            band *= scale
        forecast_rows.append({
            "target_time": row["target_time"],
            "horizon_hours": int(row["horizon_hours"]),
            "predicted_ac_power": round(prediction, 1),
            "lower_bound": round(max(0.0, prediction - band), 1),
            "upper_bound": round(min(capacity_kw, prediction + band), 1),
            "is_daytime": bool(row["target_is_daytime"]),
            "decision": decision_engine.decide(
                prediction, row["target_is_daytime"], capacity_kw
            ),
        })

    database.save_run(issue_time.isoformat(), forecast_rows)
    return {
        "issue_time": issue_time.isoformat(),
        "site": {
            "lat": lat,
            "lon": lon,
            "timezone": resolved_timezone,
            "capacity_kw": capacity_kw,
        },
        "mode": "what_if" if approximate else "plant_1",
        "approximate": approximate,
        "forecast": forecast_rows,
    }


@app.get("/forecast")
def get_forecast():
    return build_forecast_response(
        config.LAT, config.LON, config.TIMEZONE, config.SITE_CAPACITY_KW, False
    )


@app.get("/forecast/what-if")
def get_what_if_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    capacity_kw: float = Query(..., gt=0, le=1_000_000),
    timezone: str = Query("auto", min_length=1, max_length=64),
):
    return build_forecast_response(latitude, longitude, timezone, capacity_kw, True)


@app.get("/feature-importance")
def get_feature_importance():
    model = model_service.get_model()
    raw_importance = [float(x) for x in model.feature_importances_]
    total_importance = sum(raw_importance)
    importance_values = (
        [value / total_importance for value in raw_importance]
        if total_importance > 0
        else raw_importance
    )
    importance = dict(zip(config.FEATURES, importance_values))
    return {"feature_importance": dict(sorted(importance.items(), key=lambda kv: -kv[1]))}


@app.get("/history")
def get_history(limit: int = 10):
    return {"runs": database.get_recent_runs(limit)}
