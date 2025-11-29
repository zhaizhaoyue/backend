"""Data models for the application."""
from .domain import (
    DomainResult,
    LookupRequest,
    LookupResponse,
    TXTVerificationTask,
    TXTVerificationStatus,
    EvidenceInfo,
    FallbackEnrichment
)

__all__ = [
    "DomainResult",
    "LookupRequest",
    "LookupResponse",
    "TXTVerificationTask",
    "TXTVerificationStatus",
    "EvidenceInfo",
    "FallbackEnrichment"
]

