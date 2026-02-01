"""
conversation_history.py
PostgreSQL-based conversation history manager with chat titles
Stores all conversations with titles and displays them with content
"""

from typing import Dict, List, Optional, Tuple
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# POSTGRESQL CONNECTION SETUP
# ============================================================================

class PostgreSQLConnection:
    """Manages PostgreSQL database connections"""
    
    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5433")
        self.database = os.getenv("DB_NAME", "zarai_db")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "postgres")
    
    def get_connection(self):
        """Get a database connection"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return conn
        except psycopg2.Error as e:
            print(f"❌ Database connection error: {str(e)}")
            raise


# ============================================================================
# CONVERSATION HISTORY MANAGER WITH POSTGRESQL
# ============================================================================

class ConversationHistoryManager:
    """
    Manages conversation history with PostgreSQL persistence.
    Stores conversations with titles, messages, and analytics.
    """
    
    def __init__(self, session_id: str = None):
        """
        Initialize conversation history manager.
        
        Args:
            session_id: Unique identifier for conversation session (auto-generated if None)
        """
        self.db = PostgreSQLConnection()
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.chat_title = None
        self.message_history = ChatMessageHistory()
        
        # Initialize database tables
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables for conversation history if they don't exist"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create conversations table (chats with titles)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id VARCHAR(100) PRIMARY KEY,
                    chat_title VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query_count INTEGER DEFAULT 0
                );
            """)
            
            # Create messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
                    message_type VARCHAR(20),
                    content TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                );
            """)
            
            # Create query responses table (for analytics)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_analytics (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
                    query TEXT,
                    response TEXT,
                    domains_searched VARCHAR(255),
                    duration_seconds FLOAT,
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                );
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analytics_session ON conversation_analytics(session_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✓ Database tables initialized")
        except Exception as e:
            print(f"⚠️  Error initializing database: {str(e)}")
    
    def create_chat(self, chat_title: str, description: str = "") -> str:
        """
        Create a new chat conversation with a title.
        
        Args:
            chat_title: Title for the chat
            description: Optional description
            
        Returns:
            session_id
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            self.chat_title = chat_title
            
            cursor.execute("""
                INSERT INTO conversations (session_id, chat_title, description, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE 
                SET chat_title = %s, updated_at = %s
            """, (
                self.session_id, chat_title, description, datetime.now(), datetime.now(),
                chat_title, datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✓ Chat created: '{chat_title}' (ID: {self.session_id})")
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
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO chat_messages (session_id, message_type, content, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                self.session_id,
                msg_type,
                content,
                json.dumps(metadata or {}),
                datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"⚠️  Error saving message to database: {str(e)}")
    
    def save_query_response(self, query: str, response: str, domains: List[str], 
                          duration: float, status: str = "success"):
        """Save query-response pair for analytics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Update conversation metadata
            cursor.execute("""
                UPDATE conversations 
                SET updated_at = %s, query_count = query_count + 1
                WHERE session_id = %s
            """, (datetime.now(), self.session_id))
            
            # Save query response
            cursor.execute("""
                INSERT INTO conversation_analytics 
                (session_id, query, response, domains_searched, duration_seconds, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                self.session_id,
                query,
                response[:2000] if response else "",  # Truncate long responses
                ",".join(domains) if domains else "",
                duration,
                status,
                datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
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
        """
        Load a previous chat's conversation history.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get chat metadata
            cursor.execute("""
                SELECT chat_title, description FROM conversations
                WHERE session_id = %s
            """, (session_id,))
            
            chat_meta = cursor.fetchone()
            if not chat_meta:
                print(f"❌ Chat '{session_id}' not found")
                return False
            
            self.chat_title = chat_meta['chat_title']
            
            # Get all messages
            cursor.execute("""
                SELECT message_type, content FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
            """, (session_id,))
            
            rows = cursor.fetchall()
            self.session_id = session_id
            self.message_history = ChatMessageHistory()
            
            for row in rows:
                if row['message_type'] == "human":
                    self.message_history.add_message(HumanMessage(content=row['content']))
                elif row['message_type'] == "ai":
                    self.message_history.add_message(AIMessage(content=row['content']))
            
            cursor.close()
            conn.close()
            print(f"✓ Loaded chat: '{self.chat_title}' with {len(rows)} messages")
            return True
        except Exception as e:
            print(f"⚠️  Error loading chat: {str(e)}")
            return False
    
    def list_chats(self, limit: int = 20) -> List[Dict]:
        """
        List all available chats with their titles and metadata.
        
        Args:
            limit: Maximum number of chats to return
            
        Returns:
            List of chat dictionaries with title, ID, creation date, message count
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    session_id, 
                    chat_title, 
                    description,
                    created_at, 
                    updated_at,
                    query_count
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT %s
            """, (limit,))
            
            chats = []
            for row in cursor.fetchall():
                chats.append({
                    "session_id": row['session_id'],
                    "chat_title": row['chat_title'],
                    "description": row['description'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "query_count": row['query_count']
                })
            
            cursor.close()
            conn.close()
            return chats
        except Exception as e:
            print(f"⚠️  Error listing chats: {str(e)}")
            return []
    
    def get_chat_summary(self) -> Dict:
        """Get summary of current chat session"""
        history = self.message_history.messages
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT chat_title, created_at, query_count FROM conversations
                WHERE session_id = %s
            """, (self.session_id,))
            
            chat_info = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return {
                "session_id": self.session_id,
                "chat_title": chat_info['chat_title'] if chat_info else self.chat_title,
                "message_count": len(history),
                "user_queries": len([m for m in history if isinstance(m, HumanMessage)]),
                "agent_responses": len([m for m in history if isinstance(m, AIMessage)]),
                "created_at": chat_info['created_at'].isoformat() if chat_info and chat_info['created_at'] else None,
                "query_count": chat_info['query_count'] if chat_info else 0
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
        """
        Export conversation chat to JSON file.
        
        Args:
            output_file: Output filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
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
        """
        Delete a chat and all its messages.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Messages will be deleted due to CASCADE
            cursor.execute("""
                DELETE FROM conversations WHERE session_id = %s
            """, (session_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✓ Chat '{session_id}' deleted")
            return True
        except Exception as e:
            print(f"⚠️  Error deleting chat: {str(e)}")
            return False
    
    def search_chats(self, keyword: str) -> List[Dict]:
        """
        Search chats by title, description, or content.
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of matching chats
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT DISTINCT
                    c.session_id, 
                    c.chat_title, 
                    c.description,
                    c.created_at, 
                    c.updated_at
                FROM conversations c
                LEFT JOIN chat_messages cm ON c.session_id = cm.session_id
                WHERE c.chat_title ILIKE %s 
                   OR c.description ILIKE %s 
                   OR cm.content ILIKE %s
                ORDER BY c.updated_at DESC
                LIMIT 20
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "session_id": row['session_id'],
                    "chat_title": row['chat_title'],
                    "description": row['description'],
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
                })
            
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            print(f"⚠️  Error searching chats: {str(e)}")
            return []
    
    def get_chat_content(self, session_id: str) -> Dict:
        """
        Get full chat content with title and all messages.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Dictionary with chat title and formatted content
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get chat metadata
            cursor.execute("""
                SELECT chat_title, description, created_at FROM conversations
                WHERE session_id = %s
            """, (session_id,))
            
            chat_info = cursor.fetchone()
            if not chat_info:
                return None
            
            # Get all messages
            cursor.execute("""
                SELECT message_type, content, created_at FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
            """, (session_id,))
            
            messages = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                "session_id": session_id,
                "chat_title": chat_info['chat_title'],
                "description": chat_info['description'],
                "created_at": chat_info['created_at'].isoformat() if chat_info['created_at'] else None,
                "messages": [
                    {
                        "type": msg['message_type'],
                        "content": msg['content'],
                        "timestamp": msg['created_at'].isoformat() if msg['created_at'] else None
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            print(f"⚠️  Error getting chat content: {str(e)}")
            return None


# initiate the database tables on module load
if __name__ == "__main__":
    manager = ConversationHistoryManager()
    manager._initialize_database()