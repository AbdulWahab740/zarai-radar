import requests
import datetime
from dotenv import load_dotenv
import os
# from App.schema.climate import ClimateData
from fastapi import HTTPException
from pydantic import BaseModel

class ClimateData(BaseModel):
    """Climate data for a given datetime"""
    temp_c: float
    humidity: int
    wind_kph: float
    chance_of_rain: int
    condition: str
    datetime: str
load_dotenv()

# OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_API_KEY = 'd4882fbbc373398cc80603262290fdeb'
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

import requests
import datetime
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List


class ClimateData(BaseModel):
    """Climate data for a given datetime"""
    datetime: str
    temp_c: float
    humidity: int
    wind_kph: float
    chance_of_rain: int
    condition: str


def get_climate_data(lat: float, lon: float) -> List[ClimateData]:
    """
    Fetch current-hour climate data using Open-Meteo (free, no API key)
    """

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability"
        "&current_weather=true"
        "&timezone=auto"
    )

    response = requests.get(url)
    data = response.json()

    if "hourly" not in data:
        raise HTTPException(
            status_code=502,
            detail="Invalid response from Open-Meteo"
        )

    hourly = data["hourly"]
    times = hourly["time"]

    now = datetime.datetime.now()
    current_hour_str = now.strftime("%Y-%m-%dT%H:00")

    records = []

    for i, time_str in enumerate(times):
        if time_str == current_hour_str:
            records.append(
                ClimateData(
                    datetime=time_str,
                    temp_c=hourly["temperature_2m"][i],
                    humidity=hourly["relative_humidity_2m"][i],
                    wind_kph=hourly["wind_speed_10m"][i],
                    chance_of_rain=hourly["precipitation_probability"][i],
                    condition="Derived from precipitation probability"
                )
            )
            break

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No climate data available for current hour"
        )

    return records


if __name__ == "__main__":
    print(get_climate_data(30.1978, 71.4711))
