
from fastapi import Request, Query
import sys
sys.path.append("e:/Python/GEN AI/Zarai Radar/RAG")
from fastapi import APIRouter, HTTPException, Depends
from App.schema.climate import ClimateData
from App.schema.climate_risk import RiskItem, WeatherSnapshot, ClimateRiskResponse
from App.routes.auth import get_current_user
from App.db import supabase
from App.services.climate import get_lat_lon_for_district, get_climate_data, get_weekly_weather
import asyncio
from App.data.climate_risk_rules import get_overall_level, LEVEL_ORDER
from App.data.fertilizer_recommendation import calculate_fertilizer_recommendation, format_for_dashboard
from App.data.irrigation import get_irrigation_advisory
from App.data.seasonal_guaidness import get_seasonal_guidance
from RAG.hybrib_assess import get_risk_assessment_hybrid

router = APIRouter(tags=['Dashboard'])


@router.get("/dashboard/climate")
async def get_climate_for_current_farmer(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    farmer = (
        supabase.table("farmer_info")
        .select("district, province")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not farmer.data:
        raise HTTPException(status_code=404, detail="No farmer profile found.")

    district = farmer.data[0].get("district")
    province = farmer.data[0].get("province") or ""
    lat, lon = get_lat_lon_for_district(district)

    records = await get_climate_data(lat, lon)
    return {
        "district": district,
        "province": province,
        "lat": lat,
        "lon": lon,
        "data": [r.dict() for r in records],
    }


@router.get("/dashboard/overview")
async def get_dashboard_overview(current_user: dict = Depends(get_current_user)):
    """
    Consolidated endpoint for all dashboard data.
    """
    user_id = current_user.get("id")
    
    # 1. Fetch Farmer Context (Sync Supabase)
    farmer_data = (
        supabase.table("farmer_info")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    
    if not farmer_data.data:
        raise HTTPException(status_code=404, detail="Farmer profile not found.")
    
    row = farmer_data.data[0]
    district = row.get("district")
    farmer_id = row.get("id")
    lat, lon = get_lat_lon_for_district(district)
    
    # 2. Fetch Weather Data (Async/Cached)
    # Parallelize current and weekly weather
    weather_tasks = [
        get_climate_data(lat, lon),
        get_weekly_weather(lat, lon)
    ]
    climate_records, weekly_weather = await asyncio.gather(*weather_tasks)
    
    current_weather = climate_records[0]
    weather_ctx = {
        "temp_c": current_weather.temp_c,
        "humidity": current_weather.humidity,
        "wind_kph": current_weather.wind_kph,
        "chance_of_rain": current_weather.chance_of_rain,
    }
    
    farmer_context = {
        **row,
        "farmer_id": farmer_id,
        "temp_c": current_weather.temp_c,
        "humidity": current_weather.humidity,
        "weather": weather_ctx,
        "days_after_sowing": row.get("days_after_sowing") or 0
    }
    # 3. Calculate Advisories
    irrigation_advisory = await get_irrigation_advisory(farmer_context)
    fert_recommendation = calculate_fertilizer_recommendation(farmer_context)
    fert_dashboard = format_for_dashboard(fert_recommendation, farmer_context)
    # Risk Assessment (Hybrid: Rules + RAG Potential)
    hybrid_res = get_risk_assessment_hybrid(farmer_context)
    # Map Hybrid Results to Dashboard ApiRiskItem format
    # 1. Disease Risk
    dr = hybrid_res["disease_risk"]
    disease_item = {
        "type_key": "diseaseRisk",
        "level": dr["level"],
        "message_en": ", ".join([d['name'] for d in dr['diseases']]) if dr["diseases"] else "No significant disease risks detected.",
        "message_ur": ", ".join([d['name'] for d in dr['diseases']]) if dr["diseases"] else "بیماریوں کا کوئی خاص خطرہ نہیں پایا گیا۔",
        "actions_en": [d["action"] for d in dr["diseases"]],
        "actions_ur": [],
        "details": [
            {
                "name": d["name"],
                "symptoms": d.get("symptoms", []),
                "management": d.get("management", {}),
                "severity": d.get("severity", "LOW")
            } for d in dr["diseases"]
        ]
    }
    
    # 2. Climate Risk
    cr = hybrid_res["climate_risk"]
    climate_item = {
        "type_key": "climateRisk",
        "level": cr["level"],
        "message_en": ", ".join([r['name'] for r in cr['risks']]) if cr["risks"] else "No significant climate risks detected.",
        "message_ur": "موسمیاتی صورتحال معمول کے مطابق ہے۔", 
        "actions_en": [r["action"] for r in cr["risks"]],
        "actions_ur": [],
        "details": [
            {
                "name": r["name"],
                "severity": r.get("severity", "LOW"),
                "management": r.get("management", []),
                "impact": r.get("impact", "")
            } for r in cr["risks"]
        ]
    }
    
    # 3. Pest Risk (Placeholder/Baseline)
    pest_item = {
        "type_key": "pestRisk",
        "level": "LOW",
        "message_en": "No significant pest risk detected.",
        "message_ur": "کیڑوں کا کوئی اہم خطرہ نہیں پایا گیا۔",
        "actions_en": [],
        "actions_ur": []
    }
    all_assessments = [disease_item, pest_item, climate_item]
    overall_risk = get_overall_level(all_assessments)
    seasonal = get_seasonal_guidance(row.get("crop", "Wheat"), district, row.get("province", "Punjab"))
    return {
        "profile": row,
        "weather": {
            "current": current_weather.dict(),
            "weekly": weekly_weather
        },
        "irrigation": irrigation_advisory,
        "fertilizer": fert_dashboard,
        "risk": {
            "overall": overall_risk,
            "assessments": all_assessments
        },
        "seasonal": seasonal
    }


@router.get("/dashboard/fertilizer-recommendation")
async def fertilizer_recommendation_api(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    farmer_data = (
        supabase.table("farmer_info")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not farmer_data.data:
        raise HTTPException(status_code=404, detail="No farmer profile found.")
    
    row = farmer_data.data[0]
    lat, lon = get_lat_lon_for_district(row["district"])
    records = await get_climate_data(lat, lon)
    
    current = records[0]
    farmer_context = {
        **row,
        "weather": {"temp_c": current.temp_c, "chance_of_rain": current.chance_of_rain}
    }
    
    recommendation = calculate_fertilizer_recommendation(farmer_context)
    return {"recommendation": format_for_dashboard(recommendation, farmer_context)}


@router.get("/dashboard/irrigation")
async def get_irrigation_advisory_api(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    farmer_data = (
        supabase.table("farmer_info")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not farmer_data.data:
        raise HTTPException(status_code=404, detail="No farmer profile found.")
    
    return await get_irrigation_advisory({**farmer_data.data[0], "farmer_id": user_id})


@router.get("/dashboard/profile")
async def get_farmer_profile(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    farmer_data = (
        supabase.table("farmer_info")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return farmer_data.data[0] if farmer_data.data else {}


@router.put("/dashboard/profile")
async def update_farmer_profile(request: Request, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    payload = await request.json()
    update_data = {}
    
    for field in ["district", "province", "crop", "stage", "irrigation_type", "soil_type"]:
        if field in payload:
            update_data[field] = payload[field]
            
    if "area" in payload:
        try:
            update_data["area"] = int(float(payload["area"]))
        except:
            pass

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided")

    result = supabase.table("farmer_info").update(update_data).eq("user_id", user_id).execute()
    return {"status": "success", "data": result.data[0] if result.data else {}}

