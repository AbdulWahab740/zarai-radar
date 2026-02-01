# Creates embeddings for documents using a specified embedding model.
from typing import List
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# Initialize with a specific model (e.g., a popular lightweight one)
embeddings = HuggingFaceEmbeddings(model_name="intfloat/e5-base-v2")

def create_document_embeddings(documents: List[Document]) -> List[List[float]]:
    """
    Create embeddings for a list of documents.

    Args:
        documents (List[Document]): A list of Document objects.
    Returns:
        List[List[float]]: A list of embeddings corresponding to the documents.
    """
    texts = [doc.page_content for doc in documents]
    return embeddings.embed_documents(texts)

def create_query_embedding(query: str) -> List[float]:
    """
    Create an embedding for a query string.

    Args:
        query (str): The query string.
    Returns:
        List[float]: The embedding corresponding to the query.
    """
    return embeddings.embed_query(query)

