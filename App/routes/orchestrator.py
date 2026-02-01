"""
Orchestrator Agent Routes - FastAPI endpoints for the agriculture orchestrator agent
Handles conversation creation, query processing, and conversation management
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import sys
import os

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schema.conversation import (
    AgentQueryRequest,
    AgentQueryResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSearchRequest,
    ConversationSearchResponse,
    ErrorResponse
)
from services import get_orchestrator_service

router = APIRouter(
    prefix="/api/orchestrator",
    tags=["Orchestrator Agent"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


# ============================================================================
# CONVERSATION MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/chat/create", response_model=dict)
async def create_chat(request: ConversationCreate):
    """
    Create a new conversation session.
    
    - **chat_title**: Title for the chat session
    - **description**: Optional description for the chat
    
    Returns a session_id to use in subsequent queries.
    """
    service = get_orchestrator_service()
    result = await service.create_conversation(
        chat_title=request.chat_title,
        description=request.description or ""
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


@router.get("/chat/{session_id}", response_model=dict)
async def get_chat(session_id: str):
    """
    Get conversation details with full message history.
    
    - **session_id**: The conversation session ID
    
    Returns the complete conversation with all messages.
    """
    service = get_orchestrator_service()
    result = await service.get_conversation(session_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result.get("data")


@router.get("/chat/{session_id}/summary", response_model=dict)
async def get_chat_summary(session_id: str):
    """
    Get a summary of a conversation.
    
    - **session_id**: The conversation session ID
    
    Returns metadata about the conversation (message count, query count, etc.).
    """
    service = get_orchestrator_service()
    result = await service.get_conversation_summary(session_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result.get("data")


@router.get("/chats", response_model=dict)
async def list_chats(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of chats to return")
):
    """
    List all conversations.
    
    - **limit**: Maximum number of conversations to return (default: 20, max: 100)
    
    Returns a paginated list of conversations with metadata.
    """
    service = get_orchestrator_service()
    result = await service.list_conversations(limit=limit)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


@router.post("/chats/search", response_model=dict)
async def search_chats(request: ConversationSearchRequest):
    """
    Search conversations by keyword.
    
    Searches in:
    - Chat titles
    - Chat descriptions
    - Message content
    
    Returns matching conversations.
    """
    service = get_orchestrator_service()
    result = await service.search_conversations(
        keyword=request.keyword,
        limit=request.limit
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


@router.delete("/chat/{session_id}", response_model=dict)
async def delete_chat(session_id: str):
    """
    Delete a conversation and all its messages.
    
    - **session_id**: The conversation session ID
    
    This action is irreversible.
    """
    service = get_orchestrator_service()
    result = await service.delete_conversation(session_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


@router.post("/chat/{session_id}/export", response_model=dict)
async def export_chat(session_id: str, filename: Optional[str] = None):
    """
    Export a conversation as JSON file.
    
    - **session_id**: The conversation session ID
    - **filename**: Optional custom filename (auto-generated if not provided)
    
    Returns the file path where the conversation was exported.
    """
    service = get_orchestrator_service()
    result = await service.export_conversation(session_id, filename)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result


# ============================================================================
# AGENT QUERY ENDPOINTS
# ============================================================================

@router.post("/query", response_model=dict)
async def process_query(request: AgentQueryRequest):
    """
    Send a query to the agriculture orchestrator agent.
    
    - **session_id**: Existing session ID (leave null for new conversation)
    - **chat_title**: Title for new chat (required if session_id is null)
    - **query**: The user's agriculture question
    
    The agent will:
    1. Analyze the query intent
    2. Retrieve relevant documents from appropriate domains
    3. Synthesize an answer based on the documents
    4. Store the interaction in the database
    
    Returns the agent's response with reasoning and metadata.
    """
    service = get_orchestrator_service()
    
    # Validate input
    if not request.session_id and not request.chat_title:
        raise HTTPException(
            status_code=400,
            detail="Either session_id or chat_title must be provided"
        )
    
    result = await service.process_query(
        session_id=request.session_id,
        query=request.query,
        chat_title=request.chat_title
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


@router.post("/query/continue/{session_id}", response_model=dict)
async def continue_conversation(
    session_id: str,
    query: str = Query(..., description="The next query in the conversation")
):
    """
    Continue an existing conversation with a new query.
    
    - **session_id**: The existing conversation session ID
    - **query**: The next question or message
    
    The agent will maintain context from previous messages in the conversation.
    """
    service = get_orchestrator_service()
    
    result = await service.process_query(
        session_id=session_id,
        query=query
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Check if the orchestrator agent service is running.
    
    Returns service status and available capabilities.
    """
    return {
        "status": "healthy",
        "service": "Agriculture Orchestrator Agent",
        "version": "1.0.0",
        "capabilities": [
            "Query processing",
            "Conversation management",
            "Conversation history",
            "Analytics tracking",
            "Export functionality"
        ]
    }


@router.get("/info")
async def service_info():
    """
    Get information about the orchestrator agent service.
    
    Returns details about domains, supported features, and configuration.
    """
    return {
        "service": "Agriculture Orchestrator Agent",
        "description": "AI-powered agricultural knowledge agent with ReAct reasoning",
        "version": "1.0.0",
        "domains": [
            "cotton diseases",
            "climate conditions",
            "soil management",
            "agricultural policy"
        ],
        "features": {
            "conversation_memory": True,
            "multi_domain_search": True,
            "analytics_tracking": True,
            "conversation_export": True,
            "conversation_search": True,
            "persistent_storage": True
        },
        "endpoints": {
            "conversation_management": [
                "POST /api/orchestrator/chat/create",
                "GET /api/orchestrator/chat/{session_id}",
                "GET /api/orchestrator/chats",
                "POST /api/orchestrator/chats/search",
                "DELETE /api/orchestrator/chat/{session_id}",
                "POST /api/orchestrator/chat/{session_id}/export"
            ],
            "query_processing": [
                "POST /api/orchestrator/query",
                "POST /api/orchestrator/query/continue/{session_id}"
            ],
            "monitoring": [
                "GET /api/orchestrator/health",
                "GET /api/orchestrator/info"
            ]
        }
    }
