"""API routes package."""
from .health import router as health_router
from .domains import router as domains_router
from .txt_verification import router as txt_router

__all__ = [
    "health_router",
    "domains_router",
    "txt_router"
]

