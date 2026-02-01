"""
Orchestrator Service - Bridge between FastAPI and Agent Logic
Handles conversation management and agent query processing
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add RAG folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'RAG'))

from RAG.orchestrator_agent import AgricultureOrchestratorAgent
from conversation_history import ConversationHistoryManager


class OrchestratorService:
    """
    Service layer for orchestrator agent.
    Handles conversation creation, query processing, and history management.
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Initialize orchestrator service.
        
        Args:
            max_workers: Number of worker threads for async processing
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_conversations = {}  # Cache for active conversations
    
    async def create_conversation(self, chat_title: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new conversation session.
        
        Args:
            chat_title: Title for the conversation
            description: Optional description
            
        Returns:
            Dictionary with session_id and chat metadata
        """
        try:
            agent = AgricultureOrchestratorAgent(
                max_iterations=15,
                chat_title=chat_title
            )
            
            session_id = agent.history_manager.session_id
            self.active_conversations[session_id] = agent
            
            summary = agent.history_manager.get_chat_summary()
            
            return {
                "status": "success",
                "session_id": session_id,
                "chat_title": chat_title,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "summary": summary
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create conversation: {str(e)}"
            }
    
    async def process_query(self, session_id: str, query: str, 
                           chat_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a query through the agent.
        
        Args:
            session_id: Conversation session ID (or None for new)
            query: User's query
            chat_title: Title for new conversation (if session_id is None)
            
        Returns:
            Dictionary with agent response and metadata
        """
        try:
            # Get or create agent
            if session_id and session_id in self.active_conversations:
                agent = self.active_conversations[session_id]
            else:
                agent = AgricultureOrchestratorAgent(
                    max_iterations=15,
                    session_id=session_id,
                    chat_title=chat_title or "Quick Query"
                )
                if session_id:
                    self.active_conversations[session_id] = agent
            
            # Run agent in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                agent.process_query,
                query
            )
            
            return {
                "status": result.get("status", "success"),
                "session_id": agent.history_manager.session_id,
                "answer": result.get("answer", ""),
                "reasoning": result.get("reasoning", ""),
                "metadata": result.get("metadata", {}),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process query: {str(e)}"
            }
    
    async def get_conversation(self, session_id: str) -> Dict[str, Any]:
        """
        Get conversation details and history.
        
        Args:
            session_id: Conversation session ID
            
        Returns:
            Dictionary with conversation and messages
        """
        try:
            # Load from database if not in cache
            if session_id not in self.active_conversations:
                history_manager = ConversationHistoryManager(session_id=session_id)
                if not history_manager.load_chat(session_id):
                    return {
                        "status": "error",
                        "message": f"Conversation '{session_id}' not found"
                    }
            else:
                history_manager = self.active_conversations[session_id].history_manager
            
            content = history_manager.get_chat_content(session_id)
            
            if not content:
                return {
                    "status": "error",
                    "message": f"Unable to retrieve conversation '{session_id}'"
                }
            
            return {
                "status": "success",
                "data": content
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get conversation: {str(e)}"
            }
    
    async def list_conversations(self, limit: int = 20) -> Dict[str, Any]:
        """
        List all conversations.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            Dictionary with list of conversations
        """
        try:
            history_manager = ConversationHistoryManager()
            chats = history_manager.list_chats(limit=limit)
            
            return {
                "status": "success",
                "total": len(chats),
                "conversations": chats
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list conversations: {str(e)}"
            }
    
    async def search_conversations(self, keyword: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search conversations by keyword.
        
        Args:
            keyword: Search keyword
            limit: Maximum results
            
        Returns:
            Dictionary with search results
        """
        try:
            history_manager = ConversationHistoryManager()
            results = history_manager.search_chats(keyword)
            
            return {
                "status": "success",
                "keyword": keyword,
                "total": len(results),
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to search conversations: {str(e)}"
            }
    
    async def delete_conversation(self, session_id: str) -> Dict[str, Any]:
        """
        Delete a conversation.
        
        Args:
            session_id: Conversation session ID
            
        Returns:
            Status dictionary
        """
        try:
            history_manager = ConversationHistoryManager()
            success = history_manager.delete_chat(session_id)
            
            # Remove from cache if exists
            if session_id in self.active_conversations:
                del self.active_conversations[session_id]
            
            return {
                "status": "success" if success else "error",
                "message": "Conversation deleted successfully" if success else "Failed to delete conversation"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete conversation: {str(e)}"
            }
    
    async def export_conversation(self, session_id: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Export conversation as JSON.
        
        Args:
            session_id: Conversation session ID
            output_file: Optional output filename
            
        Returns:
            Dictionary with export status and file path
        """
        try:
            history_manager = ConversationHistoryManager()
            if not history_manager.load_chat(session_id):
                return {
                    "status": "error",
                    "message": f"Conversation '{session_id}' not found"
                }
            
            file_path = history_manager.export_chat(output_file)
            
            return {
                "status": "success",
                "message": "Conversation exported successfully",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to export conversation: {str(e)}"
            }
    
    async def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of a conversation.
        
        Args:
            session_id: Conversation session ID
            
        Returns:
            Dictionary with conversation summary
        """
        try:
            # Load from database
            history_manager = ConversationHistoryManager()
            if not history_manager.load_chat(session_id):
                return {
                    "status": "error",
                    "message": f"Conversation '{session_id}' not found"
                }
            
            summary = history_manager.get_chat_summary()
            
            return {
                "status": "success",
                "data": summary
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get conversation summary: {str(e)}"
            }
    
    def cleanup(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)


# Global service instance
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service() -> OrchestratorService:
    """Get or create global orchestrator service"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service
