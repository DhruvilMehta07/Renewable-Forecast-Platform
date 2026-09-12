"""
Open-Meteo integration. No API key required. forecast_days=5 provides a buffer
for the local-midnight boundary: the app issues forecasts from a timezone-aware
hour and requires target rows through +72h, which can otherwise fall just beyond
the final hourly value returned by a four-day request.
"""

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def fetch_weather(lat: float, lon: float, timezone: str = "auto") -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,shortwave_radiation",
        "current": "temperature_2m,shortwave_radiation",
        "forecast_days": 5,
        "timezone": timezone,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def geocode_place(query: str, count: int = 5) -> list[dict]:
    resp = requests.get(
        GEOCODING_URL,
        params={
            "name": query,
            "count": count,
            "language": "en",
            "format": "json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])
