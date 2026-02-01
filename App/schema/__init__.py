"""
Schema package for FastAPI
"""

from .conversation import (
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationAnalyticCreate,
    ConversationAnalyticResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    ConversationListResponse,
    ConversationSearchRequest,
    ConversationSearchResponse,
    ErrorResponse,
)

__all__ = [
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "ConversationAnalyticCreate",
    "ConversationAnalyticResponse",
    "AgentQueryRequest",
    "AgentQueryResponse",
    "ConversationListResponse",
    "ConversationSearchRequest",
    "ConversationSearchResponse",
    "ErrorResponse",
]
