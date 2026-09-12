"""
Tests the API without hitting the real network - weather_client.fetch_weather
is monkeypatched with a synthetic-but-realistic Open-Meteo response covering
today through +4 days, so target-time lookups always resolve regardless of
when the test runs.
"""

import sys
import os
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


def test_forecast_endpoint_shape_and_values(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    monkeypatch.setattr(weather_client, "fetch_weather", lambda lat, lon, tz: make_mock_weather())

    client = TestClient(main.app)
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

    client = TestClient(main.app)
    client.get("/forecast")
    resp = client.get("/history")
    assert resp.status_code == 200
    assert len(resp.json()["runs"]) == 1


def test_feature_importance_sums_to_one():
    client = TestClient(main.app)
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

    client = TestClient(main.app)
    resp = client.get("/forecast")
    data = resp.json()

    for row in data["forecast"]:
        if not row["is_daytime"]:
            assert row["predicted_ac_power"] == 0.0


def test_weather_fetch_failure_returns_502(monkeypatch):
    def broken(lat, lon, tz):
        raise ConnectionError("simulated network failure")
    monkeypatch.setattr(weather_client, "fetch_weather", broken)

    client = TestClient(main.app)
    resp = client.get("/forecast")
    assert resp.status_code == 502
