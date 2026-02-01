"""
conversation_history.py
Supabase-based conversation history manager with chat titles
Stores all conversations with titles and displays them with content
"""

from typing import Dict, List, Optional, Tuple
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from datetime import datetime, timezone
import json
import os
from App.db import supabase

# ============================================================================
# CONVERSATION HISTORY MANAGER WITH SUPABASE
# ============================================================================

class ConversationHistoryManager:
    """
    Manages conversation history with Supabase persistence.
    Stores conversations with titles, messages, and analytics.
    """
    
    def __init__(self, session_id: str = None):
        """
        Initialize conversation history manager.
        
        Args:
            session_id: Unique identifier for conversation session (auto-generated if None)
        """
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.chat_title = None
        self.message_history = ChatMessageHistory()
        
        # Check connection
        if not supabase:
            print("❌ Supabase client not initialized. Check .env configuration.")

    def _get_isotime(self):
        """Get current UTC time in ISO format"""
        return datetime.now(timezone.utc).isoformat()
    
    def create_chat(self, chat_title: str, description: str = "") -> str:
        """
        Create a new chat conversation with a title.
        Uses upsert to handle potential conflicts or updates.
        """
        self.chat_title = chat_title
        
        data = {
            "session_id": self.session_id,
            "chat_title": chat_title,
            "description": description,
            "updated_at": self._get_isotime()
        }
        
        try:
            # Upsert conversation
            supabase.table("conversations").upsert(data).execute()
            print(f"✓ Chat created/updated: '{chat_title}' (ID: {self.session_id})")
            return self.session_id
        except Exception as e:
            print(f"⚠️  Error creating chat: {str(e)}")
            raise
    
    def add_user_message(self, content: str) -> HumanMessage:
        """Add user message to history"""
        msg = HumanMessage(content=content)
        self.message_history.add_message(msg)
        self._save_message("human", content, {"type": "query"})
        return msg
    
    def add_agent_response(self, content: str, metadata: Dict = None) -> AIMessage:
        """Add agent response to history"""
        msg = AIMessage(content=content)
        self.message_history.add_message(msg)
        self._save_message("ai", content, metadata or {"type": "response"})
        return msg
    
    def _save_message(self, msg_type: str, content: str, metadata: Dict = None):
        """Save message to database"""
        try:
            data = {
                "session_id": self.session_id,
                "message_type": msg_type,
                "content": content,
                "metadata": metadata or {},
                "created_at": self._get_isotime()
            }
            supabase.table("chat_messages").insert(data).execute()
        except Exception as e:
            print(f"⚠️  Error saving message to database: {str(e)}")
    
    def save_query_response(self, query: str, response: str, domains: List[str], 
                          duration: float, status: str = "success"):
        """Save query-response pair for analytics"""
        try:
            # Update conversation metadata
            supabase.table("conversations").update({
                "updated_at": self._get_isotime(),
                # Ideally execute RPC to increment, but simplified read-update-write or just updated_at for now
                # Supabase doesn't support field increment easily without RPC or extensions
            }).eq("session_id", self.session_id).execute()
            
            # Save analytics
            analytics_data = {
                "session_id": self.session_id,
                "query": query,
                "response": response[:2000] if response else "",
                "domains_searched": ",".join(domains) if domains else "",
                "duration_seconds": duration,
                "status": status,
                "created_at": self._get_isotime()
            }
            supabase.table("conversation_analytics").insert(analytics_data).execute()
            
        except Exception as e:
            print(f"⚠️  Error saving query response to database: {str(e)}")
    
    def get_message_history(self) -> List[BaseMessage]:
        """Get all messages in current session"""
        return self.message_history.messages
    
    def get_recent_context(self, last_n: int = 4) -> str:
        """Get recent messages as context string for agent"""
        messages = self.message_history.messages[-last_n:]
        context_lines = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                context_lines.append(f"User: {msg.content[:200]}")
            elif isinstance(msg, AIMessage):
                context_lines.append(f"Agent: {msg.content[:200]}")
        
        return "\n".join(context_lines) if context_lines else ""
    
    def load_chat(self, session_id: str) -> bool:
        """Load a previous chat's conversation history."""
        try:
            # Get chat metadata
            response = supabase.table("conversations").select("*").eq("session_id", session_id).single().execute()
            chat_meta = response.data
            
            if not chat_meta:
                print(f"❌ Chat '{session_id}' not found")
                return False
            
            self.chat_title = chat_meta.get('chat_title')
            
            # Get all messages
            msg_response = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
            rows = msg_response.data
            
            self.session_id = session_id
            self.message_history = ChatMessageHistory()
            
            for row in rows:
                if row['message_type'] == "human":
                    self.message_history.add_message(HumanMessage(content=row['content']))
                elif row['message_type'] == "ai":
                    self.message_history.add_message(AIMessage(content=row['content']))
            
            print(f"✓ Loaded chat: '{self.chat_title}' with {len(rows)} messages")
            return True
        except Exception as e:
            print(f"⚠️  Error loading chat: {str(e)}")
            return False
    
    def list_chats(self, limit: int = 20) -> List[Dict]:
        """List all available chats with their titles and metadata."""
        try:
            response = supabase.table("conversations").select("*").order("updated_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"⚠️  Error listing chats: {str(e)}")
            return []
    
    def get_chat_summary(self) -> Dict:
        """Get summary of current chat session"""
        history = self.message_history.messages
        try:
            response = supabase.table("conversations").select("*").eq("session_id", self.session_id).single().execute()
            chat_info = response.data
            
            return {
                "session_id": self.session_id,
                "chat_title": chat_info['chat_title'] if chat_info else self.chat_title,
                "message_count": len(history),
                "user_queries": len([m for m in history if isinstance(m, HumanMessage)]),
                "agent_responses": len([m for m in history if isinstance(m, AIMessage)]),
                "created_at": chat_info.get('created_at'),
                "query_count": chat_info.get('query_count', 0)
            }
        except Exception as e:
            print(f"⚠️  Error getting chat summary: {str(e)}")
            return {
                "session_id": self.session_id,
                "chat_title": self.chat_title,
                "message_count": len(history),
                "user_queries": len([m for m in history if isinstance(m, HumanMessage)]),
                "agent_responses": len([m for m in history if isinstance(m, AIMessage)])
            }
    
    def export_chat(self, output_file: str = None) -> str:
        """Export conversation chat to JSON file."""
        if output_file is None:
            safe_title = self.chat_title.replace(" ", "_").replace("/", "_")[:50] if self.chat_title else "export"
            output_file = f"chat_{safe_title}_{self.session_id[:8]}.json"
        
        history = self.message_history.messages
        chat_data = {
            "session_id": self.session_id,
            "chat_title": self.chat_title,
            "exported_at": datetime.now().isoformat(),
            "total_messages": len(history),
            "messages": [
                {
                    "type": "user" if isinstance(m, HumanMessage) else "agent",
                    "content": m.content
                }
                for m in history
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(chat_data, f, indent=2)
        
        print(f"✓ Chat exported to {output_file}")
        return output_file
    
    def delete_chat(self, session_id: str) -> bool:
        """Delete a chat and all its messages."""
        try:
            # Cascading delete is handled by database constraints if set up, 
            # otherwise Supabase API deletes if foreign keys allow.
            # We explicitly delete conversation which usually cascades if DB schema is right.
            # If not, we might need to delete messages first. Assuming CASCADE setup as per original SQL.
            supabase.table("conversations").delete().eq("session_id", session_id).execute()
            
            print(f"✓ Chat '{session_id}' deleted")
            return True
        except Exception as e:
            print(f"⚠️  Error deleting chat: {str(e)}")
            return False
    
    def search_chats(self, keyword: str) -> List[Dict]:
        """Search chats by title, description (Supabase search is limited without full text search setup)"""
        try:
            # Simple ilike search on title or description
            # Combing OR filters in Supabase client: .or_('chat_title.ilike.%key%,description.ilike.%key%')
            search_filter = f"chat_title.ilike.%{keyword}%,description.ilike.%{keyword}%"
            
            response = supabase.table("conversations").select("*").or_(search_filter).order("updated_at", desc=True).limit(20).execute()
            
            return response.data
        except Exception as e:
            print(f"⚠️  Error searching chats: {str(e)}")
            return []
    
    def get_chat_content(self, session_id: str) -> Dict:
        """Get full chat content with title and all messages."""
        try:
            # Get chat
            chat_response = supabase.table("conversations").select("*").eq("session_id", session_id).single().execute()
            chat_info = chat_response.data
            if not chat_info:
                return None
            
            # Get messages
            msg_response = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
            messages = msg_response.data
            
            return {
                "session_id": session_id,
                "chat_title": chat_info.get('chat_title'),
                "description": chat_info.get('description'),
                "created_at": chat_info.get('created_at'),
                "messages": [
                    {
                        "type": msg['message_type'],
                        "content": msg['content'],
                        "timestamp": msg.get('created_at')
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            print(f"⚠️  Error getting chat content: {str(e)}")
            return None


