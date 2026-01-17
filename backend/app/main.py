"""
AIDP Proof of Render API

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware import ErrorHandlerMiddleware
from app.routes import download, presets, render, upload
from app.services.cleanup_scheduler import start_cleanup_scheduler, stop_cleanup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    start_cleanup_scheduler()
    yield
    # Shutdown
    stop_cleanup_scheduler()

app = FastAPI(
    title="AIDP Proof of Render API",
    description="GPU rendering service with cryptographic proof of work",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(download.router, prefix="/api", tags=["Download"])


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
    """
    Detailed health check endpoint.

    Returns service health status for monitoring and deployment health checks.
    Used by Railway/Render.com for deployment verification.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }
