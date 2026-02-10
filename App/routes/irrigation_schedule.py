from datetime import datetime, timedelta
from App.services.database import supabase
from App.data.irrigation import get_lat_lon_for_district, get_daily_weather




def auto_log_rainfall_for_all_farmers():
    """Run this daily via cron/scheduler"""
    
    # Get all active crops
    active_crops = supabase.table("farmer_info").select("*").eq("status", "active").execute()
    
    for crop in active_crops.data:
        # Get weather for farmer's district
        lat, lon = get_lat_lon_for_district(crop["district"])
        weather = get_daily_weather(lat, lon)
        
        if weather["rain_mm"] > 0:
            supabase.table("irrigation_logs").insert({
                "farmer_id": crop["farmer_id"],
                "crop_id": crop["id"],
                "event_type": "rainfall",
                "amount_mm": weather["rain_mm"],
                "event_date": datetime.now().date(),
                "days_after_sowing": crop["days_since_sowing"],
                "stage": crop["current_stage"],
                "sub_stage": crop["current_sub_stage"]
            }).execute()