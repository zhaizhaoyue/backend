"""
Application settings and configuration management.
All API keys and configuration should be managed here.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Info
    app_name: str = "Domain Ownership Due Diligence API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Settings
    cors_origins: list = ["*"]  # Configure appropriately for production
    
    # API Keys
    api_ninjas_key: Optional[str] = None
    # Note: DeepSeek is only needed for enhanced_domain_monitor.py (parsing raw WHOIS text)
    # The core API (main_refactored.py) uses RDAP/WHOIS JSON APIs and doesn't need LLM
    deepseek_api_key: Optional[str] = None  # Optional: Only for enhanced monitoring features
    openai_api_key: Optional[str] = None    # Optional: Alternative LLM provider
    
    # Database Configuration
    database_path: str = "./data/txt_verification.db"
    
    # File Storage Paths
    data_dir: str = "./data"
    screenshots_dir: str = "./data/screenshots"
    exports_dir: str = "./data/exports"
    evidence_dir: str = "./data/evidence"
    
    # RDAP Client Configuration
    rdap_timeout: float = 30.0
    
    # TXT Verification Configuration
    txt_verification_max_attempts: int = 60
    txt_verification_check_interval: int = 60  # seconds
    
    # Legal Intelligence Configuration
    expiry_threshold_months: int = 6
    expected_group_names: list = []
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"
    
    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.screenshots_dir,
            self.exports_dir,
            self.evidence_dir,
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    This ensures settings are loaded only once.
    """
    return Settings()


# Global settings instance
settings = get_settings()

