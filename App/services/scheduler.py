"""
ZaraiRadar - Daily Scheduler
Run this file once per day (via cron/scheduled task) to:
1. Update crop stages for all farmers
2. Fetch and log weather/rainfall data
3. Generate irrigation advisories
4. Check fertilizer schedules
5. Send notifications to farmers
6. Auto-complete harvested crops
"""

import os
import json
from datetime import datetime, timedelta
from supabase import create_client
import requests
from typing import List, Dict, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# District coordinates for weather API
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


# ============================================================================
# WHEAT GROWTH STAGE FUNCTION
# ============================================================================

def get_wheat_stage(das: int) -> tuple:
    """Get wheat growth stage based on days after sowing"""
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


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_active_crops() -> List[Dict]:
    """Get all active crops (either by status or by date threshold)"""
    try:
        # Option 1: If you have status column
        response = (
            supabase.table("farmer_info")
            .select("*")
            .eq("status", "active")
            .execute()
        )
        return response.data
    except:
        # Option 2: Fallback - get crops from last 150 days
        cutoff_date = (datetime.now().date() - timedelta(days=150)).isoformat()
        response = (
            supabase.table("farmer_info")
            .select("*")
            .gte("sowing_date", cutoff_date)
            .execute()
        )
        
        # Filter by DAS < 130 (not harvested)
        active_crops = []
        for crop in response.data:
            das = calculate_das(crop["sowing_date"])
            if das < 130:
                active_crops.append(crop)
        
        return active_crops


def calculate_das(sowing_date: str) -> int:
    """Calculate days after sowing"""
    sowing = datetime.fromisoformat(sowing_date).date()
    today = datetime.now().date()
    return (today - sowing).days


def get_weather_for_district(district: str) -> Dict:
    """Fetch current weather from Open-Meteo API"""
    
    coords = DISTRICT_COORDINATES.get(district)
    if not coords:
        print(f"⚠️ Unknown district: {district}")
        return None
    
    lat, lon = coords
    
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m"],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "relative_humidity_2m_mean"
            ],
            "timezone": "auto",
            "forecast_days": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "temp_current": data["current"]["temperature_2m"],
            "temp_max": data["daily"]["temperature_2m_max"][0],
            "temp_min": data["daily"]["temperature_2m_min"][0],
            "humidity": data["daily"]["relative_humidity_2m_mean"][0],
            "rain_mm": data["daily"]["precipitation_sum"][0] or 0,
            "date": data["daily"]["time"][0]
        }
    
    except Exception as e:
        print(f"❌ Error fetching weather for {district}: {e}")
        return None


# ============================================================================
# TASK 1: UPDATE CROP STAGES
# ============================================================================

def update_all_crop_stages():
    """Update current stage and sub_stage for all active crops"""
    
    print("\n" + "="*70)
    print("📊 TASK 1: Updating Crop Stages")
    print("="*70)
    
    active_crops = get_active_crops()
    updated_count = 0
    
    for crop in active_crops:
        das = calculate_das(crop["sowing_date"])
        main_stage, sub_stage = get_wheat_stage(das)
        
        # Update in database
        try:
            supabase.table("farmer_info").update({
                "current_stage": main_stage,
                "current_sub_stage": sub_stage,
                "days_since_sowing": das,
                "last_updated": datetime.now().isoformat()
            }).eq("id", crop["id"]).execute()
            
            print(f"✓ Updated Crop #{crop['id']} - DAS: {das}, Stage: {main_stage} → {sub_stage}")
            updated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to update Crop #{crop['id']}: {e}")
    
    print(f"\n✅ Updated {updated_count}/{len(active_crops)} crops")
    return updated_count


# ============================================================================
# TASK 2: LOG RAINFALL DATA
# ============================================================================

def log_daily_rainfall():
    """Fetch weather and log rainfall for all active crops"""
    
    print("\n" + "="*70)
    print("🌧️ TASK 2: Logging Rainfall Data")
    print("="*70)
    
    active_crops = get_active_crops()
    logged_count = 0
    
    # Group crops by district to minimize API calls
    crops_by_district = {}
    for crop in active_crops:
        district = crop["district"]
        if district not in crops_by_district:
            crops_by_district[district] = []
        crops_by_district[district].append(crop)
    
    # Fetch weather once per district
    for district, crops in crops_by_district.items():
        weather = get_weather_for_district(district)
        
        if not weather:
            continue
        
        print(f"\n📍 {district}: {weather['rain_mm']}mm rain, {weather['temp_max']:.1f}°C")
        
        # Log for each crop in this district
        for crop in crops:
            das = calculate_das(crop["sowing_date"])
            main_stage, sub_stage = get_wheat_stage(das)
            
            # Only log if there was rain
            if weather["rain_mm"] > 0:
                try:
                    supabase.table("irrigation_logs").insert({
                        "farmer_id": crop["farmer_id"],
                        "crop_id": crop["id"],
                        "event_type": "rainfall",
                        "amount_mm": weather["rain_mm"],
                        "event_date": weather["date"],
                        "days_after_sowing": das,
                        "stage": main_stage,
                        "sub_stage": sub_stage
                    }).execute()
                    
                    logged_count += 1
                    print(f"  ✓ Logged {weather['rain_mm']}mm for Crop #{crop['id']}")
                    
                except Exception as e:
                    print(f"  ❌ Failed to log for Crop #{crop['id']}: {e}")
            
            # Also update weather in farmer_info for quick access
            try:
                supabase.table("farmer_info").update({
                    "last_weather_update": datetime.now().isoformat(),
                    "current_temperature": weather["temp_current"],
                    "current_humidity": weather["humidity"]
                }).eq("id", crop["id"]).execute()
            except:
                pass
    
    print(f"\n✅ Logged rainfall for {logged_count} crops")
    return logged_count


# ============================================================================
# TASK 3: CHECK FERTILIZER SCHEDULE
# ============================================================================

def check_fertilizer_schedules():
    """Check if any crops need fertilizer application soon"""
    
    print("\n" + "="*70)
    print("💊 TASK 3: Checking Fertilizer Schedules")
    print("="*70)
    
    active_crops = get_active_crops()
    
    # Fertilizer application windows (DAS ranges)
    FERTILIZER_WINDOWS = {
        "Sowing": (0, 14),
        "Tillering": (15, 35),
        "Jointing": (36, 55)
    }
    
    due_notifications = []
    upcoming_notifications = []
    
    for crop in active_crops:
        das = calculate_das(crop["sowing_date"])
        
        for stage, (start, end) in FERTILIZER_WINDOWS.items():
            # Check if in application window
            if start <= das <= end:
                due_notifications.append({
                    "crop_id": crop["id"],
                    "farmer_id": crop["farmer_id"],
                    "stage": stage,
                    "das": das,
                    "status": "DUE_NOW",
                    "message": f"Fertilizer application due for {stage} stage"
                })
                print(f"⚡ Crop #{crop['id']} - {stage} fertilizer DUE NOW (DAS {das})")
            
            # Check if coming up in 3 days
            elif start - 3 <= das < start:
                upcoming_notifications.append({
                    "crop_id": crop["id"],
                    "farmer_id": crop["farmer_id"],
                    "stage": stage,
                    "das": das,
                    "days_remaining": start - das,
                    "status": "UPCOMING",
                    "message": f"Fertilizer needed in {start - das} days"
                })
                print(f"📅 Crop #{crop['id']} - {stage} fertilizer in {start - das} days")
    
    print(f"\n✅ Found {len(due_notifications)} due + {len(upcoming_notifications)} upcoming")
    
    return {
        "due": due_notifications,
        "upcoming": upcoming_notifications
    }


# ============================================================================
# TASK 4: CHECK IRRIGATION NEEDS
# ============================================================================

def check_irrigation_needs():
    """Check which crops need irrigation based on last irrigation date"""
    
    print("\n" + "="*70)
    print("💧 TASK 4: Checking Irrigation Needs")
    print("="*70)
    
    active_crops = get_active_crops()
    irrigation_alerts = []
    
    for crop in active_crops:
        das = calculate_das(crop["sowing_date"])
        main_stage, sub_stage = get_wheat_stage(das)
        
        # Get last irrigation date
        last_irrigation = (
            supabase.table("irrigation_logs")
            .select("event_date")
            .eq("crop_id", crop["id"])
            .eq("event_type", "irrigation")
            .order("event_date", desc=True)
            .limit(1)
            .execute()
        )
        
        if last_irrigation.data:
            last_date = datetime.fromisoformat(last_irrigation.data[0]["event_date"]).date()
            days_since = (datetime.now().date() - last_date).days
        else:
            # No irrigation logged, use sowing date
            days_since = das
        
        # Critical substages needing water
        CRITICAL_SUBSTAGES = ["Tillering", "Booting", "Heading", "Anthesis"]
        
        # Alert if no irrigation in 7+ days and in critical stage
        if days_since >= 7 and sub_stage in CRITICAL_SUBSTAGES:
            irrigation_alerts.append({
                "crop_id": crop["id"],
                "farmer_id": crop["farmer_id"],
                "das": das,
                "stage": main_stage,
                "sub_stage": sub_stage,
                "days_since_irrigation": days_since,
                "priority": "HIGH",
                "message": f"Irrigation needed - {days_since} days since last watering"
            })
            print(f"⚠️ Crop #{crop['id']} - {sub_stage} stage, {days_since} days without water")
    
    print(f"\n✅ Found {len(irrigation_alerts)} irrigation alerts")
    return irrigation_alerts


# ============================================================================
# TASK 5: AUTO-COMPLETE HARVESTED CROPS
# ============================================================================

def auto_complete_harvested_crops():
    """Mark crops as completed if DAS > 130 (wheat harvest threshold)"""
    
    print("\n" + "="*70)
    print("🌾 TASK 5: Auto-Completing Harvested Crops")
    print("="*70)
    
    active_crops = get_active_crops()
    completed_count = 0
    
    for crop in active_crops:
        das = calculate_das(crop["sowing_date"])
        
        # Wheat typically harvested at 125-135 DAS
        if das >= 130:
            try:
                supabase.table("farmer_info").update({
                    "status": "completed",
                    "harvest_date": datetime.now().date().isoformat(),
                    "final_das": das
                }).eq("id", crop["id"]).execute()
                
                print(f"✓ Marked Crop #{crop['id']} as completed (DAS {das})")
                completed_count += 1
                
            except Exception as e:
                print(f"❌ Failed to complete Crop #{crop['id']}: {e}")
    
    print(f"\n✅ Auto-completed {completed_count} crops")
    return completed_count


# ============================================================================
# TASK 6: GENERATE NOTIFICATIONS
# ============================================================================

def generate_farmer_notifications():
    """Create notifications to be sent to farmers"""
    
    print("\n" + "="*70)
    print("🔔 TASK 6: Generating Notifications")
    print("="*70)
    
    # Get all alerts from previous tasks
    fertilizer_alerts = check_fertilizer_schedules()
    irrigation_alerts = check_irrigation_needs()
    
    all_notifications = []
    
    # Fertilizer notifications
    for alert in fertilizer_alerts["due"]:
        notification = {
            "farmer_id": alert["farmer_id"],
            "crop_id": alert["crop_id"],
            "type": "fertilizer_due",
            "priority": "HIGH",
            "title": f"⚡ Fertilizer Application Due",
            "message": f"Apply {alert['stage']} stage fertilizer today (Day {alert['das']})",
            "action_required": True,
            "created_at": datetime.now().isoformat()
        }
        all_notifications.append(notification)
    
    for alert in fertilizer_alerts["upcoming"]:
        notification = {
            "farmer_id": alert["farmer_id"],
            "crop_id": alert["crop_id"],
            "type": "fertilizer_upcoming",
            "priority": "MEDIUM",
            "title": f"📅 Upcoming Fertilizer",
            "message": f"Prepare fertilizer for {alert['stage']} stage in {alert['days_remaining']} days",
            "action_required": False,
            "created_at": datetime.now().isoformat()
        }
        all_notifications.append(notification)
    
    # Irrigation notifications
    for alert in irrigation_alerts:
        notification = {
            "farmer_id": alert["farmer_id"],
            "crop_id": alert["crop_id"],
            "type": "irrigation_needed",
            "priority": "HIGH" if alert["priority"] == "HIGH" else "MEDIUM",
            "title": f"💧 Irrigation Needed",
            "message": f"Crop at {alert['sub_stage']} stage needs water ({alert['days_since_irrigation']} days dry)",
            "action_required": True,
            "created_at": datetime.now().isoformat()
        }
        all_notifications.append(notification)
    
    # Save to database (optional - create notifications table)
    for notification in all_notifications:
        try:
            supabase.table("notifications").insert(notification).execute()
        except:
            # If notifications table doesn't exist, just print
            print(f"  📬 Notification for Farmer #{notification['farmer_id']}: {notification['title']}")
    
    print(f"\n✅ Generated {len(all_notifications)} notifications")
    return all_notifications


# ============================================================================
# TASK 7: CLEANUP OLD DATA
# ============================================================================

def cleanup_old_data():
    """Archive/delete old completed crops and logs"""
    
    print("\n" + "="*70)
    print("🗑️ TASK 7: Cleaning Up Old Data")
    print("="*70)
    
    # Delete irrigation logs older than 6 months
    six_months_ago = (datetime.now().date() - timedelta(days=180)).isoformat()
    
    try:
        deleted = (
            supabase.table("irrigation_logs")
            .delete()
            .lt("event_date", six_months_ago)
            .execute()
        )
        print(f"✓ Deleted old irrigation logs (before {six_months_ago})")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    
    # Mark old completed crops as archived
    try:
        archived = (
            supabase.table("farmer_info")
            .update({"status": "archived"})
            .eq("status", "completed")
            .lt("harvest_date", six_months_ago)
            .execute()
        )
        print(f"✓ Archived old completed crops")
    except:
        pass
    
    print("\n✅ Cleanup complete")


# ============================================================================
# MAIN SCHEDULER FUNCTION
# ============================================================================

def run_daily_tasks():
    """Main function - run all daily tasks"""
    
    print("\n" + "="*70)
    print("🌾 ZARAIRADAR DAILY SCHEDULER")
    print(f"⏰ Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        # Task 1: Update crop stages
        update_all_crop_stages()
        
        # Task 2: Log rainfall
        log_daily_rainfall()
        
        # Task 3: Check fertilizer schedules
        check_fertilizer_schedules()
        
        # Task 4: Check irrigation needs
        check_irrigation_needs()
        
        # Task 5: Auto-complete harvested crops
        auto_complete_harvested_crops()
        
        # Task 6: Generate notifications
        generate_farmer_notifications()
        
        # Task 7: Cleanup old data (run once per week)
        if datetime.now().weekday() == 0:  # Monday
            cleanup_old_data()
        
        # Log success
        print("\n" + "="*70)
        print("✅ ALL TASKS COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        
        # Save run log
        try:
            supabase.table("scheduler_logs").insert({
                "run_date": datetime.now().date().isoformat(),
                "run_time": datetime.now().time().isoformat(),
                "status": "success",
                "tasks_completed": 7
            }).execute()
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"\n❌ SCHEDULER FAILED: {e}")
        
        # Log failure
        try:
            supabase.table("scheduler_logs").insert({
                "run_date": datetime.now().date().isoformat(),
                "run_time": datetime.now().time().isoformat(),
                "status": "failed",
                "error_message": str(e)
            }).execute()
        except:
            pass
        
        return False


# ============================================================================
# RUN IMMEDIATELY (For Testing)
# ============================================================================

if __name__ == "__main__":
    run_daily_tasks()