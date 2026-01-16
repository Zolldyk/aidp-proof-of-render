"""
AIDP Proof of Render API

Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware import ErrorHandlerMiddleware
from app.routes import presets, render, upload

app = FastAPI(
    title="AIDP Proof of Render API",
    description="GPU rendering service with cryptographic proof of work",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
app.add_middleware(ErrorHandlerMiddleware)

# Register routers
app.include_router(presets.router, prefix="/api", tags=["Metadata"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(render.router, prefix="/api", tags=["Render"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AIDP Proof of Render API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "api": "operational",
    }
