"""
ZaraiRadar - Fertilizer Optimization Engine
Calculates personalized fertilizer recommendations for farmers
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Load fertilizer knowledge base
with open('App/data/fertilizer_knowledge_base.json', 'r') as f:
    FERTILIZER_KB = json.load(f)


# ============================================================================
# WHEAT GROWTH STAGE FUNCTION
# ============================================================================

def get_wheat_stage(das):
    """
    Get wheat growth stage based on days after sowing
    Returns: (main_stage, sub_stage)
    """
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
# MAIN CALCULATION FUNCTIONS
# ============================================================================

def calculate_fertilizer_recommendation(farmer_data: Dict) -> Dict:
    """
    Main function to calculate complete fertilizer recommendation
    
    Args:
        farmer_data: {
            'crop': 'wheat',
            'variety': 'Faisalabad-2008',
            'field_size_acres': 10,
            'target_yield_maunds': 50,
            'soil_type': 'Loamy',
            'irrigation_type': 'canal',
            'province': 'Punjab',
            'district': 'Faisalabad',
            'sowing_date': '2025-11-10',
            'days_after_sowing': 45,
            'current_stage': 'Tillering',
            'weather': {
                'rainfall_forecast_7d': 15,
                'temperature_avg': 22
            }
        }
    
    Returns:
        Complete fertilizer recommendation with schedule and products
    """
    
    # Step 1: Get base requirements
    base_req = calculate_base_requirements(
        crop=farmer_data['crop'],
        field_size=farmer_data['area']
    )
    
    # Step 2: Adjust for soil and irrigation
    adjusted_req = adjust_for_soil_and_irrigation(
        base_requirements=base_req,
        soil_type=farmer_data['soil_type'],
        irrigation_type=farmer_data['irrigation_type']
    )
    
    # Step 3: Create application schedule
    schedule = create_application_schedule(
        total_requirements=adjusted_req,
        crop=farmer_data['crop'],
        days_after_sowing=farmer_data['days_after_sowing'],
        sowing_date=farmer_data['crop_start_date'],
        weather=farmer_data.get('weather', {})
    )
    
    # Step 4: Convert to products
    products = convert_to_products(schedule)
    
    # Step 5: Calculate costs
    costs = calculate_costs(products)
    
    # Step 6: Get tips and warnings
    tips = get_application_tips(farmer_data, schedule)
    
    return {
        "base_requirements": base_req,
        "adjusted_requirements": adjusted_req,
        "application_schedule": schedule,
        "products_needed": products,
        "cost_estimate": costs,
        "tips": tips,
        "generated_at": datetime.now().isoformat(),
        'area': farmer_data.get('area', 1.0)
    }


def calculate_base_requirements(crop: str, field_size: float) -> Dict:
    """
    Calculate base nutrient requirements
    """
    
    # Normalize crop name to lowercase for lookup
    crop_key = crop.lower()
    crop_data = next(
        (item for item in FERTILIZER_KB['fertilizer_recommendations'] if item['crop'].lower() == crop_key),
        None
    )
    if not crop_data:
        raise ValueError(f"Crop '{crop}' not found in knowledge base")
    
    base = crop_data['base_requirements']
    if crop == 'Wheat':
        target_yield = 35  # Default target yield in maunds per acre
    
    
    yield_difference = target_yield - base['base_yield_maunds_per_acre']

    base_N = base['nitrogen_N_kg_per_acre']
    base_P = base['phosphorus_P2O5_kg_per_acre']
    base_K = base['potassium_K2O_kg_per_acre']

    if yield_difference > 0:
        additional_N = (
            yield_difference / 10
        ) * base['additional_N_per_10_maunds_increase']

        adjusted_N = base_N + additional_N
    else:
        adjusted_N = base_N

    total_N = adjusted_N * field_size
    total_P = base_P * field_size
    total_K = base_K * field_size

    return {
        "per_acre": {
            "nitrogen_N_kg": round(adjusted_N, 1),
            "phosphorus_P2O5_kg": round(base_P, 1),
            "potassium_K2O_kg": round(base_K, 1)
        },
        "total_field": {
            "nitrogen_N_kg": round(total_N, 1),
            "phosphorus_P2O5_kg": round(total_P, 1),
            "potassium_K2O_kg": round(total_K, 1)
        },
        "field_size_acres": field_size,
        "target_yield_maunds_per_acre": target_yield
    }


def adjust_for_soil_and_irrigation(base_requirements: Dict, soil_type: str, irrigation_type: str) -> Dict:
    """
    Adjust fertilizer amounts based on soil type and irrigation
    """
    
    # Get crop data
    crop_data = FERTILIZER_KB['fertilizer_recommendations'][0]  # Wheat
    
    # Soil adjustments
    soil_adj = crop_data['soil_type_adjustments'].get(soil_type, {
        "nitrogen_multiplier": 1.0,
        "phosphorus_multiplier": 1.0,
        "potassium_multiplier": 1.0
    })
    
    # Irrigation adjustments
    irrigation_adj = crop_data['irrigation_adjustments'].get(irrigation_type, {
        "multiplier": 1.0
    })
    
    # Apply adjustments
    base_total = base_requirements['total_field']
    
    adjusted_N = base_total['nitrogen_N_kg'] * soil_adj['nitrogen_multiplier'] * irrigation_adj['multiplier']
    adjusted_P = base_total['phosphorus_P2O5_kg'] * soil_adj['phosphorus_multiplier']
    adjusted_K = base_total['potassium_K2O_kg'] * soil_adj['potassium_multiplier']
    
    return {
        "total_field": {
            "nitrogen_N_kg": round(adjusted_N, 1),
            "phosphorus_P2O5_kg": round(adjusted_P, 1),
            "potassium_K2O_kg": round(adjusted_K, 1)
        },
        "adjustments_applied": {
            "soil_type": soil_type,
            "soil_multipliers": soil_adj,
            "irrigation_type": irrigation_type,
            "irrigation_multiplier": irrigation_adj['multiplier']
        }
    }


def create_application_schedule(
    total_requirements: Dict,
    crop: str,
    days_after_sowing: int,
    sowing_date: str,
    weather: Dict
) -> List[Dict]:
    """
    Create stage-wise application schedule using accurate wheat growth stages
    """
    
    # Get current growth stage
    current_main_stage, current_sub_stage = get_wheat_stage(days_after_sowing)
    
    # Get split schedule from knowledge base
    crop_data = FERTILIZER_KB['fertilizer_recommendations'][0]  # Wheat
    split_schedule = crop_data['split_application_schedule']
    
    total_N = total_requirements['total_field']['nitrogen_N_kg']
    total_P = total_requirements['total_field']['phosphorus_P2O5_kg']
    total_K = total_requirements['total_field']['potassium_K2O_kg']
    
    sowing_date_obj = datetime.strptime(sowing_date, '%Y-%m-%d')
    
    applications = []
    
    for split in split_schedule:
        # Get target days (middle of range)
        days_range = split['days_range']
        days_target = (days_range[0] + days_range[1]) // 2
        
        # Calculate amounts for this application
        N_amount = total_N * (split['nitrogen_percent'] / 100)
        P_amount = total_P * (split['phosphorus_percent'] / 100)
        K_amount = total_K * (split['potassium_percent'] / 100)
        
        # Skip if nothing to apply
        if N_amount == 0 and P_amount == 0 and K_amount == 0:
            continue
        
        # Calculate application date
        application_date = sowing_date_obj + timedelta(days=days_target)
        days_remaining = days_target - days_after_sowing
        
        # Determine status based on current DAS vs application window
        if days_after_sowing > days_range[1]:
            # Past the application window
            status = "MISSED"
            urgency = "OVERDUE"
        elif days_after_sowing >= days_range[0] and days_after_sowing <= days_range[1]:
            # Within the application window
            status = "DUE_NOW"
            urgency = "IMMEDIATE"
        elif days_remaining <= 7:
            # Coming up soon (within 7 days)
            status = "UPCOMING"
            urgency = "WITHIN_WEEK"
        else:
            # Future application
            status = "FUTURE"
            urgency = "SCHEDULED"
        
        # Weather consideration
        weather_note = ""
        if weather.get('rainfall_forecast_7d', 0) > 30 and days_remaining <= 7:
            weather_note = "⚠️ Heavy rain forecast - consider delaying application by 2-3 days"
        elif weather.get('rainfall_forecast_7d', 0) > 50 and status == "DUE_NOW":
            weather_note = "⚠️ Very heavy rain forecast - DELAY application until after rain"
        
        # Add current stage indicator if this is the active application
        stage_match = ""
        if status == "DUE_NOW":
            stage_match = f"✓ Current crop stage: {current_sub_stage}"
        
        applications.append({
            "stage": split['stage'],
            "sub_stage": split['sub_stage'],
            "days_after_sowing": days_target,
            "days_range": days_range,
            "application_date": application_date.strftime('%Y-%m-%d'),
            "days_remaining": days_remaining,
            "status": status,
            "urgency": urgency,
            "nutrients": {
                "nitrogen_N_kg": round(N_amount, 1),
                "phosphorus_P2O5_kg": round(P_amount, 1),
                "potassium_K2O_kg": round(K_amount, 1)
            },
            "instructions": split['instructions'],
            "products_suggested": split['products'],
            "weather_note": weather_note,
            "importance": split.get('urgency_if_missed', 'MEDIUM'),
            "growth_indicators": split.get('growth_stage_indicators', []),
            "stage_match": stage_match,
            "timing_note": split.get('timing_note', '')
        })
    
    return applications


def convert_to_products(schedule: List[Dict]) -> List[Dict]:
    """
    Convert nutrient requirements to actual products (bags)
    """
    
    products_db = {p['product_name']: p for p in FERTILIZER_KB['fertilizer_products']}
    
    all_applications = []
    
    for application in schedule:
        nutrients = application['nutrients']
        N_needed = nutrients['nitrogen_N_kg']
        P_needed = nutrients['phosphorus_P2O5_kg']
        K_needed = nutrients['potassium_K2O_kg']
        
        products_this_stage = []
        
        # Strategy: Use DAP for P (also provides some N), then Urea for remaining N, then MOP for K
        
        # 1. Calculate DAP for phosphorus
        if P_needed > 0:
            DAP_data = products_db['DAP']
            DAP_P_percent = DAP_data['composition']['phosphorus_P2O5_percent'] / 100
            DAP_kg = P_needed / DAP_P_percent
            DAP_bags = DAP_kg / DAP_data['physical_properties']['kg_per_bag']
            
            # DAP also provides nitrogen
            N_from_DAP = DAP_kg * (DAP_data['composition']['nitrogen_N_percent'] / 100)
            
            products_this_stage.append({
                "product_name": "DAP",
                "full_name": DAP_data['common_name'],
                "bags": round(DAP_bags, 1),
                "kg": round(DAP_kg, 1),
                "provides": {
                    "nitrogen_N_kg": round(N_from_DAP, 1),
                    "phosphorus_P2O5_kg": round(P_needed, 1)
                },
                "cost_pkr": round(DAP_bags * DAP_data['pricing']['avg_price_pkr_per_bag'], 0)
            })
            
            N_needed -= N_from_DAP
        
        # 2. Calculate Urea for remaining nitrogen
        if N_needed > 0:
            Urea_data = products_db['Urea']
            Urea_N_percent = Urea_data['composition']['nitrogen_N_percent'] / 100
            Urea_kg = N_needed / Urea_N_percent
            Urea_bags = Urea_kg / Urea_data['physical_properties']['kg_per_bag']
            
            products_this_stage.append({
                "product_name": "Urea",
                "full_name": Urea_data['common_name'],
                "bags": round(Urea_bags, 1),
                "kg": round(Urea_kg, 1),
                "provides": {
                    "nitrogen_N_kg": round(N_needed, 1)
                },
                "cost_pkr": round(Urea_bags * Urea_data['pricing']['avg_price_pkr_per_bag'], 0)
            })
        
        # 3. Calculate Potash for potassium
        if K_needed > 0:
            MOP_data = products_db['MOP']
            MOP_K_percent = MOP_data['composition']['potassium_K2O_percent'] / 100
            MOP_kg = K_needed / MOP_K_percent
            MOP_bags = MOP_kg / MOP_data['physical_properties']['kg_per_bag']
            
            products_this_stage.append({
                "product_name": "MOP",
                "full_name": MOP_data['common_name'],
                "bags": round(MOP_bags, 1),
                "kg": round(MOP_kg, 1),
                "provides": {
                    "potassium_K2O_kg": round(K_needed, 1)
                },
                "cost_pkr": round(MOP_bags * MOP_data['pricing']['avg_price_pkr_per_bag'], 0)
            })
        
        all_applications.append({
            "stage": application['stage'],
            "status": application['status'],
            "days_remaining": application['days_remaining'],
            "products": products_this_stage
        })
    
    return all_applications


def calculate_costs(products: List[Dict]) -> Dict:
    """
    Calculate total costs
    """
    
    total_cost = 0
    cost_by_stage = {}
    cost_by_product = {}
    
    for application in products:
        stage_cost = 0
        
        for product in application['products']:
            cost = product['cost_pkr']
            stage_cost += cost
            total_cost += cost
            
            # Track by product
            product_name = product['product_name']
            if product_name not in cost_by_product:
                cost_by_product[product_name] = {
                    "bags": 0,
                    "cost": 0
                }
            cost_by_product[product_name]['bags'] += product['bags']
            cost_by_product[product_name]['cost'] += cost
        
        cost_by_stage[application['stage']] = stage_cost
    
    return {
        "total_cost_pkr": round(total_cost, 0),
        "cost_by_stage": cost_by_stage,
        "cost_by_product": cost_by_product
    }


def get_application_tips(farmer_data: Dict, schedule: List[Dict]) -> List[Dict]:
    """
    Get contextual tips and warnings
    """
    
    tips = []
    
    # 1. Add general tips from Knowledge Base
    for tip in FERTILIZER_KB['application_tips'][:2]:
        tips.append({
            "type": "general",
            "title": tip['tip'],
            "advice": tip['advice']
        })
    
    # 2. Add weather-based tips
    weather = farmer_data.get('weather', {})
    if weather.get('rainfall_forecast_7d', 0) > 30:
        tips.append({
            "type": "weather",
            "title": "Heavy rain forecast",
            "advice": "Delay fertilizer application until after rain to prevent nutrient leaching and waste"
        })
    
    # 3. Add soil-specific tips
    soil_type = farmer_data.get('soil_type')
    if soil_type == 'Sandy':
        tips.append({
            "type": "soil",
            "title": "Sandy soil detected",
            "advice": "Apply fertilizer in smaller doses more frequently to prevent leaching"
        })
    
    # 4. Add urgency warnings (DUE_NOW and MISSED)
    for application in schedule:
        if application['status'] == 'DUE_NOW':
            tips.insert(0, {  # Add at top
                "type": "urgent",
                "title": f"⚠️ {application['stage']} stage fertilizer DUE NOW",
                "advice": f"Apply within next 2-3 days for best results. {application['importance']}"
            })
        elif application['status'] == 'MISSED' and 'HIGH' in application['importance'].upper():
            tips.insert(0, {
                "type": "warning",
                "title": f"❗ MISSED {application['stage']} Application",
                "advice": f"You missed the critical {application['sub_stage']} application. Consult an expert immediately as this affects yield."
            })
    
    # 5. Flowering stage specific tip if no other urgent tips
    if not any(t['type'] in ['urgent', 'warning'] for t in tips):
        das = farmer_data.get('days_after_sowing', 0)
        main_stage, _ = get_wheat_stage(das)
        if main_stage == "Flowering":
            tips.append({
                "type": "general",
                "title": "Flowering Stage Monitoring",
                "advice": "Inspect for uniform heading. Avoid heavy irrigation during peak flowering to prevent lodging."
            })
            
    return tips


# ============================================================================
# DASHBOARD FORMATTING
# ============================================================================

def format_for_dashboard(recommendation: Dict, farmer_data: Dict) -> Dict:
    """
    Format fertilizer recommendation for dashboard display
    """
    
    schedule = recommendation['application_schedule']
    products = recommendation['products_needed']
    costs = recommendation['cost_estimate']
    
    # Find next application
    next_app = next(
        (app for app in schedule if app['status'] in ['DUE_NOW', 'UPCOMING']),
        None
    )
    
    # Summary of all products needed (season total)
    season_products = {}
    for app in products:
        for product in app['products']:
            name = product['product_name']
            if name not in season_products:
                season_products[name] = {
                    "bags": 0,
                    "cost": 0,
                    "full_name": product['full_name']
                }
            season_products[name]['bags'] += product['bags']
            season_products[name]['cost'] += product['cost_pkr']
    
    # Build next application info safely
    if next_app:
        next_application_info = {
            "stage": next_app['stage'],
            "sub_stage": next_app['sub_stage'],
            "status": next_app['status'],
            "days_remaining": next_app['days_remaining'],
            "days_range": f"Day {next_app['days_range'][0]}-{next_app['days_range'][1]}",
            "urgency": next_app['urgency'],
            "products": next((p for p in products if p['stage'] == next_app['stage']), {}).get('products', []),
            "instructions": next_app['instructions'],
            "weather_note": next_app.get('weather_note', ''),
            "stage_match": next_app.get('stage_match', ''),
            "growth_indicators": next_app.get('growth_indicators', []),
            "timing_note": next_app.get('timing_note', '')
        }
    else:
        # No upcoming applications
        next_application_info = {
            "stage": "All applications complete",
            "sub_stage": "Season Complete",
            "status": "COMPLETE",
            "days_remaining": 0,
            "days_range": "N/A",
            "urgency": "NONE",
            "products": [],
            "instructions": "All scheduled fertilizer applications have been completed for this season.",
            "weather_note": "",
            "stage_match": "",
            "growth_indicators": [],
            "timing_note": ""
        }
    
    return {
        "fertilizer_card": {
            "title": "💊 FERTILIZER RECOMMENDATION",
            "area": farmer_data.get('area', 1.0),
            "next_application": next_application_info,
            "upcoming_schedule": [
                {
                    "stage": app['stage'],
                    "sub_stage": app['sub_stage'],
                    "days_remaining": app['days_remaining'],
                    "days_range": f"Day {app['days_range'][0]}-{app['days_range'][1]}",
                    "date": app['application_date'],
                    "nutrients_summary": f"N: {app['nutrients']['nitrogen_N_kg']}kg, P: {app['nutrients']['phosphorus_P2O5_kg']}kg",
                    "timing_note": app.get('timing_note', '')
                }
                for app in schedule if app['status'] in ['UPCOMING', 'FUTURE']
            ][:3],
            "season_total": {
                "products": season_products,
                "total_cost": costs['total_cost_pkr']
            },
            "tips": recommendation['tips'][:3]
        }
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    
    # Example farmer data
    farmer_data = {
        'crop': 'wheat',
        'variety': 'general',
        'field_size_acres': 10,
        'target_yield_maunds': 50,
        'soil_type': 'Loamy',
        'irrigation_type': 'good_canal',
        'province': 'Punjab',
        'district': 'Faisalabad',
        'sowing_date': '2024-11-10',
        'days_after_sowing': 25,  # Changed to 25 to test Tillering stage
        'weather': {
            'rainfall_forecast_7d': 15,
            'temperature_avg': 22
        }
    }
    
    # Calculate current stage
    main_stage, sub_stage = get_wheat_stage(farmer_data['days_after_sowing'])
    farmer_data['current_stage'] = main_stage  # For compatibility
    
    print("=" * 70)
    print("ZARAIRADAR FERTILIZER OPTIMIZATION")
    print("=" * 70)
    print(f"\nCurrent Crop Status:")
    print(f"  Days After Sowing: {farmer_data['days_after_sowing']}")
    print(f"  Growth Stage: {main_stage} → {sub_stage}")
    print(f"  Target Yield: {farmer_data['target_yield_maunds']} maunds/acre")
    
    # Calculate recommendation
    recommendation = calculate_fertilizer_recommendation(farmer_data)
    
    # Format for dashboard
    dashboard = format_for_dashboard(recommendation)
    
    # Display
    fert_card = dashboard['fertilizer_card']
    
    print(f"\n{fert_card['title']}")
    print("-" * 70)
    
    # Next application
    next_app = fert_card['next_application']
    print(f"\n⚡ NEXT APPLICATION - {next_app['status']}")
    print(f"   Stage: {next_app['stage']} → {next_app['sub_stage']}")
    print(f"   Timing: {next_app['days_range']} after sowing")
    if next_app['days_remaining'] > 0:
        print(f"   Days Remaining: {next_app['days_remaining']}")
    if next_app['stage_match']:
        print(f"   {next_app['stage_match']}")
    if next_app['growth_indicators']:
        print(f"   Signs to Look For:")
        for indicator in next_app['growth_indicators'][:3]:
            print(f"      • {indicator}")
    print(f"\n   Products Needed:")
    for product in next_app['products']:
        print(f"      • {product['full_name']}: {product['bags']} bags ({product['kg']} kg)")
        print(f"        Cost: Rs. {product['cost_pkr']:,}")
    if next_app['weather_note']:
        print(f"\n   {next_app['weather_note']}")
    print(f"\n   Instructions: {next_app['instructions']}")
    if next_app['timing_note']:
        print(f"   Note: {next_app['timing_note']}")
    
    # Upcoming schedule
    if fert_card['upcoming_schedule']:
        print(f"\n📅 UPCOMING APPLICATIONS:")
        for upcoming in fert_card['upcoming_schedule']:
            print(f"   • {upcoming['stage']} → {upcoming['sub_stage']}")
            print(f"     {upcoming['days_range']} ({upcoming['days_remaining']} days remaining) - {upcoming['date']}")
            print(f"     {upcoming['nutrients_summary']}")
            if upcoming['timing_note']:
                print(f"     {upcoming['timing_note']}")
    
    # Season total
    print(f"\n💰 SEASON TOTAL:")
    season = fert_card['season_total']
    for product_name, details in season['products'].items():
        print(f"   • {details['full_name']}: {details['bags']:.1f} bags = Rs. {details['cost']:,}")
    print(f"   TOTAL COST: Rs. {season['total_cost']:,}")
    
    # Tips
    print(f"\n💡 TIPS:")
    for tip in fert_card['tips']:
        print(f"   • [{tip['type'].upper()}] {tip['title']}")
        print(f"     {tip['advice']}")
    
    print("\n" + "=" * 70)
    
    # JSON output
    print("\n📤 JSON FOR FRONTEND:")
    print(json.dumps(dashboard, indent=2))