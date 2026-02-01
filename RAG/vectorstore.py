# vector_search.py
from App.db import supabase
from RAG.embeddings import create_query_embedding

def similarity_search(query, data_type=None, crop=None, province="Punjab", limit=5) -> list[tuple[str, float]]:
    """
    Perform similarity search on agri_documents table using vector embeddings via Supabase RPC.

    Args:
        query (str): The user query
        data_type (str, optional): Topic filter. Defaults to None.
        crop (str, optional): Crop filter. Defaults to None.
        province (str, optional): Province filter. Defaults to "Punjab".
        limit (int, optional): Number of results. Defaults to 5.

    Returns:
        List[str]: Top matching document contents
    """
    if not supabase:
        print("❌ Supabase client not initialized. Check .env configuration.")
        return []

    # Generate embedding for the query using same model as documents
    query_embedding = create_query_embedding(query)

    params = {
        "query_embedding": query_embedding,
        "match_threshold": 0.5, # Adjust threshold as needed
        "match_count": limit,
        "filter_province": province,
        "filter_crop": crop,
        "filter_data_type": data_type
    }

    try:
        # Call the PostgreSQL function (RPC) created in Supabase
        response = supabase.rpc("match_agri_documents", params).execute()
        result = response.data
        
        # Return list of (content, score) tuples
        return [(row['content'], float(row['score'])) for row in result]
        
    except Exception as e:
        print(f"Error during similarity search: {e}")
        return []


    
