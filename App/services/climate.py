import httpx
import datetime
import asyncio
from dotenv import load_dotenv
import os
from schema.climate import ClimateData
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from pathlib import Path
import time

env_path = Path(__file__).resolve().parent / "services" / ".env"
load_dotenv(dotenv_path=env_path)

# Simple TTL Cache for weather data
# Keys: "lat_lon_type", Values: {"data": ..., "expires": timestamp}
WEATHER_CACHE: Dict[str, Dict] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

# Coordinates (lat, lon) for farmer districts
DISTRICT_COORDINATES = {
    "Lahore": (31.5204, 74.3587),
    "Multan": (30.1978, 71.4711),
    "Faisalabad": (31.4181, 73.0789),
    "Gujranwala": (32.1877, 74.1945),
    "Rawalpindi": (33.6007, 73.0679),
    "Karachi": (24.8607, 67.0011),
    "Hyderabad": (25.3969, 68.3578),
    "Sukkur": (27.7052, 68.8574),
    "Larkana": (27.5604, 68.2267),
    "Peshawar": (33.9920, 71.4800),
    "Mardan": (34.1983, 72.0450),
    "Abbottabad": (34.1688, 73.2215),
    "Swat": (34.7795, 72.3624),
    "Quetta": (30.1798, 66.9750),
    "Gwadar": (25.1214, 62.3254),
    "Turbat": (26.0026, 63.0500),
    "Khuzdar": (27.7384, 66.6434),
}


def get_lat_lon_for_district(district: str) -> tuple[float, float]:
    """Return (lat, lon) for a district name. Case-insensitive lookup."""
    if not district:
        raise HTTPException(status_code=400, detail="District is required")
    key = district.strip()
    for name, coords in DISTRICT_COORDINATES.items():
        if name.lower() == key.lower():
            return coords
    raise HTTPException(
        status_code=404,
        detail=f"Coordinates not defined for district: {district}.",
    )


async def get_climate_data(lat: float, lon: float) -> List[ClimateData]:
    """
    Fetch current-hour climate data asynchronously with caching.
    """
    cache_key = f"{lat}_{lon}_current"
    now_ts = time.time()
    
    if cache_key in WEATHER_CACHE:
        if now_ts < WEATHER_CACHE[cache_key]["expires"]:
            return WEATHER_CACHE[cache_key]["data"]

    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeather API key not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Current Weather (OpenWeather)
        current_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        
        # Forecast (Open-Meteo)
        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability"
            "&current_weather=true"
            "&timezone=auto"
        )

        try:
            responses = await asyncio.gather(
                client.get(current_url),
                client.get(forecast_url)
            )
            
            curr_res, fore_res = responses
            curr_res.raise_for_status()
            fore_res.raise_for_status()
            
            current_data = curr_res.json()
            data = fore_res.json()
            
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Weather service error: {str(e)}")

    humidity_now = current_data["main"]["humidity"]
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    now = datetime.datetime.now()
    current_hour_str = now.strftime("%Y-%m-%dT%H:00")
    records = []
    
    for i, time_str in enumerate(times):
        if time_str == current_hour_str:
            records.append(
                ClimateData(
                    datetime=time_str,
                    temp_c=hourly["temperature_2m"][i],
                    humidity=humidity_now,
                    wind_kph=hourly["wind_speed_10m"][i],
                    chance_of_rain=hourly["precipitation_probability"][i],
                    condition="Clear" if hourly["precipitation_probability"][i] < 20 else "Cloudy"
                )
            )
            break

    if not records:
        raise HTTPException(status_code=404, detail="No climate data available for current hour")

    # Update Cache
    WEATHER_CACHE[cache_key] = {
        "data": records,
        "expires": now_ts + CACHE_TTL_SECONDS
    }

    return records


async def get_weekly_weather(lat: float, lon: float) -> List[Dict]:
    """
    Fetch 7-day weather forecast asynchronously with caching.
    """
    cache_key = f"{lat}_{lon}_weekly"
    now_ts = time.time()
    
    if cache_key in WEATHER_CACHE:
        if now_ts < WEATHER_CACHE[cache_key]["expires"]:
            return WEATHER_CACHE[cache_key]["data"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "relative_humidity_2m_mean"
        ],
        "timezone": "auto"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Weekly weather service error: {str(e)}")

    daily = data.get("daily", {})
    weekly_weather = []

    for i in range(len(daily.get("time", []))):
        weekly_weather.append({
            "date": daily["time"][i],
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "rain_mm": daily["precipitation_sum"][i],
            "humidity": daily["relative_humidity_2m_mean"][i]
        })

    # Update Cache
    WEATHER_CACHE[cache_key] = {
        "data": weekly_weather,
        "expires": now_ts + CACHE_TTL_SECONDS
    }

    return weekly_weather


if __name__ == "__main__":
    # Test
    # asyncio.run(get_climate_data(30.1978, 71.4711))
    pass
