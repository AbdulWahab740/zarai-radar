import sys
import os

# Add parent directory to path to allow importing App module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from App.db import supabase
from RAG.embeddings import create_document_embeddings
from RAG.splitter import load_and_split_documents


def insert_document(data_path, topic, crop, province, data_type, source, year):
    if not supabase:
        print("❌ Supabase client not initialized. Check .env configuration.")
        return

    chunks = load_and_split_documents(data_path)
    count = 0

    for chunk in chunks:
        # `chunk` is a Document — pass as a single-item list to the embeddings function
        embedding_list = create_document_embeddings([chunk])
        # store the first embedding returned for this single chunk
        embedding = embedding_list[0] if embedding_list else None

        data = {
            "content": chunk.page_content,
            "topic": topic,
            "crop": crop,
            "province": province,
            "data_type": data_type,
            "source": source,
            "year": year,
            "embedding": embedding
        }
        
        try:
            # Insert record using Supabase client
            supabase.table("agri_documents").insert(data).execute()
            count += 1
        except Exception as e:
            print(f"Error inserting chunk: {e}")

    print(f"✅ Inserted {count} chunks from {os.path.basename(data_path)}")

if __name__ == "__main__":
    data_directory = os.path.join(os.path.dirname(__file__), 'data', 'Fertilizer FAO.pdf')

    insert_document(
        data_path=data_directory,
        topic="Fertilizer FAO",
        crop="All",
        province="Pakistan",
        data_type="soil",
        source="FAO",
        year=2025
    )
