import requests
import datetime
from dotenv import load_dotenv
import os
from App.schema.climate import ClimateData
from fastapi import APIRouter, HTTPException, Depends
from App.routes.auth import get_current_user
from App.db import supabase

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

router = APIRouter()

# Coordinates (lat, lon) for farmer districts – same cities as in setup
DISTRICT_COORDINATES = {
    # Punjab
    "Lahore": (31.5204, 74.3587),
    "Multan": (30.1978, 71.4711),
    "Faisalabad": (31.4181, 73.0789),
    "Gujranwala": (32.1877, 74.1945),
    "Rawalpindi": (33.6007, 73.0679),
    # Sindh
    "Karachi": (24.8607, 67.0011),
    "Hyderabad": (25.3969, 68.3578),
    "Sukkur": (27.7052, 68.8574),
    "Larkana": (27.5604, 68.2267),
    # KPK
    "Peshawar": (33.9920, 71.4800),
    "Mardan": (34.1983, 72.0450),
    "Abbottabad": (34.1688, 73.2215),
    "Swat": (34.7795, 72.3624),
    # Balochistan
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
        detail=f"Coordinates not defined for district: {district}. Supported: {list(DISTRICT_COORDINATES.keys())}",
    )


def get_climate_data(lat: float, lon: float):
    'Get the climate data for a given latitude and longitude of particular city and hour'
    forecast_days = 1
    # WeatherAPI URL
    url = f"http://api.weatherapi.com/v1/forecast.json?key={OPENWEATHER_API_KEY}&q={lat},{lon}&days={forecast_days}&aqi=no&alerts=yes"
    # Fetch data
    data = requests.get(url).json()

    # Parse hourly forecast
    records = []
    cur =  datetime.datetime.now()
    curHour = cur.hour

    for day in data['forecast']['forecastday']:
        
        for hour in day['hour']:
            fore = int(hour['time'].split(" ")[1].split(":")[0])
                
            if curHour == fore:
                records.append(ClimateData(
                    datetime=hour['time'],
                    temp_c=hour['temp_c'],
                    humidity=hour['humidity'],
                    wind_kph=hour['wind_kph'],
                    chance_of_rain=hour['chance_of_rain'],
                    condition=hour['condition']['text']
                ))
                break
    if not records:
        raise HTTPException(status_code=404, detail="No climate data found for the given latitude and longitude")
    return records

