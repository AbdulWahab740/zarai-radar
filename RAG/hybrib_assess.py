"""
ZaraiRadar - Hybrid Risk Assessment System
Combines rule-based filtering with RAG for accurate disease/climate risk detection
"""

import json
from typing import List, Dict, Any

# Load knowledge base
with open('RAG/data/wheat_knowledge_base.json', 'r') as f:
    KNOWLEDGE_BASE = json.load(f)


# ============================================================================
# RULE-BASED DISEASE MATCHING
# ============================================================================

def match_diseases_by_conditions(
    farmer_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Rule-based matching: Find diseases that match current weather conditions
    Returns list of diseases with risk scores
    """
    
    temp = farmer_context['temp_c']
    humidity = farmer_context['humidity']
    stage = farmer_context['stage']
    days_after_sowing = farmer_context['days_after_sowing']
    
    matched_diseases = []
    
    for disease in KNOWLEDGE_BASE['wheat_diseases']:
        # Check if disease affects current stage
        if stage not in disease['affected_stages']:
            continue
        
        # Check if within vulnerable days range
        das_range = disease['vulnerable_days_after_sowing']
        if not (das_range[0] <= days_after_sowing <= das_range[1]):
            continue
        
        # Check weather conditions match
        conditions = disease['favorable_conditions']
        
        # Temperature match score (0-100)
        temp_score = 0
        if conditions['temperature_min'] <= temp <= conditions['temperature_max']:
            # Perfect match - closer to optimal temp = higher score
            temp_optimal = conditions['temperature_optimal']
            temp_range = conditions['temperature_max'] - conditions['temperature_min']
            deviation = abs(temp - temp_optimal)
            temp_score = max(0, 100 - (deviation / temp_range * 100))
        else:
            # Outside range - give 0
            temp_score = 0
        
        # Humidity match score (0-100)
        humidity_score = 0
        if humidity >= conditions['humidity_min']:
            # Higher humidity = higher score (up to 100% humidity)
            humidity_excess = humidity - conditions['humidity_min']
            humidity_score = min(100, 60 + humidity_excess)
        else:
            # Below minimum - severe penalty
            deficit = conditions['humidity_min'] - humidity
            # Each 10% below minimum = -20 points
            humidity_score = max(0, 50 - (deficit * 2))
        
        # Overall risk score (weighted average)
        overall_score = (temp_score * 0.5) + (humidity_score * 0.5)
        
        # Only include if BOTH conditions have reasonable match
        # AND overall score > 50 (realistic risk)
        if overall_score >= 50 and temp_score >= 30 and humidity_score >= 30:
            matched_diseases.append({
                'disease_name': disease['disease_name'],
                'disease_id': disease['disease_id'],
                'risk_score': round(overall_score, 1),
                'temp_match': temp_score,
                'humidity_match': humidity_score,
                'conditions_met': {
                    'temperature': f"{temp}°C (required: {conditions['temperature_min']}-{conditions['temperature_max']}°C) ✓",
                    'humidity': f"{humidity}% (required: ≥{conditions['humidity_min']}%) {'✓' if humidity >= conditions['humidity_min'] else '✗'}",
                    'stage': stage,
                    'das': days_after_sowing
                },
                'triggers': disease['climate_triggers'],
                'symptoms': disease['symptoms'],
                'management': disease['management'],
                'severity': 'HIGH' if overall_score >= 70 else 'MEDIUM' if overall_score >= 40 else 'LOW',
                'impact_details': disease['severity_impact'],
                'source': disease['source']
            })
    
    # Sort by risk score descending
    matched_diseases.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return matched_diseases


def match_climate_risks_by_conditions(
    farmer_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Rule-based matching: Find climate risks based on current conditions
    """
    
    temp = farmer_context['temp_c']
    stage = farmer_context['stage']
    days_after_sowing = farmer_context['days_after_sowing']
    
    matched_risks = []
    
    for risk in KNOWLEDGE_BASE['climate_risk_factors']:
        # Check if risk affects current stage
        if stage not in risk['affected_stages']:
            continue
        
        # Check if within critical days range
        das_range = risk['critical_days_after_sowing']
        if not (das_range[0] <= days_after_sowing <= das_range[1]):
            continue
        
        # Check trigger conditions
        triggers = risk['trigger_conditions']
        risk_score = 0
        triggered = False
        
        # Temperature-based risks
        if 'temperature_threshold' in triggers:
            threshold = triggers['temperature_threshold']
            
            # Determine if it's a heat risk (temp > threshold) or cold risk (temp < threshold)
            # Frost/cold risks have thresholds < 10°C
            is_cold_risk = threshold < 10
            
            if is_cold_risk:
                # Cold/frost risk - trigger if temp BELOW threshold
                if temp <= threshold:
                    # How much below threshold?
                    deficit = threshold - temp
                    risk_score = min(100, 60 + (deficit * 10))
                    triggered = True
                else:
                    # Well above threshold - no risk
                    risk_score = 0
            else:
                # Heat risk - trigger if temp ABOVE threshold
                if temp >= threshold:
                    # How much over threshold?
                    excess = temp - threshold
                    risk_score = min(100, 60 + (excess * 10))
                    triggered = True
                else:
                    # Below threshold - no risk
                    risk_score = 0
        
        # Only add if actually triggered
        if triggered and risk_score >= 50:
            matched_risks.append({
                'risk_name': risk['risk_name'],
                'risk_id': risk['risk_id'],
                'risk_score': round(risk_score, 1),
                'triggers_met': risk['climate_indicators'],
                'impact': risk['impact'],
                'management': risk['management_recommendations'],
                'severity': 'HIGH' if risk_score > 70 else 'MEDIUM',
                'source': risk['source']
            })
    
    # Sort by risk score
    matched_risks.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return matched_risks


# ============================================================================
# ENHANCED RAG WITH RULE-BASED FILTERING
# ============================================================================

def get_risk_assessment_hybrid(
    farmer_context: Dict[str, Any],
    rag_results: List[tuple] = None
) -> Dict[str, Any]:
    """
    Hybrid approach: Use rules first, then enhance with RAG
    """
    
    # Step 1: Rule-based matching (FAST & ACCURATE)
    rule_based_diseases = match_diseases_by_conditions(farmer_context)
    rule_based_climate = match_climate_risks_by_conditions(farmer_context)
    
    # Step 2: Use RAG for context (Semantic Knowledge)
    rag_context = []
    if rag_results:
        rag_context = [
            {"content": r[0], "score": r[1], "id": idx} 
            for idx, r in enumerate(rag_results)
        ]
    
    # Determine overall risk levels
    disease_risk_level = "LOW"
    if rule_based_diseases:
        max_score = rule_based_diseases[0]['risk_score']
        if max_score >= 70:
            disease_risk_level = "HIGH"
        elif max_score >= 40:
            disease_risk_level = "MEDIUM"
    
    climate_risk_level = "LOW"
    if rule_based_climate:
        max_score = rule_based_climate[0]['risk_score']
        if max_score >= 70:
            climate_risk_level = "HIGH"
        elif max_score >= 40:
            climate_risk_level = "MEDIUM"
    
    return {
        "disease_risk": {
            "level": disease_risk_level,
            "confidence": rule_based_diseases[0]['risk_score'] / 100 if rule_based_diseases else 0.0,
            "diseases": [
                {
                    "name": d['disease_name'],
                    "risk": "HIGH" if d['risk_score'] >= 70 else "MEDIUM" if d['risk_score'] >= 40 else "LOW",
                    "score": d['risk_score'],
                    "reason": f"Temperature {d['conditions_met']['temperature']} and humidity {d['conditions_met']['humidity']} match ideal conditions",
                    "triggers": d['triggers'][:3],
                    "action": get_treatment_summary(d['management']),
                    "symptoms": d['symptoms'],
                    "management": d['management'],
                    "severity": d['severity']
                }
                for d in rule_based_diseases[:3]  # Top 3
            ]
        },
        "climate_risk": {
            "level": climate_risk_level,
            "confidence": rule_based_climate[0]['risk_score'] / 100 if rule_based_climate else 0.0,
            "risks": [
                {
                    "name": r['risk_name'],
                    "severity": r['severity'],
                    "impact": r['impact'] if isinstance(r['impact'], str) else r['impact'].get('yield_reduction', 'High'),
                    "triggers": r['triggers_met'][:3],
                    "action": r['management'][0] if r['management'] else "Monitor conditions",
                    "management": r['management']
                }
                for r in rule_based_climate[:2]  # Top 2
            ]
        },
        "rag_context": rag_context,
        "priority_actions": generate_priority_actions(rule_based_diseases, rule_based_climate),
        "summary": generate_summary(rule_based_diseases, rule_based_climate, farmer_context)
    }


def get_treatment_summary(management: Dict) -> str:
    """Extract key treatment from management dict"""
    if management.get('chemical_control'):
        return management['chemical_control'][0]  # First recommendation
    return "Monitor crop regularly"


def generate_priority_actions(diseases: List, climate_risks: List) -> List[str]:
    """Generate top 2-3 priority actions"""
    actions = []
    
    # Disease actions
    if diseases and diseases[0]['risk_score'] >= 60:
        disease = diseases[0]
        if disease['management'].get('chemical_control'):
            actions.append(disease['management']['chemical_control'][0])
    
    # Climate actions
    if climate_risks and climate_risks[0]['risk_score'] >= 60:
        risk = climate_risks[0]
        if risk['management']:
            actions.append(risk['management'][0])
    
    # Default monitoring if no urgent actions
    if not actions:
        actions.append("Continue regular crop monitoring")
    
    return actions[:3]


def generate_summary(diseases: List, climate_risks: List, context: Dict) -> str:
    """Generate one-sentence summary"""
    
    if not diseases and not climate_risks:
        return "No significant disease or climate risks detected at current conditions"
    
    if diseases and diseases[0]['risk_score'] >= 70:
        return f"High risk of {diseases[0]['disease_name']} due to favorable weather conditions - immediate action recommended"
    
    if climate_risks and climate_risks[0]['risk_score'] >= 70:
        return f"High {climate_risks[0]['risk_name']} risk - take protective measures"
    
    if diseases:
        return f"Moderate risk of {diseases[0]['disease_name']} - monitor crop closely"
    
    return "Monitor weather conditions and crop health regularly"


# ============================================================================
# COMPARISON: RULE-BASED vs RAG
# ============================================================================

def compare_approaches(farmer_context: Dict, rag_results: List):
    """Compare rule-based vs RAG results"""
    
    print("\n" + "="*70)
    print("🔬 COMPARISON: Rule-Based vs RAG")
    print("="*70)
    
    # Rule-based
    rule_diseases = match_diseases_by_conditions(farmer_context)
    
    print("\n✅ RULE-BASED RESULTS (Filtered by actual conditions):")
    for i, disease in enumerate(rule_diseases[:5], 1):
        print(f"\n{i}. {disease['disease_name']} - Risk Score: {disease['risk_score']}")
        print(f"   Temperature match: {disease['temp_match']:.1f}/100")
        print(f"   Humidity match: {disease['humidity_match']:.1f}/100")
        print(f"   Conditions: {disease['conditions_met']['temperature']}, {disease['conditions_met']['humidity']}")
    
    # RAG results
    print("\n\n📊 RAG RESULTS (Semantic similarity only):")
    for i, (text, disease, climate, doc_type, similarity) in enumerate(rag_results[:5], 1):
        print(f"\n{i}. [{doc_type}] Similarity: {similarity:.3f}")
        if disease:
            print(f"   Disease: {disease}")
        if climate:
            print(f"   Climate Risk: {climate}")
        print(f"   {text[:100]}...")
    
    print("\n" + "="*70)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    
    test_context = {
        'crop': 'wheat',
        'province': 'Punjab',
        'district': 'Faisalabad',
        'stage': 'Vegetative',
        'days_after_sowing': 40,
        'temp': 22,
        'humidity': 40
    }
    
    print("\n" + "="*70)
    print("🌾 ZARAIRADAR - HYBRID RISK ASSESSMENT")
    print("="*70)
    print(f"\nFarmer Context:")
    print(f"  Location: {test_context['district']}, {test_context['province']}")
    print(f"  Crop Stage: {test_context['stage']} (Day {test_context['days_after_sowing']})")
    print(f"  Weather: {test_context['temp']}°C, {test_context['humidity']}% humidity")
    
    # Get rule-based assessment
    assessment = get_risk_assessment_hybrid(test_context)
    
    print("\n" + "="*70)
    print("📊 RISK ASSESSMENT RESULTS")
    print("="*70)
    
    # Disease Risk
    disease_risk = assessment['disease_risk']
    print(f"\n🦠 DISEASE RISK: {disease_risk['level']}")
    print(f"   Confidence: {disease_risk['confidence']:.0%}")
    
    if disease_risk['diseases']:
        print(f"\n   Detected Diseases:")
        for disease in disease_risk['diseases']:
            print(f"\n   • {disease['name']} [{disease['risk']}] - Score: {disease['score']}")
            print(f"     Reason: {disease['reason']}")
            print(f"     Action: {disease['action']}")
    else:
        print("   ✓ No disease risks detected")
    
    # Climate Risk
    climate_risk = assessment['climate_risk']
    print(f"\n🌡️ CLIMATE RISK: {climate_risk['level']}")
    print(f"   Confidence: {climate_risk['confidence']:.0%}")
    
    if climate_risk['risks']:
        print(f"\n   Active Risks:")
        for risk in climate_risk['risks']:
            print(f"\n   • {risk['name']} [{risk['severity']}]")
            print(f"     Impact: {risk['impact']}")
            print(f"     Action: {risk['action']}")
    else:
        print("   ✓ No climate risks detected")
    
    # Summary
    print(f"\n📋 SUMMARY")
    print(f"   {assessment['summary']}")
    
    print(f"\n⚡ PRIORITY ACTIONS:")
    for i, action in enumerate(assessment['priority_actions'], 1):
        print(f"   {i}. {action}")
    
    print("\n" + "="*70)