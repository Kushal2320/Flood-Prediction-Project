# app/risk_engine.py
import requests
import os
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

OWM = os.getenv("OPENWEATHER_API_KEY") or os.getenv("OPENWEATHER_KEY")

if not OWM:
    raise RuntimeError("OPENWEATHER_API_KEY missing from .env")

router = APIRouter()


# -------------------------
# 1) GEOCODING ENDPOINT
# -------------------------
@router.get("/geocode")
def geocode(city: str = Query(..., min_length=1)):
    """
    Uses OpenWeather API to get lat/lon for an Indian city.
    """
    try:
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {"q": city + ",IN", "limit": 1, "appid": OWM}
        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            raise HTTPException(400, f"OpenWeather Geocode error: {r.text}")

        data = r.json()
        if not data:
            raise HTTPException(404, "City not found")

        item = data[0]
        return {
            "name": item.get("name", city),
            "lat": item["lat"],
            "lon": item["lon"],
        }

    except Exception as e:
        raise HTTPException(500, f"Geocode error: {e}")


# -------------------------
# 2) RISK ENGINE
# -------------------------
@router.get("/risk")
def risk(lat: float, lon: float):
    """
    Simple rainfall-based flood risk estimation using OpenWeather 'onecall'.
    """
    try:
        url = "https://api.openweathermap.org/data/2.5/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely",
            "appid": OWM,
            "units": "metric",
        }
        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            raise HTTPException(400, f"OWM error: {r.text}")

        data = r.json()

        # Extract rain metrics
        hourly = data.get("hourly", [])
        rain_1h = hourly[0]["rain"]["1h"] if (hourly and "rain" in hourly[0]) else 0
        rain_3h = sum(h.get("rain", {}).get("1h", 0) for h in hourly[:3])
        rain_24h = sum(h.get("rain", {}).get("1h", 0) for h in hourly[:24])

        score = int(rain_3h * 2 + rain_24h * 1.2)

        # risk level
        if score > 100:
            level = "High"
        elif score > 40:
            level = "Moderate"
        else:
            level = "Low"

        alerts = []
        if rain_3h > 15:
            alerts.append("Heavy rainfall expected soon.")
        if rain_24h > 50:
            alerts.append("Sustained heavy rain in last 24h.")

        return {
            "level": level,
            "score": score,
            "reason": f"Rain 3h={rain_3h}mm, 24h={rain_24h}mm",
            "signals": {
                "rain_3h_mm": rain_3h,
                "rain_24h_mm": rain_24h,
            },
            "alerts": alerts,
        }

    except Exception as e:
        raise HTTPException(500, f"Risk engine error: {e}")
