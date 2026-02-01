from fastapi import APIRouter, HTTPException
from schema.conversation import ConversationInput, ChatConversationResponse
from services import get_orchestrator_service

router = APIRouter(tags=["Chat Conversation"])

CHAT_TITLE_DEFAULT = "Dashboard Chat"


@router.post("/chat/conversation", response_model=ChatConversationResponse)
async def chat_conversation(request: ConversationInput):
    """
    RAG-powered chat: runs the user query through the agriculture orchestrator agent.
    Uses intent detection, multi-domain retrieval (vector store), and LLM synthesis.
    Pass session_id to continue an existing conversation.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        service = get_orchestrator_service()
        result = await service.process_query(
            session_id=request.session_id or None,
            query=request.query.strip(),
            chat_title=CHAT_TITLE_DEFAULT if not request.session_id else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}",
        )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Agent returned an error"),
        )

    metadata = result.get("metadata") or {}
    domains = metadata.get("domains_searched", [])
    source = "Zarai Radar RAG"
    if isinstance(domains, list) and domains:
        source = f"RAG ({', '.join(domains)})"

    return ChatConversationResponse(
        answer=result.get("answer", ""),
        session_id=result.get("session_id", ""),
        source=source,
        status=result.get("status", "success"),
        metadata=metadata,
    )