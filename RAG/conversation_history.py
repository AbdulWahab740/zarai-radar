"""
conversation_history.py
Supabase-backed conversation history manager (RAG wrapper).
"""

from App.conversation_history import ConversationHistoryManager

__all__ = ["ConversationHistoryManager"]


# initiate the database tables on module load
if __name__ == "__main__":
    manager = ConversationHistoryManager()