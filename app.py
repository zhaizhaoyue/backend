"""
Domain Ownership Due Diligence Tool - FastAPI Backend
Main Application Entry Point
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.api.routes import health, domains, txt_verification
from src.api.routes import pipeline

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Automated domain verification with RDAP/WHOIS, Playwright scraping, and TXT verification",
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(domains.router)
app.include_router(txt_verification.router)
app.include_router(pipeline.router)


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    print("=" * 80)
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print("=" * 80)
    print(f"📁 Data directory: {settings.data_dir}")
    
    # Create data directory if it doesn't exist
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    
    # Install Playwright browsers on first run
    if os.environ.get("INSTALL_PLAYWRIGHT", "true").lower() == "true":
        print("🎭 Checking Playwright browsers...")
        os.system("playwright install chromium")
    
    print("✅ Server ready!")
    print("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    print("\n🛑 Shutting down server...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.port if hasattr(settings, 'port') else 8000,
        reload=True
    )

