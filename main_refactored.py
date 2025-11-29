"""
Domain Ownership Due Diligence Tool - FastAPI Backend (Refactored)

This is the refactored version with proper project structure.
To use this, rename it to main.py or update your start scripts.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.routes import health_router, domains_router, txt_router


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Automated WHOIS/RDAP lookups with legal risk classification",
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(domains_router)
app.include_router(txt_router)


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Data directory: {settings.data_dir}")
    print(f"Database path: {settings.database_path}")
    
    # Install Playwright browsers on first run
    if os.environ.get("INSTALL_PLAYWRIGHT", "true").lower() == "true":
        print("Checking Playwright browsers...")
        os.system("playwright install chromium")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_refactored:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

