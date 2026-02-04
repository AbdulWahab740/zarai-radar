from disease_vec import search_disease_vec_with_similarity
from risk_assess import generate_risk_assessment_insights , format_for_dashboard, get_fallback_insights
from typing import List, Dict, Any


def complete_risk_assessment(farmer_context):
    """
    Complete end-to-end risk assessment workflow
    
    Args:
        farmer_context: Dict with crop, location, stage, weather data
    
    Returns:
        Dashboard-ready risk assessment data
    """
    
    print("=" * 60)
    print("🌾 ZARAIRADAR RISK ASSESSMENT")
    print("=" * 60)
    
    # Step 1: Build enhanced query
    print("\n[1/4] Building query...")
    enhanced_query = f"""
    Crop: {farmer_context['crop']}
    Location: {farmer_context['district']}, {farmer_context['province']}
    Growth Stage: {farmer_context['stage']}
    Days Since Sowing: {farmer_context['days_since_sowing']}
    Temperature: {farmer_context['temp']}°C
    Humidity: {farmer_context['humidity']}%

    What diseases and climate risks should this farmer watch for right now?
    """
    
    # Step 2: Search vector database
    print("[2/4] Searching knowledge base...")
    results = search_disease_vec_with_similarity(enhanced_query, farmer_context, limit=5)
    
    if not results:
        print("❌ No relevant documents found")
        return format_for_dashboard(get_fallback_insights())
    
    print(f"✓ Found {len(results)} relevant documents")
    
    # Step 3: Generate insights with LLM
    print("[3/4] Generating insights with AI...")
    insights = generate_risk_assessment_insights(results, farmer_context)
    
    # Step 4: Format for dashboard
    print("[4/4] Formatting for dashboard...")
    dashboard_data = format_for_dashboard(insights)
    
    print("\n✓ Risk assessment complete!")
    print("=" * 60)
    
    return dashboard_data


def display_dashboard(dashboard_data):
    """
    Pretty print dashboard data for CLI
    """
    
    print("\n" + "=" * 60)
    print("📊 DASHBOARD OUTPUT")
    print("=" * 60)
    
    # Summary
    summary = dashboard_data['summary']
    print(f"\n📋 SUMMARY")
    print(f"   {summary['message']}")
    
    if summary['priority_actions']:
        print(f"\n   🎯 Priority Actions:")
        for i, action in enumerate(summary['priority_actions'], 1):
            print(f"      {i}. {action}")
    
    # Disease Risk
    disease_card = dashboard_data['disease_card']
    print(f"\n{disease_card['icon']} DISEASE RISK: {disease_card['level']}")
    print(f"   Confidence: {disease_card['confidence']:.0%}")
    
    if disease_card['diseases']:
        for disease in disease_card['diseases']:
            print(f"\n   • {disease['name']} [{disease['risk_badge']}]")
            print(f"     Why: {disease['description']}")
            if disease['triggers']:
                print(f"     Triggers: {', '.join(disease['triggers'])}")
            print(f"     Action: {disease['treatment']}")
    else:
        print("   ✓ No significant disease risks detected")
    
    # Climate Risk
    climate_card = dashboard_data['climate_card']
    print(f"\n{climate_card['icon']} CLIMATE RISK: {climate_card['level']}")
    print(f"   Confidence: {climate_card['confidence']:.0%}")
    
    if climate_card['alerts']:
        for alert in climate_card['alerts']:
            print(f"\n   {alert['severity_icon']} {alert['name']} [{alert['severity']}]")
            print(f"     Impact: {alert['impact']}")
            if alert['triggers']:
                print(f"     Triggers: {', '.join(alert['triggers'])}")
            print(f"     Action: {alert['action']}")
    else:
        print("   ✓ No significant climate risks detected")
    
    print("\n" + "=" * 60)
if __name__ == "__main__":
    
    # Test context - same as yours
    test_context = {
        'crop': 'wheat',
        'province': 'Punjab',
        'district': 'Faisalabad',
        'stage': 'Sowing',
        'days_since_sowing': 45,
        'temp': 22,
        'humidity': 85
    }
    
    # Run complete assessment
    dashboard_data = complete_risk_assessment(test_context)
    
    # Display results
    print("\n📋 DISPLAYING DASHBOARD:"
          )
    print(dashboard_data)
    # Print JSON for frontend
    print("\n📤 JSON OUTPUT FOR FRONTEND:")
    import json
    print(json.dumps(dashboard_data, indent=2))