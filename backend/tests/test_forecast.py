"""
Tests the API without hitting the real network - weather_client.fetch_weather
is monkeypatched with a synthetic-but-realistic Open-Meteo response covering
today through +4 days, so target-time lookups always resolve regardless of
when the test runs.
"""

import sys
import os
from uuid import uuid4
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import config
import database
import weather_client
import main


def make_mock_weather():
    now = pd.Timestamp.now(tz="UTC").tz_convert(config.TIMEZONE).tz_localize(None).floor("h")
    start = now.floor("D")
    times = [start + pd.Timedelta(hours=i) for i in range(24 * 4)]
    time_strs = [t.isoformat(timespec="minutes") for t in times]
    radiation = [max(0, 800 * np.sin(np.pi * (t.hour - 6) / 12)) if 6 <= t.hour <= 18 else 0 for t in times]
    temperature = [25 + 5 * np.sin(np.pi * (t.hour - 6) / 12) for t in times]
    return {
        "current": {"time": now.isoformat(timespec="minutes"), "temperature_2m": 28.0, "shortwave_radiation": 400.0},
        "hourly": {"time": time_strs, "temperature_2m": temperature, "shortwave_radiation": radiation},
    }


def _use_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()


def _authenticated_client():
    client = TestClient(main.app)
    username = f"test_{uuid4().hex[:10]}"
    response = client.post(
        "/auth/signup",
        json={"username": username, "password": "test-password-123", "display_name": "Test User"},
    )
    assert response.status_code == 200
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    client.test_username = username
    return client


def test_protected_forecast_requires_authentication():
    response = TestClient(main.app).get("/forecast")
    assert response.status_code == 401


def test_signup_login_and_duplicate_username():
    client = TestClient(main.app)
    username = f"operator_{uuid4().hex[:10]}"
    payload = {"username": username, "password": "secure-pass-123", "display_name": "Grid Operator"}

    signup = client.post("/auth/signup", json=payload)
    assert signup.status_code == 200
    assert signup.json()["user"]["username"] == username
    assert "password_hash" not in signup.json()["user"]

    duplicate = client.post("/auth/signup", json=payload)
    assert duplicate.status_code == 409

    login = client.post("/auth/login", json={"username": username, "password": payload["password"]})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    wrong_password = client.post("/auth/login", json={"username": username, "password": "wrong-password"})
    assert wrong_password.status_code == 401


def test_history_is_scoped_to_authenticated_user():
    first = _authenticated_client()
    second = _authenticated_client()
    first_user = database.get_user_by_username(first.test_username)
    database.save_run("2026-01-01T00:00:00", [], {"capacity_kw": 1}, "plant_1", first_user["id"])
    assert len(first.get("/history").json()["runs"]) == 1
    assert len(second.get("/history").json()["runs"]) == 0


def test_forecast_endpoint_shape_and_values(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(weather_client, "fetch_weather", lambda lat, lon, tz: make_mock_weather())

    client = _authenticated_client()
    resp = client.get("/forecast")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["forecast"]) == 72
    assert [row["horizon_hours"] for row in data["forecast"]] == list(range(1, 73))

    for row in data["forecast"]:
        assert row["predicted_ac_power"] >= 0
        assert row["lower_bound"] <= row["predicted_ac_power"] <= row["upper_bound"]
        assert row["decision"] in {"curtail", "backup_dispatch", "normal"}


def test_forecast_saved_to_history(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(weather_client, "fetch_weather", lambda lat, lon, tz: make_mock_weather())

    client = _authenticated_client()
    client.get("/forecast")
    resp = client.get("/history")
    assert resp.status_code == 200
    assert len(resp.json()["runs"]) == 1
    assert len(resp.json()["runs"][0]["forecast"]) == 72


def test_what_if_forecast_is_approximate_and_capacity_scaled(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(weather_client, "fetch_weather", lambda lat, lon, tz: make_mock_weather())

    client = _authenticated_client()
    resp = client.get("/forecast/what-if?latitude=19.076&longitude=72.877&capacity_kw=5000")
    assert resp.status_code == 200
    data = resp.json()

    assert data["mode"] == "what_if"
    assert data["approximate"] is True
    assert data["site"]["capacity_kw"] == 5000
    assert len(data["forecast"]) == 72
    assert all(row["predicted_ac_power"] <= 5000 for row in data["forecast"])


def test_weather_request_keeps_five_day_coverage(monkeypatch):
    captured = {}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return make_mock_weather()

    def fake_get(url, params, timeout):
        captured.update(params)
        return MockResponse()

    monkeypatch.setattr(weather_client.requests, "get", fake_get)
    weather_client.fetch_weather(14.5, 78.0, "Asia/Kolkata")
    assert captured["forecast_days"] == 5


def test_geocode_returns_selectable_locations(monkeypatch):
    monkeypatch.setattr(weather_client, "geocode_place", lambda query: [{
        "name": "Mumbai",
        "latitude": 19.076,
        "longitude": 72.877,
        "country": "India",
        "admin1": "Maharashtra",
        "timezone": "Asia/Kolkata",
    }])

    response = _authenticated_client().get("/geocode?query=Mumbai")
    assert response.status_code == 200
    assert response.json()["results"][0]["timezone"] == "Asia/Kolkata"


def test_geocode_no_results_returns_404(monkeypatch):
    monkeypatch.setattr(weather_client, "geocode_place", lambda query, count=5: [])
    response = _authenticated_client().get("/geocode?query=UnknownPlace")
    assert response.status_code == 404


def test_geocode_falls_back_to_query_terms(monkeypatch):
    def geocode(query, count=5):
        if query == "Dhirubhai Ambani":
            return []
        return [
            {
                "name": f"{query} result {index}",
                "latitude": float(index),
                "longitude": float(index),
                "country": "India",
                "admin1": None,
                "timezone": "Asia/Kolkata",
            }
            for index in range(1, 5)
        ]

    monkeypatch.setattr(weather_client, "geocode_place", geocode)
    response = _authenticated_client().get("/geocode?query=Dhirubhai%20Ambani")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 3


def test_geocode_failure_returns_502(monkeypatch):
    def broken(query):
        raise ConnectionError("simulated geocoding failure")

    monkeypatch.setattr(weather_client, "geocode_place", broken)
    response = _authenticated_client().get("/geocode?query=Mumbai")
    assert response.status_code == 502


def test_feature_importance_sums_to_one():
    client = _authenticated_client()
    resp = client.get("/feature-importance")
    assert resp.status_code == 200
    values = resp.json()["feature_importance"].values()
    assert abs(sum(values) - 1.0) < 0.01


def test_night_predictions_are_exact_zero(monkeypatch, tmp_path):
    """Real live testing showed small nonzero jitter (e.g. 203.4 kW) at night -
    nighttime generation is a known physical zero (docs/EDA.md), so it should
    always be snapped to exactly 0, never left as noisy regression output."""
    _use_temp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(weather_client, "fetch_weather", lambda lat, lon, tz: make_mock_weather())

    client = _authenticated_client()
    resp = client.get("/forecast")
    data = resp.json()

    for row in data["forecast"]:
        if not row["is_daytime"]:
            assert row["predicted_ac_power"] == 0.0


def test_weather_fetch_failure_returns_502(monkeypatch):
    def broken(lat, lon, tz):
        raise ConnectionError("simulated network failure")
    monkeypatch.setattr(weather_client, "fetch_weather", broken)

    client = _authenticated_client()
    resp = client.get("/forecast")
    assert resp.status_code == 502
