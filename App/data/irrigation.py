from datetime import datetime, timedelta
from fastapi import HTTPException
import os, requests
from App.db import supabase
from App.services.climate import get_weekly_weather, get_lat_lon_for_district

# ----------------------------------
# Wheat Stage Function
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


def calculate_crop_et(temp_max, temp_min, humidity, stage):
    """Calculate crop evapotranspiration"""
    temp_avg = (temp_max + temp_min) / 2
    temp_range = max(temp_max - temp_min, 0.1)
    
    # Reference ET (simplified)
    et0 = 0.0023 * (temp_avg + 17.8) * (temp_range ** 0.5)
    
    # Crop coefficient by stage
    KC = {
        "Sowing": 0.3,
        "Vegetative": 0.7,
        "Flowering": 1.15,
        "Harvest": 0.6
    }
    
    crop_et = et0 * KC.get(stage, 0.7)
    return round(crop_et, 2)  # mm/day


def calculate_soil_moisture_deficit(
    last_irrigation_days_ago,
    rainfall_last_7d,
    et_daily,
    soil_type
):
    """Calculate if irrigation is needed based on moisture deficit"""
    
    # Field capacity (mm) by soil type
    FIELD_CAPACITY = {
        "Loamy": 150,
        "Loam": 150,
        "Sandy": 80,
        "Clay": 180
    }
    
    # Water used since last irrigation
    water_used = et_daily * last_irrigation_days_ago
    
    # Water added by rain
    water_added = rainfall_last_7d
    
    # Current moisture deficit
    deficit = max(water_used - water_added, 0)
    
    # Trigger irrigation at 50% depletion
    soil_key = soil_type if soil_type in FIELD_CAPACITY else "Loamy"
    threshold = FIELD_CAPACITY[soil_key] * 0.5
    
    return deficit >= threshold


def irrigation_decision_improved(
    stage, 
    sub_stage, 
    soil, 
    weather,
    last_irrigation_das,
    days_since_last_rain
):
    """Improved irrigation decision"""
    
    et_daily = calculate_crop_et(
        weather["temp_max"],
        weather["temp_min"],
        weather["humidity"],
        stage
    )
    
    needs_water = calculate_soil_moisture_deficit(
        last_irrigation_days_ago=last_irrigation_das,
        rainfall_last_7d=weather["rain_7d"],
        et_daily=et_daily,
        soil_type=soil
    )
    
    # Rain forecast check
    if weather.get("rain_forecast_48h", 0) > 15:
        return "delay", "Heavy rain expected"
    
    # Critical stage check
    if sub_stage in CRITICAL_SUBSTAGES and needs_water:
        return "irrigate_urgent", f"Critical stage + moisture deficit"
    
    # Regular decision
    if needs_water:
        return "irrigate", f"Soil moisture deficit reached"
    elif days_since_last_rain < 2:
        return "skip", "Recent rain sufficient"
    else:
        return "monitor", "Moisture adequate"


async def generate_weekly_plan_with_weather(ctx):

    das = ctx["days_after_sowing"]
    soil = ctx["soil_type"]
    irrigation_type = ctx["irrigation_type"]
    district = ctx["district"]

    # Get coordinates
    lat, lon = get_lat_lon_for_district(district)

    # Fetch weather async
    weekly_weather = await get_weekly_weather(lat, lon)

    weekly_plan = []
    depth = 0

    for i, day_weather in enumerate(weekly_weather):

        future_das = das + i
        stage, sub_stage = get_wheat_stage(future_das)

        decision, d, temp_max = irrigation_decision(
            stage,
            sub_stage,
            soil,
            irrigation_type,
            day_weather
        )
        if i == 0: depth = d

        weekly_plan.append({
            "day": datetime.fromisoformat(day_weather["date"]).strftime("%a"),
            "stage": stage,
            "sub_stage": sub_stage,
            "status": decision,
            "rain_mm": day_weather["rain_mm"]
        })

    return weekly_plan, depth


def get_irrigation_context(farmer_context):
    """Get last irrigation/rainfall info (Sync Supabase)"""
    # Assuming user_id is passed as farmer_id or in ctx
    fid = farmer_context.get("farmer_id") or farmer_context.get("user_id")
    if not fid: return {"last_irrigation_date": None, "last_rainfall_date": None, "rainfall_last_7d": 0}

    # Last irrigation
    last_irrigation = (
        supabase.table("irrigation_logs")
        .select("event_date, amount_mm")
        .eq("farmer_id", fid)
        .eq("event_type", "irrigation")
        .order("event_date", desc=True)
        .limit(1)
        .execute()
    )
    
    # Last rainfall
    last_rainfall = (
        supabase.table("irrigation_logs")
        .select("event_date, amount_mm")
        .eq("farmer_id", fid)
        .eq("event_type", "rainfall")
        .order("event_date", desc=True)
        .limit(1)
        .execute()
    )
    
    # Rainfall last 7 days
    seven_days_ago = (datetime.now() - timedelta(days=7)).date()
    # Handle string comparison or date comparison if needed
    rainfall_7d = (
        supabase.table("irrigation_logs")
        .select("amount_mm")
        .eq("farmer_id", fid)
        .eq("event_type", "rainfall")
        .gte("event_date", seven_days_ago.isoformat())
        .execute()
    )
    
    total_rain_7d = sum(row["amount_mm"] for row in rainfall_7d.data) if rainfall_7d.data else 0
    
    return {
        "last_irrigation_date": last_irrigation.data[0]["event_date"] if last_irrigation.data else None,
        "last_rainfall_date": last_rainfall.data[0]["event_date"] if last_rainfall.data else None,
        "rainfall_last_7d": round(total_rain_7d, 1)
    }


async def wheat_irrigation_advisory_v2(farmer_context):
    """Improved irrigation advisory with ET and moisture tracking"""
    
    das = farmer_context["days_after_sowing"]
    stage, sub_stage = get_wheat_stage(das)
    
    # Calculate days since last irrigation
    if farmer_context.get("last_irrigation_date"):
        try:
            last_irrigation = datetime.fromisoformat(farmer_context["last_irrigation_date"].replace('Z', '+00:00'))
            days_since_irrigation = (datetime.now(last_irrigation.tzinfo) - last_irrigation).days
        except:
            days_since_irrigation = das
    else:
        days_since_irrigation = das
    
    # Get weather
    lat, lon = get_lat_lon_for_district(farmer_context["district"])
    weekly_weather = await get_weekly_weather(lat, lon)
    
    today_weather = weekly_weather[0]
    et_daily = calculate_crop_et(
        today_weather["temp_max"],
        today_weather["temp_min"],
        today_weather["humidity"],
        stage
    )
    
    needs_irrigation = calculate_soil_moisture_deficit(
        last_irrigation_days_ago=days_since_irrigation,
        rainfall_last_7d=farmer_context.get("rainfall_last_7d", 0),
        et_daily=et_daily,
        soil_type=farmer_context["soil_type"]
    )
    
    # Days since last rain
    days_since_last_rain = das
    if farmer_context.get("last_rainfall_date"):
        try:
            last_rain = datetime.fromisoformat(farmer_context["last_rainfall_date"].replace('Z', '+00:00'))
            days_since_last_rain = (datetime.now(last_rain.tzinfo) - last_rain).days
        except:
            pass

    decision, reason = irrigation_decision_improved(
        stage, sub_stage,
        farmer_context["soil_type"],
        {
            **today_weather,
            "rain_forecast_48h": sum(w["rain_mm"] for w in weekly_weather[:2]),
            "rain_7d": farmer_context.get("rainfall_last_7d", 0)
        },
        days_since_irrigation,
        days_since_last_rain
    )
    
    base_depth = STAGE_WATER_DEPTH.get(stage, 2.5)
    depth = round(
        base_depth * 
        SOIL_FACTOR.get(farmer_context["soil_type"], 1.0) * 
        IRRIGATION_EFFICIENCY.get(farmer_context["irrigation_type"], 1.0),
        1
    )
    
    return {
        "decision": decision,
        "reason": reason,
        "depth_inches": depth,
        "timing": irrigation_time(today_weather["temp_max"]),
        "et_daily_mm": et_daily,
        "days_since_last_irrigation": days_since_irrigation,
        "moisture_status": "deficit" if needs_irrigation else "adequate",
        "weekly_plan": [
            {
                "day": w["date"],
                "temp": f"{w['temp_min']}-{w['temp_max']}°C",
                "rain": f"{w['rain_mm']}mm",
                "status": "Check"
            }
            for w in weekly_weather
        ]
    }


async def get_irrigation_advisory(farmer_context):
    """Main entry point - Optimized"""
    # 1. Get history context (Supabase - sync)
    irrigation_ctx = get_irrigation_context(farmer_context)
    
    # 2. Update context
    farmer_context.update(irrigation_ctx)
    
    # 3. Advisory (Async Weather)
    return await wheat_irrigation_advisory_v2(farmer_context)
