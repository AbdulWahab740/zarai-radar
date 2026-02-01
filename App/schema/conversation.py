"""
Pydantic schemas for FastAPI request/response validation
Used for chat, conversation, and analytics endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# CHAT MESSAGE SCHEMAS
# ============================================================================

class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message"""
    session_id: str = Field(..., description="Session ID of the conversation")
    message_type: str = Field(..., description="Type of message: 'human' or 'ai'")
    content: str = Field(..., description="Content of the message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_20231215_120000",
                "message_type": "human",
                "content": "How do I treat cotton leaf curl disease?",
                "metadata": {"type": "query"}
            }
        }


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    id: int
    session_id: str
    message_type: str
    content: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# CONVERSATION SCHEMAS
# ============================================================================
class ConversationInput(BaseModel):
    """Chat message input: query and optional session_id for conversation continuity."""
    query: str = Field(..., description="User's question about agriculture")
    session_id: Optional[str] = Field(None, description="Existing session ID for continuing conversation")


class ChatConversationResponse(BaseModel):
    """Response from RAG-powered chat endpoint."""
    answer: str = Field(..., description="Agent's answer from RAG")
    session_id: str = Field(..., description="Session ID for follow-up messages")
    source: Optional[str] = Field("Zarai Radar RAG", description="Source label for citations")
    status: str = Field("success", description="Status of the request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="e.g. domains_searched, duration_seconds") 


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation"""
    chat_title: str = Field(..., description="Title for the chat")
    description: Optional[str] = Field(None, description="Optional description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chat_title": "Cotton Disease Management",
                "description": "Discussion about cotton plant diseases and treatment"
            }
        }


class ConversationUpdate(BaseModel):
    """Schema for updating conversation metadata"""
    chat_title: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "chat_title": "Cotton Disease Management - Updated",
                "description": "Updated description"
            }
        }


class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    session_id: str
    chat_title: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    query_count: int
    message_count: Optional[int] = None
    user_queries: Optional[int] = None
    agent_responses: Optional[int] = None
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Schema for detailed conversation with messages"""
    session_id: str
    chat_title: str
    description: Optional[str]
    created_at: datetime
    messages: List[ChatMessageResponse]
    
    class Config:
        from_attributes = True


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class ConversationAnalyticCreate(BaseModel):
    """Schema for creating analytics entry"""
    session_id: str = Field(..., description="Session ID")
    query: str = Field(..., description="User query")
    response: str = Field(..., description="Agent response")
    domains_searched: Optional[str] = Field(None, description="Comma-separated domains")
    duration_seconds: Optional[float] = Field(None, description="Query processing duration")
    status: str = Field("pending", description="Status: pending, success, failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_20231215_120000",
                "query": "What are cotton diseases?",
                "response": "Cotton is affected by...",
                "domains_searched": "disease,climate",
                "duration_seconds": 2.5,
                "status": "success"
            }
        }


class ConversationAnalyticResponse(BaseModel):
    """Schema for analytics response"""
    id: int
    session_id: str
    query: str
    response: str
    domains_searched: Optional[str]
    duration_seconds: Optional[float]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# AGENT QUERY SCHEMAS
# ============================================================================

class AgentQueryRequest(BaseModel):
    """Schema for agent query request"""
    session_id: Optional[str] = Field(None, description="Existing session ID or None for new")
    chat_title: Optional[str] = Field(None, description="Title for new chat (required if session_id is None)")
    query: str = Field(..., description="User's question about agriculture")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": None,
                "chat_title": "Cotton Disease Consultation",
                "query": "How do I identify and treat cotton leaf curl virus?"
            }
        }


class AgentQueryResponse(BaseModel):
    """Schema for agent query response"""
    status: str = Field(..., description="Status of query execution")
    session_id: str = Field(..., description="Session ID for this conversation")
    answer: str = Field(..., description="Agent's response")
    reasoning: Optional[str] = Field(None, description="Agent's reasoning process")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    duration_seconds: Optional[float] = Field(None, description="Time taken to process query")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "session_id": "session_20231215_120000",
                "answer": "Cotton leaf curl virus causes...",
                "reasoning": "Agent searched disease and climate domains",
                "metadata": {
                    "domains": ["disease", "climate"],
                    "iterations": 3
                },
                "duration_seconds": 2.5
            }
        }


# ============================================================================
# SEARCH AND LIST SCHEMAS
# ============================================================================

class ConversationListResponse(BaseModel):
    """Schema for list of conversations"""
    total: int = Field(..., description="Total conversations found")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")
    conversations: List[ConversationResponse]


class ConversationSearchRequest(BaseModel):
    """Schema for searching conversations"""
    keyword: str = Field(..., description="Search keyword")
    limit: int = Field(20, ge=1, le=100, description="Max results to return")
    
    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "cotton disease",
                "limit": 10
            }
        }


class ConversationSearchResponse(BaseModel):
    """Schema for search results"""
    keyword: str
    total: int = Field(..., description="Total results found")
    results: List[ConversationResponse]


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses"""
    status: str = "error"
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Chat not found",
                "detail": "Session ID 'invalid_id' does not exist in database"
            }
        }
