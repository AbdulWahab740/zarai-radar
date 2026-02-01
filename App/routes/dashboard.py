from fastapi import APIRouter, HTTPException, Depends
from App.schema.climate import ClimateData
from App.schema.climate_risk import RiskItem, WeatherSnapshot, ClimateRiskResponse
from App.routes.auth import get_current_user
from App.db import supabase
from App.services.climate import get_lat_lon_for_district, get_climate_data
from App.data.climate_risk_rules import evaluate_climate_risk, get_overall_level

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

    triggered = evaluate_climate_risk(crop, stage, weather)
    overall = get_overall_level(triggered)

    # Build risk items: climate from rules; disease/pest as placeholders (LOW) for Phase 1
    climate_item = triggered[0] if triggered else {
        "level": "LOW",
        "message_en": "Weather favorable for current stage.",
        "message_ur": "موجودہ مرحلے کے لیے موسم سازگار ہے۔",
        "actions_en": ["Continue routine checks."],
        "actions_ur": ["معمول کی جانچ جاری رکھیں۔"],
    }
    risks = [
        RiskItem(
            type_key="diseaseRisk",
            level="LOW",
            message_en="No significant disease risk from current weather. Monitor if humidity rises.",
            message_ur="موجودہ موسم سے بیماری کا کوئی خاص خطرہ نہیں۔ نمی بڑھے تو نگرانی کریں۔",
            actions_en=["Monitor field for early symptoms.", "Keep humidity in check."],
            actions_ur=["ابتدائی علامات کے لیے کھیت کی نگرانی کریں۔", "نمی پر نظر رکھیں۔"],
        ),
        RiskItem(
            type_key="pestRisk",
            level="LOW",
            message_en="No elevated pest risk from current conditions. Standard scouting recommended.",
            message_ur="موجودہ حالات سے کیڑوں کا کوئی بڑھا ہوا خطرہ نہیں۔ معیاری جائزہ تجویز ہے۔",
            actions_en=["Place sticky traps.", "Monitor pest counts."],
            actions_ur=["چپکنے والے جال لگائیں۔", "کیڑوں کی گنتی پر نظر رکھیں۔"],
        ),
        RiskItem(
            type_key="climateRisk",
            level=climate_item["level"],
            message_en=climate_item["message_en"],
            message_ur=climate_item["message_ur"],
            actions_en=climate_item["actions_en"],
            actions_ur=climate_item["actions_ur"],
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
