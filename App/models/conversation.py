"""
Database models for conversation history and chat management using SQLAlchemy ORM.
Used by FastAPI application to manage chat sessions, messages, and analytics.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    """
    Represents a chat conversation session with metadata.
    Each conversation has a unique session_id and contains multiple messages.
    """
    __tablename__ = "conversations"
    
    session_id = Column(String(100), primary_key=True, index=True)
    chat_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    query_count = Column(Integer, default=0)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    analytics = relationship("ConversationAnalytic", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_conversations_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Conversation(session_id={self.session_id}, title={self.chat_title})>"


class ChatMessage(Base):
    """
    Represents individual messages in a conversation.
    Can be user messages (human) or agent responses (ai).
    Stores message content and metadata for context.
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("conversations.session_id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)  # "human" or "ai"
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_messages_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, type={self.message_type}, session={self.session_id})>"


class ConversationAnalytic(Base):
    """
    Analytics data for agent queries.
    Tracks query performance, domains searched, and response status.
    Used for monitoring and improving agent behavior.
    """
    __tablename__ = "conversation_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("conversations.session_id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    domains_searched = Column(String(255), nullable=True)  # Comma-separated domains
    duration_seconds = Column(Float, nullable=True)
    status = Column(String(50), default="pending")  # pending, success, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="analytics")
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<ConversationAnalytic(id={self.id}, session={self.session_id}, status={self.status})>"
