"""
Health check endpoints.
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from config.settings import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operational"
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

