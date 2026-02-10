
from datetime import datetime


def get_seasonal_guidance(crop: str, district: str, province: str) -> dict:
    """
    Generate seasonal guidance for optimal sowing window
    """
    
    # Seasonal data for wheat in different regions
    WHEAT_SOWING_WINDOWS = {
        "Punjab": {
            "optimal_start": "2024-11-01",
            "optimal_end": "2024-11-25",
            "sowing_window_start": "2024-10-25",
            "sowing_window_end": "2024-12-10",
            "season_type": "Rabi Season",
            "districts": {
                "Faisalabad": {
                    "optimal_dates": "Nov 1 - Nov 20",
                    "recommendation": "Ideal conditions with canal water availability"
                },
                "Multan": {
                    "optimal_dates": "Nov 5 - Nov 25",
                    "recommendation": "Optimal sowing window has passed. Consider early maturing varieties if planting now."
                },
                "Lahore": {
                    "optimal_dates": "Nov 1 - Nov 20",
                    "recommendation": "Good soil moisture and temperature conditions"
                }
            }
        },
        "Sindh": {
            "optimal_start": "2024-11-10",
            "optimal_end": "2024-12-05",
            # ... similar structure
        }
    }
    
    # Get region data
    region_data = WHEAT_SOWING_WINDOWS.get(province, {})
    district_data = region_data.get("districts", {}).get(district, {})
    
    # Calculate current status
    today = datetime.now().date()
    optimal_start = datetime.fromisoformat(region_data["optimal_start"]).date()
    optimal_end = datetime.fromisoformat(region_data["optimal_end"]).date()
    
    # Determine status
    if today < optimal_start:
        status = "upcoming"
        message = f"Optimal sowing starts in {(optimal_start - today).days} days"
    elif optimal_start <= today <= optimal_end:
        status = "optimal"
        message = "Currently in optimal sowing window"
    else:
        status = "passed"
        message = district_data.get("recommendation", "Optimal window has passed")
    
    # Generate monthly breakdown
    months_data = generate_monthly_status(
        optimal_start, 
        optimal_end,
        region_data["sowing_window_start"],
        region_data["sowing_window_end"]
    )
    
    return {
        "sowing_period": f"{optimal_start.strftime('%B')} - {optimal_end.strftime('%B')}",
        "optimal_dates": f"{optimal_start.strftime('%b %d')} - {optimal_end.strftime('%b %d')}",
        "season_type": region_data["season_type"],
        "status": status,
        "recommendation": message,
        "months": months_data,
        "district_specific": district_data
    }


def generate_monthly_status(optimal_start, optimal_end, window_start, window_end):
    """Generate status for each month"""
    
    months = []
    current_month = datetime.now().month
    
    for month_num in range(1, 13):
        month_name = datetime(2024, month_num, 1).strftime("%b")
        month_start = datetime(2024, month_num, 1).date()
        month_end = datetime(2024, month_num, 28).date()  # Simplified
        
        # Determine status
        if month_start >= datetime.fromisoformat(window_start).date() and month_end <= datetime.fromisoformat(window_end).date():
            if month_start >= optimal_start and month_end <= optimal_end:
                status = "optimal"  # Dark green
            else:
                status = "sowing_window"  # Light green
        else:
            status = "off_season"  # Gray
        
        # Check if completed
        is_completed = month_num < current_month
        is_current = month_num == current_month
        
        months.append({
            "month": month_name,
            "status": status,
            "is_completed": is_completed,
            "is_current": is_current
        })
    
    return months