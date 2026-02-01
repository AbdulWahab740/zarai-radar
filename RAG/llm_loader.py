
import logging, traceback
import os
from dotenv import load_dotenv
load_dotenv()

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# def load_llm():
#     """Loads and caches the LLM for use in the application."""
#     if not GEMINI_API_KEY:
#         logging.warning("GEMINI API KEY Not found! Set GEMINI_API_KEY in .env file")
#     try:
#         llm = ChatGoogleGenerativeAI(
#             model="gemini-1.5-flash",
#             temperature=0.5,
#             max_tokens=2000,
#             api_key=GEMINI_API_KEY
#         )
#         return llm
#     except Exception as e:
#         traceback.print_exc()
from langchain_groq import ChatGroq       

GROK_API_KEY = os.getenv("GROK_API_KEY")

def load_llm():
    """Return the info of LLM"""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=2000,
        timeout=None,
        max_retries=2,
        api_key=GROK_API_KEY
    )
