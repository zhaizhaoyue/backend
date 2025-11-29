"""API package for the application."""
from .dependencies import get_rdap_client, get_txt_manager, get_results_storage

__all__ = [
    "get_rdap_client",
    "get_txt_manager",
    "get_results_storage"
]

