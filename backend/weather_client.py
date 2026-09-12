"""
Open-Meteo integration. No API key required. forecast_days=4 (not 3) is
deliberate: forecast_days=3 returns hours from midnight of today through
midnight+72h, which can fall short of a full 72h-ahead window depending on
what time "now" actually is. 4 days guarantees coverage regardless of time of day.
"""

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat: float, lon: float, timezone: str) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,shortwave_radiation",
        "current": "temperature_2m,shortwave_radiation",
        "forecast_days": 4,
        "timezone": timezone,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
