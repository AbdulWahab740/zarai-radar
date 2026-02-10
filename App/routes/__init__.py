"""
Routes package for FastAPI application
"""

from fastapi import APIRouter

# Import all routers
from .orchestrator import router as orchestrator_router
from .chat_conversation import router as chat_router
from .auth import router as auth_router
from .farmer import router as farmer_router
from .dashboard import router as dashboard_router
from .prediction import router as prediction_router
# Create main router
api_router = APIRouter()

# Include all routers
api_router.include_router(orchestrator_router)
api_router.include_router(chat_router)
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(farmer_router, tags=["Farmer"])
api_router.include_router(dashboard_router, tags=["Dashboard"])
api_router.include_router(prediction_router, tags=["Disease Prediction"])

__all__ = ["api_router"]
