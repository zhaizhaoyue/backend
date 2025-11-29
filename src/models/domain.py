"""
Data models for the Domain Ownership Due Diligence Tool.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class EvidenceInfo(BaseModel):
    """Evidence file information."""
    status: str  # "READY", "PENDING", "FAILED"
    format: str = "png"
    url: Optional[str] = None
    source_url: Optional[str] = None


class FallbackEnrichment(BaseModel):
    """Placeholder for future owner enrichment."""
    status: str = "NOT_IMPLEMENTED"
    notes: str = "Placeholder for future enrichment"


class DomainResult(BaseModel):
    """Complete result for a single domain lookup."""
    domain: str
    registrant_organization: Optional[str] = None
    registrar: Optional[str] = None
    registry: Optional[str] = None
    creation_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    nameservers: List[str] = []
    data_source: Optional[str] = None
    timestamp: datetime


class LookupRequest(BaseModel):
    """Request payload for domain lookup."""
    domains: List[str]


class LookupResponse(BaseModel):
    """Response payload for domain lookup."""
    run_id: str
    started_at: datetime
    finished_at: datetime
    domains_count: int
    results: List[DomainResult]
    csv_download_url: str


class TXTVerificationTask(BaseModel):
    """TXT verification task for domain control validation."""
    id: str
    case_id: str  # run_id or batch ID
    domain: str
    txt_name: str  # TXT record name (usually "@")
    expected_token: str  # Generated verification token
    status: str  # "WAITING", "VERIFIED", "FAILED", "EXPIRED"
    attempts: int = 0
    max_attempts: int = 1
    last_checked_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    fail_reason: Optional[str] = None
    dns_raw_result: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TXTVerificationStatus(BaseModel):
    """Status response for TXT verification."""
    task_id: str
    domain: str
    status: str
    expected_token: str
    txt_name: str
    attempts: int
    max_attempts: int
    instructions: Optional[str] = None
    verified_at: Optional[datetime] = None
    fail_reason: Optional[str] = None
