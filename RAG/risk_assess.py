"""
ZaraiRadar - Risk Assessment Agent
Generates insights from RAG retrieval for dashboard display
"""

from typing import List, Dict, Any
import json
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from llm_loader import load_llm

def generate_risk_assessment_insights(
    retrieved_chunks: List[tuple],
    farmer_context: Dict[str, Any],
    
) -> Dict[str, Any]:
    """
    Generate structured risk assessment insights from RAG chunks
    
    Args:
        retrieved_chunks: List of (text, disease, climate, doc_type, similarity) tuples
        farmer_context: Dict with crop, location, stage, weather, etc.
        llm_client: LLM API client
    
    Returns:
        Structured risk assessment with disease and climate insights
    """
    
    # Prepare context from retrieved chunks
    context_text = prepare_context_for_llm(retrieved_chunks)

    # Build the prompt
    system_prompt = get_system_prompt()
    user_prompt = build_user_prompt(farmer_context, context_text)

    # Use LLM from llm_loader if not provided
    llm_client = load_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    response = llm_client.invoke(messages).content

    # Parse LLM response into structured format
    insights = parse_llm_response(response)
    return insights


def prepare_context_for_llm(retrieved_chunks: List[tuple]) -> str:
    """
    Format retrieved chunks into clean context for LLM
    """
    context_parts = []
    
    for i, (text, disease, climate, doc_type, similarity) in enumerate(retrieved_chunks, 1):
        chunk_info = f"[Document {i}] (Relevance: {similarity:.2f})"
        
        if disease:
            chunk_info += f" - Disease: {disease}"
        if climate:
            chunk_info += f" - Climate Risk: {climate}"
        
        chunk_info += f"\n{text}\n"
        context_parts.append(chunk_info)
    
    return "\n---\n".join(context_parts)


def get_system_prompt() -> str:
    """
    System prompt for the risk assessment agent
    """
    return """You are an agricultural expert advisor for Pakistani farmers using the ZaraiRadar platform.

Your task is to analyze retrieved agricultural documents and provide a structured risk assessment for the farmer's current crop situation.

CRITICAL INSTRUCTIONS:
1. Use ONLY information from the provided documents - do not add external knowledge
2. Always cite which document number you're referencing
3. Provide actionable, specific advice with dosages, timing, and methods
4. Be concise but thorough - farmers need clarity, not jargon
5. Use Pakistani English and familiar agricultural terms
6. Include specific product names, application rates, and timing from documents

OUTPUT FORMAT (JSON):
{
  "disease_risk": {
    "level": "HIGH|MEDIUM|LOW",
    "confidence": 0.0-1.0,
    "top_diseases": [
      {
        "name": "Disease name",
        "risk_level": "HIGH|MEDIUM|LOW",
        "triggers": ["trigger 1", "trigger 2"],
        "reasoning": "Why this disease is risky now",
        "source_doc": 1
      }
    ],
    "recommendations": [
      {
        "action": "Specific action to take",
        "timing": "When to do it",
        "product": "Product name and dosage if applicable",
        "urgency": "IMMEDIATE|WITHIN_48H|THIS_WEEK|MONITOR"
      }
    ]
  },
  "climate_risk": {
    "level": "HIGH|MEDIUM|LOW",
    "confidence": 0.0-1.0,
    "active_risks": [
      {
        "name": "Risk name",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "impact": "Description of impact",
        "triggers": ["trigger 1", "trigger 2"],
        "source_doc": 2
      }
    ],
    "recommendations": [
      {
        "action": "Specific action to take",
        "timing": "When to do it",
        "urgency": "IMMEDIATE|WITHIN_48H|THIS_WEEK|MONITOR"
      }
    ]
  },
  "overall_assessment": {
    "summary": "1-2 sentence summary of current situation",
    "priority_actions": ["Most important action 1", "Action 2"],
    "monitoring_needed": ["What to watch for 1", "What to watch for 2"]
  }
}

Remember: Farmers trust your advice - be accurate, specific, and actionable."""


def build_user_prompt(farmer_context: Dict[str, Any], context_text: str) -> str:
    """
    Build the user prompt with farmer context and retrieved documents
    """
    
    # Extract weather info
    weather = farmer_context.get('weather', {})
    
    prompt = f"""Analyze the current crop situation and provide risk assessment insights.

FARMER'S CURRENT SITUATION:
- Crop: {farmer_context.get('crop', 'Unknown')}
- Location: {farmer_context.get('district', 'Unknown')}, {farmer_context.get('province', 'Unknown')}
- Growth Stage: {farmer_context.get('stage', 'Unknown')}
- Days Since Sowing: {farmer_context.get('days_since_sowing', 'Unknown')}

CURRENT WEATHER CONDITIONS:
- Temperature: {weather.get('temp', 'Unknown')}°C
- Humidity: {weather.get('humidity', 'Unknown')}%
- Recent Rainfall (7 days): {weather.get('rainfall_7d', 'Unknown')}mm
- Forecast: {weather.get('forecast', 'No forecast available')}

RETRIEVED AGRICULTURAL DOCUMENTS:
{context_text}

Based on the above context and documents, provide a comprehensive risk assessment in JSON format following the specified structure. Focus on:
1. Which diseases are high risk given current weather and growth stage
2. Which climate risks threaten the crop now
3. Specific, actionable recommendations with timing and products
4. Prioritize the most urgent actions

Respond ONLY with valid JSON - no additional text."""

    return prompt


def parse_llm_response(llm_response: str) -> Dict[str, Any]:
    """
    Parse LLM JSON response and validate structure
    """
    try:
        # Extract JSON from response (in case LLM adds extra text)
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in LLM response")
        
        json_str = llm_response[json_start:json_end]
        insights = json.loads(json_str)
        
        # Validate required fields
        validate_insights_structure(insights)
        
        return insights
        
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response was: {llm_response}")
        return get_fallback_insights()
    except Exception as e:
        print(f"Unexpected error: {e}")
        return get_fallback_insights()


def validate_insights_structure(insights: Dict) -> None:
    """
    Validate that insights have required structure
    """
    required_keys = ['disease_risk', 'climate_risk', 'overall_assessment']
    for key in required_keys:
        if key not in insights:
            raise ValueError(f"Missing required key: {key}")
    
    # Validate disease_risk structure
    if 'level' not in insights['disease_risk']:
        raise ValueError("Missing disease_risk.level")
    if 'top_diseases' not in insights['disease_risk']:
        insights['disease_risk']['top_diseases'] = []
    
    # Validate climate_risk structure
    if 'level' not in insights['climate_risk']:
        raise ValueError("Missing climate_risk.level")
    if 'active_risks' not in insights['climate_risk']:
        insights['climate_risk']['active_risks'] = []


def get_fallback_insights() -> Dict[str, Any]:
    """
    Return safe fallback insights if LLM fails
    """
    return {
        "disease_risk": {
            "level": "UNKNOWN",
            "confidence": 0.0,
            "top_diseases": [],
            "recommendations": [
                {
                    "action": "Unable to generate risk assessment. Please consult local agricultural extension officer.",
                    "timing": "As soon as possible",
                    "urgency": "MONITOR"
                }
            ]
        },
        "climate_risk": {
            "level": "UNKNOWN",
            "confidence": 0.0,
            "active_risks": [],
            "recommendations": []
        },
        "overall_assessment": {
            "summary": "Risk assessment temporarily unavailable. Monitor crop closely and consult experts if issues arise.",
            "priority_actions": ["Contact agricultural extension office"],
            "monitoring_needed": ["Any visible crop stress or disease symptoms"]
        }
    }


# ============================================================================
# EXAMPLE USAGE FOR DASHBOARD
# ============================================================================

def format_for_dashboard(insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert LLM insights into dashboard-friendly format
    """
    
    dashboard_data = {
        # Disease Risk Panel
        "disease_panel": {
            "risk_level": insights['disease_risk']['level'],
            "risk_color": get_risk_color(insights['disease_risk']['level']),
            "confidence": insights['disease_risk']['confidence'],
            "top_diseases": [
                {
                    "name": d['name'],
                    "risk": d['risk_level'],
                    "triggers": d['triggers'][:3],  # Top 3 triggers
                    "alert_message": f"{d['name']} - {d['risk_level']} RISK"
                }
                for d in insights['disease_risk']['top_diseases'][:3]  # Top 3 diseases
            ],
            "urgent_actions": [
                r for r in insights['disease_risk'].get('recommendations', [])
                if r.get('urgency') in ['IMMEDIATE', 'WITHIN_48H']
            ][:2]  # Top 2 urgent actions
        },
        
        # Climate Risk Panel
        "climate_panel": {
            "risk_level": insights['climate_risk']['level'],
            "risk_color": get_risk_color(insights['climate_risk']['level']),
            "confidence": insights['climate_risk']['confidence'],
            "active_alerts": [
                {
                    "name": r['name'],
                    "severity": r['severity'],
                    "impact": r['impact'],
                    "alert_message": f"⚠️ {r['name']} - {r['severity']}"
                }
                for r in insights['climate_risk']['active_risks']
                if r['severity'] in ['CRITICAL', 'HIGH']
            ],
            "recommendations": insights['climate_risk'].get('recommendations', [])[:2]
        },
        
        # Overall Summary for Dashboard Top
        "summary_card": {
            "headline": insights['overall_assessment']['summary'],
            "priority_actions": insights['overall_assessment']['priority_actions'][:3],
            "monitoring": insights['overall_assessment']['monitoring_needed'][:2]
        },
        
        # Data freshness
        "metadata": {
            "generated_at": "timestamp_here",
            "data_sources": "PARC, CABI PlantWise (Demo Data)",
            "confidence_note": f"Assessment based on {insights['disease_risk']['confidence']:.0%} confidence match"
        }
    }
    
    return dashboard_data


def get_risk_color(risk_level: str) -> str:
    """
    Map risk level to color code for UI
    """
    colors = {
        "HIGH": "#EF4444",      # Red
        "MEDIUM": "#F59E0B",    # Yellow/Orange
        "LOW": "#10B981",       # Green
        "UNKNOWN": "#6B7280"    # Gray
    }
    return colors.get(risk_level, "#6B7280")


# ============================================================================
# COMPLETE WORKFLOW EXAMPLE
# ============================================================================

def complete_risk_assessment_workflow(
    farmer_context: Dict[str, Any],
    rag_search_function,  # Your RAG search function
    llm_client
) -> Dict[str, Any]:
    """
    Complete end-to-end workflow from farmer context to dashboard-ready insights
    """
    
    # Step 1: Enhance query with farmer context
    enhanced_query = f"""
    Crop: {farmer_context['crop']}
    Location: {farmer_context['district']}, {farmer_context['province']}
    Growth Stage: {farmer_context['stage']}
    Days Since Sowing: {farmer_context['days_since_sowing']}
    Temperature: {farmer_context['weather']['temp']}°C
    Humidity: {farmer_context['weather']['humidity']}%
    Recent Rainfall: {farmer_context['weather']['rainfall_7d']}mm
    
    What diseases and climate risks should this farmer watch for right now?
    Provide specific management recommendations.
    """
    
    # Step 2: Retrieve relevant chunks from vector DB
    retrieved_chunks = rag_search_function(enhanced_query, farmer_context)
    
    # Step 3: Generate insights using LLM
    insights = generate_risk_assessment_insights(
        retrieved_chunks,
        farmer_context,
        llm_client
    )
    
    # Step 4: Format for dashboard display
    dashboard_data = format_for_dashboard(insights)
    
    return dashboard_data


# ============================================================================
# SIMPLE PROMPT TEMPLATE (Alternative - No Structured JSON)
# ============================================================================

def get_simple_prompt_template(farmer_context: Dict, context_text: str) -> str:
    """
    Simpler prompt if you want natural language response instead of JSON
    """
    return f"""You are an agricultural advisor analyzing crop risks for a Pakistani farmer.

FARMER'S SITUATION:
- Crop: {farmer_context['crop']} at {farmer_context['stage']} stage (Day {farmer_context['days_since_sowing']})
- Location: {farmer_context['district']}, {farmer_context['province']}
- Weather: {farmer_context['weather']['temp']}°C, {farmer_context['weather']['humidity']}% humidity, {farmer_context['weather']['rainfall_7d']}mm rain (last 7 days)

RELEVANT AGRICULTURAL KNOWLEDGE:
{context_text}

Provide a concise risk assessment covering:

1. DISEASE RISK (High/Medium/Low):
   - Which diseases are most likely now and why
   - What triggers their appearance
   - Specific treatment recommendations with products and dosages

2. CLIMATE RISK (High/Medium/Low):
   - Weather-related threats to watch for
   - Potential impacts on yield and quality
   - Protective actions to take

3. PRIORITY ACTIONS:
   - Top 2-3 most urgent things farmer should do this week
   - Specific timing (e.g., "within 48 hours", "before next rain")

Be specific, actionable, and cite which documents support your recommendations.
Keep the response under 300 words - farmers need quick, clear guidance."""



if __name__ == "__main__":
    # Example usage
    print("Risk Assessment Agent Module")
    print("Import this module and use:")
    print("  - generate_risk_assessment_insights()")
    print("  - format_for_dashboard()")
    print("  - complete_risk_assessment_workflow()")