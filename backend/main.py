import re

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
import weather_client
import features
import model_service
import decision_engine
import database
from auth import create_access_token, get_current_user, hash_password, verify_password

app = FastAPI(title="Renewable Forecast Platform API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

database.init_db()


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
    }


@app.post("/auth/signup")
def signup(request: SignupRequest):
    username = request.username.strip()
    display_name = request.display_name.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
        raise HTTPException(status_code=422, detail="Username may contain only letters, numbers, dot, underscore, and hyphen")
    if not display_name:
        raise HTTPException(status_code=422, detail="Display name is required")
    if database.get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username is already registered")
    user = database.create_user(username, display_name, hash_password(request.password))
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": public_user(user)}


@app.post("/auth/login")
def login(request: LoginRequest):
    user = database.get_user_by_username(request.username.strip())
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": public_user(user)}


@app.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": public_user(user)}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/geocode")
def geocode(query: str = Query(..., min_length=2, max_length=120), user: dict = Depends(get_current_user)):
    query = query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Location query must contain at least 2 characters")
    try:
        results = weather_client.geocode_place(query)
        if not results:
            fallback_terms = [term for term in query.split() if len(term) >= 3]
            fallback_results = []
            seen_locations = set()
            for term in fallback_terms:
                for result in weather_client.geocode_place(term, count=3):
                    location_key = (result.get("latitude"), result.get("longitude"))
                    if location_key not in seen_locations:
                        seen_locations.add(location_key)
                        fallback_results.append(result)
                    if len(fallback_results) == 3:
                        break
                if len(fallback_results) == 3:
                    break
            results = fallback_results
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


def build_forecast_response(lat, lon, timezone, capacity_kw, approximate, user_id):
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

    database.save_run(
        issue_time.isoformat(),
        forecast_rows,
        site={"lat": lat, "lon": lon, "timezone": resolved_timezone, "capacity_kw": capacity_kw},
        mode="what_if" if approximate else "plant_1",
        user_id=user_id,
    )
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
def get_forecast(user: dict = Depends(get_current_user)):
    return build_forecast_response(
        config.LAT, config.LON, config.TIMEZONE, config.SITE_CAPACITY_KW, False, user["id"]
    )


@app.get("/forecast/what-if")
def get_what_if_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    capacity_kw: float = Query(..., gt=0, le=1_000_000),
    timezone: str = Query("auto", min_length=1, max_length=64),
    user: dict = Depends(get_current_user),
):
    return build_forecast_response(latitude, longitude, timezone, capacity_kw, True, user["id"])


@app.get("/feature-importance")
def get_feature_importance(user: dict = Depends(get_current_user)):
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
def get_history(limit: int = Query(10, ge=1, le=50), user: dict = Depends(get_current_user)):
    return {"runs": database.get_recent_runs(limit, user["id"])}
