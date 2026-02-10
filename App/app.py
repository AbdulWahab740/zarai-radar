import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
# Add app to path for imports
sys.path.insert(1, os.path.dirname(__file__))

# Load environment variables from project root
load_dotenv()


# Import routes
from routes import api_router

app = FastAPI(
    title="Zarai Radar - Agriculture Orchestrator API",
    description="AI-powered agricultural knowledge agent with ReAct reasoning and conversation memory",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from App.services.prediction import PredictionService

@app.on_event("startup")
def startup_event():
    app.state.prediction_service = PredictionService()
# Include API routes
app.include_router(api_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Zarai Radar - Agriculture Orchestrator API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "orchestrator": "/orchestrator",
            "health": "/health",
            "info": "/orchestrator/info",
            "auth": "/auth"
        }
    }


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Zarai Radar API"
    }


# Error handlers
@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": str(exc),
            "type": "ValueError"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )