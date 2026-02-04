
from fastapi import Request, Query
import sys
sys.path.append("e:/Python/GEN AI/Zarai Radar/RAG")
from RAG.execute_risk import complete_risk_assessment
from fastapi import APIRouter, HTTPException, Depends
from App.schema.climate import ClimateData
from App.schema.climate_risk import RiskItem, WeatherSnapshot, ClimateRiskResponse
from App.routes.auth import get_current_user
from App.db import supabase
from App.services.climate import get_lat_lon_for_district, get_climate_data
from App.data.climate_risk_rules import evaluate_climate_risk, get_overall_level
from App.data.disease_assess import evaluate_disease_pest_risk
from App.data.fertilizer_recommendation import calculate_fertilizer_recommendation, format_for_dashboard

router = APIRouter(tags=['Dashboard'])


@router.get("/dashboard/climate")
async def get_climate_for_current_farmer(current_user: dict = Depends(get_current_user)):
    """
    Get climate data for the logged-in farmer's city.
    Fetches farmer_info (district) for the user, resolves lat/lon for that district, then returns weather.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    farmer = (
        supabase.table("farmer_info")
        .select("district, province")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not farmer.data or len(farmer.data) == 0:
        raise HTTPException(
            status_code=404,
            detail="No farmer profile found. Complete setup (district) first.",
        )

    district = farmer.data[0].get("district")
    province = farmer.data[0].get("province") or ""
    lat, lon = get_lat_lon_for_district(district)

    records = get_climate_data(lat, lon)
    return {
        "district": district,
        "province": province,
        "lat": lat,
        "lon": lon,
        "data": [r.dict() for r in records],
    }



# RAG-based risk assessment endpoint
@router.post("/dashboard/rag-risk")
async def get_rag_risk_for_current_farmer(request: Request, current_user: dict = Depends(get_current_user)):
    """
    RAG-based risk assessment for dashboard (returns full JSON with actions)
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    farmer = (
        supabase.table("farmer_info")
        .select("district, province, crop, stage, crop_start_date")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not farmer.data or len(farmer.data) == 0:
        raise HTTPException(status_code=404, detail="No farmer profile found. Complete setup first.")
    row = farmer.data[0]
    district = row.get("district") or ""
    province = row.get("province") or ""
    crop = row.get("crop") or "Wheat"
    stage = row.get("stage") or "Vegetative"
    days_since_sowing = row.get("crop_start_date") or 0

    lat, lon = get_lat_lon_for_district(district)
    records = get_climate_data(lat, lon)
    if not records:
        raise HTTPException(status_code=502, detail="No climate data for risk assessment.")
    current = records[0]
    weather = {
        "temp": current.temp_c,
        "humidity": current.humidity,
        "rainfall_7d": getattr(current, "rainfall_7d", 0),
        "forecast": getattr(current, "forecast", "")
    }

    farmer_context = {
        "crop": crop,
        "district": district,
        "province": province,
        "stage": stage,
        "days_since_sowing": days_since_sowing,
        "weather": weather,
        "temp": current.temp_c,
        "humidity": current.humidity
    }

    dashboard_data = complete_risk_assessment(farmer_context)
    return dashboard_data

@router.get("/dashboard/climate-risk", response_model=ClimateRiskResponse)
async def get_climate_risk_for_current_farmer(current_user: dict = Depends(get_current_user)):
    """
    Phase 1: Climate risk assessment by (crop, stage) + current weather.
    Fetches farmer profile (crop, stage, district), current weather, evaluates rules, returns risks.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    farmer = (
        supabase.table("farmer_info")
        .select("district, province, crop, stage")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not farmer.data or len(farmer.data) == 0:
        raise HTTPException(
            status_code=404,
            detail="No farmer profile found. Complete setup first.",
        )

    row = farmer.data[0]
    district = row.get("district") or ""
    province = row.get("province") or ""
    crop = row.get("crop") or "Wheat"
    stage = row.get("stage") or "Vegetative"

    lat, lon = get_lat_lon_for_district(district)
    records = get_climate_data(lat, lon)
    if not records:
        raise HTTPException(status_code=502, detail="No climate data for risk assessment.")

    current = records[0]
    weather = {
        "temp_c": current.temp_c,
        "humidity": current.humidity,
        "wind_kph": current.wind_kph,
        "chance_of_rain": current.chance_of_rain,
    }

    climate_assess = evaluate_climate_risk(crop, stage, weather)
    overall = get_overall_level(climate_assess)
    disease_assess = evaluate_disease_pest_risk(crop, stage, weather)
    disease_assess = disease_assess[0]

    # Only return indicators (no actions)
    climate_item = climate_assess[0] if climate_assess else {
        "level": "LOW",
        "message_en": "Weather favorable for current stage.",
        "message_ur": "موجودہ مرحلے کے لیے موسم سازگار ہے۔"
    }
    risks = [
        RiskItem(
            type_key="diseaseRisk",
            level=disease_assess["level"],
            message_en=disease_assess["message_en"],
            message_ur=disease_assess["message_ur"],
            actions_en=[],
            actions_ur=[],
        ),
        RiskItem(
            type_key="pestRisk",
            level="LOW",
            message_en="No elevated pest risk from current conditions. Standard scouting recommended.",
            message_ur="موجودہ حالات سے کیڑوں کا کوئی بڑھا ہوا خطرہ نہیں۔ معیاری جائزہ تجویز ہے۔",
            actions_en=[],
            actions_ur=[],
        ),
        RiskItem(
            type_key="climateRisk",
            level=climate_item["level"],
            message_en=climate_item["message_en"],
            message_ur=climate_item["message_ur"],
            actions_en=[],
            actions_ur=[],
        ),
    ]

    return ClimateRiskResponse(
        overall_level=overall,
        crop=crop,
        stage=stage,
        district=district,
        province=province,
        weather_snapshot=WeatherSnapshot(
            temp_c=weather["temp_c"],
            humidity=weather["humidity"],
            wind_kph=weather["wind_kph"],
            chance_of_rain=weather["chance_of_rain"],
        ),
        risks=risks,
    )

@router.get("/dashboard/fertilizer-recommendation")
def fertilizer_recommendation(current_user: dict = Depends(get_current_user)):
    """
    Endpoint for fertilizer recommendation.
    Returns fertilizer recommendation for the authenticated user (via access token).
    """
    import time
    start_time = time.time()
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    farmer_data  = (
        supabase.table("farmer_info")
        .select("crop, stage, soil_type, irrigation_type, area, crop_start_date, province, district, days_after_sowing")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not farmer_data.data or len(farmer_data.data) == 0:
        raise HTTPException(status_code=404, detail="No farmer profile found. Complete setup first.")
    row = farmer_data.data[0]
    crop = row.get("crop") or "Wheat"
    stage = row.get("stage") or "Vegetative"
    soil_type = row.get("soil_type") or "Loamy"
    irrigation_type = row.get("irrigation_type") or "Flood"
    area = row.get("area") or 1.0
    crop_start_date = row.get("crop_start_date") or ""
    province = row.get("province") or ""
    district = row.get("district") or ""
    days_after_sowing = row.get("days_after_sowing") or 0
    lat, lon = get_lat_lon_for_district(district)
    records = get_climate_data(lat, lon)
    if not records:
        raise HTTPException(status_code=502, detail="No climate data for risk assessment.")

    current = records[0]
    weather = {
        "temp_c": current.temp_c,
        "chance_of_rain": current.chance_of_rain,
    }
    farmer_context = {
        "crop": crop,
        "stage": stage,
        "soil_type": soil_type,
        "irrigation_type": irrigation_type,
        "area": area,
        "crop_start_date": crop_start_date,
        "province": province,
        "district": district,
        "days_after_sowing": days_after_sowing,
        "weather": weather,
    }

    recommendation = calculate_fertilizer_recommendation(farmer_context)
    dashboard = format_for_dashboard(recommendation, farmer_context)
    elapsed = time.time() - start_time
    print(f"[fertilizer-recommendation] Response time: {elapsed:.2f} seconds")
    print(dashboard)
    return {"recommendation": dashboard}