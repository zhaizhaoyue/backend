"""
Dependency injection for API endpoints.
Provides singleton instances of services and storage.
"""
from functools import lru_cache
from typing import Dict
from src.core.rdap_client import RDAPClient
from src.core.txt_verification import TXTVerificationManager
from config.settings import settings


# Singleton storage for results (in production, use a database or Redis)
_results_storage: Dict = {}


@lru_cache()
def get_rdap_client() -> RDAPClient:
    """
    Get or create RDAP client instance.
    
    Returns:
        Singleton RDAPClient instance
    """
    return RDAPClient(api_ninjas_key=settings.api_ninjas_key)


@lru_cache()
def get_txt_manager() -> TXTVerificationManager:
    """
    Get or create TXT verification manager instance.
    
    Returns:
        Singleton TXTVerificationManager instance
    """
    return TXTVerificationManager(db_path=settings.database_path)


def get_results_storage() -> Dict:
    """
    Get results storage dictionary.
    
    Returns:
        Results storage dictionary
    """
    return _results_storage

