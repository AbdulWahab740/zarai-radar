import json
import pandas as pd
import psycopg2
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

# db.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize supabase client if credentials are provided, otherwise set to None
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")
        print("HTML pages will still be served, but API endpoints requiring Supabase will not work.")


# Initialize with a specific model (e.g., a popular lightweight one)
model = HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")


def create_disease_chunks(disease_data):
    """Create text chunks from disease data for RAG retrieval"""
    chunks = []
    
    # Chunk 1: Disease identification and symptoms
    chunk1 = f"""
    Disease: {disease_data['disease_name']} ({disease_data['pathogen']})
    Crop: Wheat
    Affected Growth Stages: {', '.join(disease_data['affected_stages'])}
    
    Symptoms: {disease_data['symptoms']}
    
    This disease is most severe during {' and '.join(disease_data['affected_stages'])} stages, 
    typically appearing {disease_data['vulnerable_days_after_sowing'][0]}-{disease_data['vulnerable_days_after_sowing'][1]} days after sowing.
    """
    
    chunks.append({
        'text': chunk1.strip(),
        'type': 'disease_symptoms',
        'disease_name': disease_data['disease_name'],
        'stages': disease_data['affected_stages'],
        'metadata': {
            'pathogen': disease_data['pathogen'],
            'days_after_sowing': disease_data['vulnerable_days_after_sowing']
        }
    })
    
    # Chunk 2: Favorable conditions and climate triggers
    conditions = disease_data['favorable_conditions']
    chunk2 = f"""
    {disease_data['disease_name']} Weather Conditions and Risk Factors
    
    Favorable Climate Conditions:
    - Temperature: {conditions['temperature_min']}-{conditions['temperature_max']}°C (optimal: {conditions['temperature_optimal']}°C)
    - Humidity: Above {conditions['humidity_min']}%
    - Rainfall: {conditions['rainfall_requirement']} rainfall required
    - Dew: {"Morning dew favors disease" if conditions['dew_requirement'] else "Dew not required"}
    
    Climate Triggers that Increase Risk:
    {chr(10).join('- ' + trigger for trigger in disease_data['climate_triggers'])}
    
    High Risk Districts in Pakistan:
    {', '.join(disease_data['high_risk_districts'])}
    
    Regional Prevalence:
    - Punjab: {disease_data['regional_prevalence']['Punjab']}
    - Sindh: {disease_data['regional_prevalence']['Sindh']}
    - KPK: {disease_data['regional_prevalence']['KPK']}
    - Balochistan: {disease_data['regional_prevalence']['Balochistan']}
    """
    
    chunks.append({
        'text': chunk2.strip(),
        'type': 'disease_conditions',
        'disease_name': disease_data['disease_name'],
        'stages': disease_data['affected_stages'],
        'metadata': {
            'temp_range': [conditions['temperature_min'], conditions['temperature_max']],
            'humidity_min': conditions['humidity_min'],
            'high_risk_districts': disease_data['high_risk_districts']
        }
    })
    
    # Chunk 3: Management and treatment
    mgmt = disease_data['management']
    chunk3 = f"""
    {disease_data['disease_name']} Management and Treatment
    
    Preventive Measures:
    {chr(10).join('- ' + measure for measure in mgmt['preventive'])}
    
    Chemical Control:
    {chr(10).join('- ' + chemical for chemical in mgmt['chemical_control'])}
    
    Application Timing: {mgmt['timing']}
    
    Potential Impact if Untreated:
    - Yield Loss: {disease_data['severity_impact']['yield_loss_potential']}
    - Quality Impact: {disease_data['severity_impact']['quality_impact']}
    
    Source: {disease_data['source']}
    """
    
    chunks.append({
        'text': chunk3.strip(),
        'type': 'disease_management',
        'disease_name': disease_data['disease_name'],
        'stages': disease_data['affected_stages'],
        'metadata': {
            'yield_loss': disease_data['severity_impact']['yield_loss_potential'],
            'source': disease_data['source']
        }
    })
    
    return chunks

def create_climate_chunks(climate_data):
    """Create text chunks from climate risk data"""
    chunks = []
    
    # Chunk 1: Risk description and impact
    chunk1 = f"""
    Climate Risk: {climate_data['risk_name']}
    Crop: Wheat
    Affected Growth Stages: {', '.join(climate_data['affected_stages'])}
    Critical Timing: {climate_data['critical_days_after_sowing'][0]}-{climate_data['critical_days_after_sowing'][1]} days after sowing
    
    Description: {climate_data['description']}
    
    Impact on Wheat Crop:
    - Yield Reduction: {climate_data['impact']['yield_reduction']}
    - Grain Quality: {climate_data['impact']['grain_quality']}
    - Other Effects: {climate_data['impact']['other_effects']}
    """
    
    chunks.append({
        'text': chunk1.strip(),
        'type': 'climate_risk_description',
        'climate_risk_name': climate_data['risk_name'],
        'stages': climate_data['affected_stages'],
        'metadata': {
            'critical_days': climate_data['critical_days_after_sowing'],
            'impact': climate_data['impact']
        }
    })
    
    # Chunk 2: Trigger conditions and indicators
    chunk2 = f"""
    {climate_data['risk_name']} - Warning Signs and Trigger Conditions
    
    Trigger Conditions:
    {json.dumps(climate_data['trigger_conditions'], indent=2)}
    
    Climate Indicators to Watch:
    {chr(10).join('- ' + indicator for indicator in climate_data['climate_indicators'])}
    
    Regional Vulnerability in Pakistan:
    - Punjab: {climate_data['regional_vulnerability']['Punjab']}
    - Sindh: {climate_data['regional_vulnerability']['Sindh']}
    - KPK: {climate_data['regional_vulnerability']['KPK']}
    - Balochistan: {climate_data['regional_vulnerability']['Balochistan']}
    
    High Risk Districts:
    {', '.join(climate_data['high_risk_districts'])}
    """
    
    chunks.append({
        'text': chunk2.strip(),
        'type': 'climate_risk_triggers',
        'climate_risk_name': climate_data['risk_name'],
        'stages': climate_data['affected_stages'],
        'metadata': {
            'triggers': climate_data['trigger_conditions'],
            'high_risk_districts': climate_data['high_risk_districts']
        }
    })
    
    # Chunk 3: Management recommendations
    chunk3 = f"""
    {climate_data['risk_name']} - Management Recommendations
    
    Actions to Take:
    {chr(10).join('- ' + rec for rec in climate_data['management_recommendations'])}
    
    Source: {climate_data['source']}
    """
    
    chunks.append({
        'text': chunk3.strip(),
        'type': 'climate_risk_management',
        'climate_risk_name': climate_data['risk_name'],
        'stages': climate_data['affected_stages'],
        'metadata': {
            'source': climate_data['source']
        }
    })
    
    return chunks

def insert_data_to_supabase():
    print("Loading JSON data...")
    with open('data/wheat_knowledge_base.json', 'r') as f:
        data = json.load(f)
    # print("\nProcessing disease data...")
    # for disease in data['wheat_diseases']:
    #     chunks = create_disease_chunks(disease)
        
    #     for chunk in chunks:
    #         # Generate embedding
    #         embedding = model.embed_query(chunk['text'])
            
    #         data = {
    #             "chunk_text": chunk['text'],
    #             "embedding": embedding,
    #             "document_type": chunk['type'],
    #             "crop_type": 'wheat',
    #             "disease_name": chunk['disease_name'],
    #             "affected_stages": chunk['stages'],
    #             "metadata": json.dumps(chunk['metadata'])
    #         }
    #         try:
    #             # Insert record using Supabase client
    #             supabase.table("diseases_vec").insert(data).execute()
    #         except Exception as e:
    #             print(f"Error inserting chunk: {e}")

    print("\nProcessing climate data...")
    for risk in data['climate_risk_factors']:
        chunks = create_climate_chunks(risk)
        
        for chunk in chunks:
            # Generate embedding
            embedding = model.embed_query(chunk['text'])
            
            data = {
                "chunk_text": chunk['text'],
                "embedding": embedding,
                "document_type": chunk['type'],
                "crop_type": 'wheat',
                "climate_risk_name": chunk['climate_risk_name'],
                "affected_stages": chunk['stages'],
                "metadata": json.dumps(chunk['metadata'])
            }
            try:
                # Insert record using Supabase client
                supabase.table("diseases_vec").insert(data).execute()
               
            except Exception as e:
                print(f"Error inserting chunk: {e}")
        print(f"  ✓ Loaded {risk['risk_name']} ({len(chunks)} chunks)")

import numpy as np
import ast  
def cosine_similarity(a, b):
    # Ensure both are NumPy arrays of float
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
def search_disease_vec_with_similarity(enhanced_query, farmer_context, limit=5):
    """
    Your existing Supabase RAG search function
    """
    # Generate embedding using Hugging Face
    query_embedding = model.embed_query(enhanced_query)  # list of floats

    # Normalize stage string
    filter_stage = farmer_context["stage"].strip().title()

    # Query table directly
    response = (
        supabase.table("diseases_vec")
        .select("chunk_text, disease_name, climate_risk_name, document_type, embedding, affected_stages")
        .filter("affected_stages", "cs", f"{{{filter_stage}}}")
        .limit(50)  # fetch more to calculate similarity manually
        .execute()
    )

    if not response.data:
        print("⚠️ No matching rows found in database.")
        return []

    # Calculate similarity for each row
    results = []
    rows = response.data
    for row in rows:    
        # Convert embedding to float array
        row_embedding_str = row["embedding"]  # Supabase returns as string
        row_embedding = np.array(ast.literal_eval(row_embedding_str), dtype=np.float32)
        sim = cosine_similarity(query_embedding, row_embedding)
        results.append(
            (
                row["chunk_text"],
                row.get("disease_name"),
                row.get("climate_risk_name"),
                row.get("document_type"),
                sim
            )
        )

    # Sort by similarity descending
    results.sort(key=lambda x: x[4], reverse=True)

    return results[:limit]


def test_rag_query(query_text, farmer_context):
    """Test function to query the RAG system using Supabase"""

    print(f"\nTesting RAG Query: '{query_text}'")
    print(f"Context: {farmer_context}")

    # Create enhanced query (UNCHANGED)
    enhanced_query = f"""
    Crop: {farmer_context['crop']}
    Location: {farmer_context['district']}, {farmer_context['province']}
    Growth Stage: {farmer_context['stage']}
    Days Since Sowing: {farmer_context['days_since_sowing']}
    Temperature: {farmer_context['temp']}°C
    Humidity: {farmer_context['humidity']}%

    Farmer Question: {query_text}
    """

    results = search_disease_vec_with_similarity(enhanced_query, farmer_context)

    print("\n--- Top Retrieved Chunks ---")
    for i, (text, disease, climate, doc_type, similarity) in enumerate(results, 1):
        print(f"\n{i}. [{doc_type}] Similarity: {similarity:.3f}")
        if disease:
            print(f"   Disease: {disease}")
        if climate:
            print(f"   Climate Risk: {climate}")
        print(f"   {text[:200]}...")

    return results, farmer_context

if __name__ == "__main__":
    test_context = {
        'crop': 'wheat',
        'province': 'Punjab',
        'district': 'Faisalabad',
        'stage': 'Vegetative',
        'days_since_sowing': 40,
        'temp': 22,
        'humidity': 85
    }
    
    test_rag_query("What diseases should I watch for?", test_context)