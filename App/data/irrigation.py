from datetime import datetime, timedelta
# from App.services.climate import get_weekly_weather, get_lat_lon_for_district
from fastapi import HTTPException
import os, requests
# ----------------------------------
# Wheat Stage Function (Given)
# ----------------------------------
def get_wheat_stage(das):
    if das <= 14:
        return "Sowing", "Germination/Emergence"
    elif das <= 35:
        return "Vegetative", "Tillering"
    elif das <= 55:
        return "Vegetative", "Jointing"
    elif das <= 75:
        return "Vegetative", "Booting"
    elif das <= 90:
        return "Flowering", "Heading"
    elif das <= 105:
        return "Flowering", "Anthesis"
    elif das <= 110:
        return "Flowering", "Early Grain Fill"
    elif das <= 125:
        return "Harvest", "Grain Filling"
    else:
        return "Harvest", "Maturity"


# ----------------------------------
# Agronomy Knowledge Tables
# ----------------------------------

# Base irrigation depth per stage (inches)
STAGE_WATER_DEPTH = {
    "Sowing": 3.0,
    "Vegetative": 2.5,
    "Flowering": 3.0,
    "Harvest": 1.5
}

# Critical substages needing high water
CRITICAL_SUBSTAGES = [
    "Tillering",
    "Booting",
    "Heading",
    "Anthesis",
    "Early Grain Fill"
]

# Soil retention factor
SOIL_FACTOR = {
    "Loamy": 1.0,
    "Sandy": 1.2,
    "Clay": 0.8
}

# Irrigation efficiency factor
IRRIGATION_EFFICIENCY = {
    "Canal": 1.0,
    "Tube Well": 0.95,
    "Rainfed": 0.7
}


# ----------------------------------
# Core Decision Function
# ----------------------------------
def irrigation_decision(stage, sub_stage, soil, irrigation_type, weather):

    base_depth = STAGE_WATER_DEPTH.get(stage, 2.5)

    soil_factor = SOIL_FACTOR.get(soil, 1)
    irrigation_factor = IRRIGATION_EFFICIENCY.get(irrigation_type, 1)

    depth = round(base_depth * soil_factor * irrigation_factor, 1)

    rain = weather["rain_mm"]

    temp_max = weather["temp_max"]
    temp_min = weather["temp_min"]

    avg_temp = (temp_max + temp_min) / 2

    if rain > 8:
        decision = "rain"
    elif sub_stage in CRITICAL_SUBSTAGES:
        decision = "irrigate"
    elif avg_temp > 30:
        decision = "irrigate"
    else:
        decision = "rest"

    return decision, depth, temp_max

def irrigation_time(temp_max):

    if temp_max > 32:
        return "Early Morning or Evening"
    elif temp_max > 28:
        return "Morning"
    else:
        return "Late Morning"

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


def get_weekly_weather(lat, lon):
    """
    Fetch 7-day weather forecast using Open-Meteo
    """

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

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    daily = data["daily"]

    weekly_weather = []

    for i in range(len(daily["time"])):

        weekly_weather.append({
            "date": daily["time"][i],
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "rain_mm": daily["precipitation_sum"][i],
            "humidity": daily["relative_humidity_2m_mean"][i]
        })

    return weekly_weather

# ----------------------------------
# Weekly Planner
# ----------------------------------

def generate_weekly_plan_with_weather(ctx):

    das = ctx["days_after_sowing"]
    soil = ctx["soil_type"]
    irrigation_type = ctx["irrigation_type"]
    district = ctx["district"]

    # Get coordinates
    lat, lon = get_lat_lon_for_district(district)

    # Fetch weather
    weekly_weather = get_weekly_weather(lat, lon)

    weekly_plan = []

    for i, day_weather in enumerate(weekly_weather):

        future_das = das + i
        stage, sub_stage = get_wheat_stage(future_das)

        decision, depth, temp_max = irrigation_decision(
        stage,
        sub_stage,
        soil,
        irrigation_type,
        day_weather
    )


        weekly_plan.append({
            "day": datetime.fromisoformat(day_weather["date"]).strftime("%a"),
            "stage": stage,
            "sub_stage": sub_stage,
            "status": decision,
            "rain_mm": day_weather["rain_mm"]
        })

    return weekly_plan, depth

# ----------------------------------
# Main Advisory Function
# ----------------------------------
def wheat_irrigation_advisory(farmer_context):

    das = farmer_context["days_after_sowing"]
    soil = farmer_context["soil_type"]
    irrigation_type = farmer_context["irrigation_type"]
    weather = farmer_context["weather"]

    weekly_plan, depth = generate_weekly_plan_with_weather(farmer_context)

    

    temp = weather["temperature"]
    return {
        "weekly_plan": weekly_plan,
        "next_water": {
            "decision": weekly_plan[0]["status"],
            "depth": f"{depth} inches",
            "timing": irrigation_time(temp)
        }
    }

farmer_context = {
    "days_after_sowing": 60,
    "soil_type": "Loamy",
    "irrigation_type": "Tube Well",
    "province": "Punjab",
    "district": "Multan",
    "weather": {
        "rain_forecast_mm": 2,
        "temperature": 33
    }
}

result = wheat_irrigation_advisory(farmer_context)

print(result)
