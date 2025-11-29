"""
Domain lookup endpoints.
"""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from src.models.domain import (
    LookupRequest,
    LookupResponse,
    DomainResult
)
from src.core.rdap_client import RDAPClient
from src.core.txt_verification import TXTVerificationManager
from src.utils.csv_exporter import CSVExporter
from src.api.dependencies import get_rdap_client, get_txt_manager, get_results_storage

router = APIRouter(prefix="/api/domains", tags=["domains"])


def generate_run_id() -> str:
    """Generate a unique run ID."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S-") + os.urandom(4).hex()


@router.post("/lookup", response_model=LookupResponse)
async def lookup_domains(
    request: LookupRequest,
    rdap_client: RDAPClient = Depends(get_rdap_client),
    txt_manager: TXTVerificationManager = Depends(get_txt_manager),
    results_storage: dict = Depends(get_results_storage)
):
    """
    Perform domain lookups and return structured data.
    
    Args:
        request: Lookup request with domains and configuration
        rdap_client: RDAP client instance
        txt_manager: TXT verification manager instance
        results_storage: Results storage dictionary
        
    Returns:
        Lookup response with results and CSV download URL
    """
    run_id = generate_run_id()
    started_at = datetime.now(timezone.utc)
    
    results = []
    
    for domain in request.domains:
        print(f"Processing domain: {domain}")
        
        # Perform RDAP/WHOIS lookup
        lookup_data, source_url = await rdap_client.lookup_domain(domain)
        
        # Create domain result
        domain_result = DomainResult(
            domain=domain,
            registrant_organization=lookup_data.get('registrant_org'),
            registrar=lookup_data.get('registrar'),
            registry=lookup_data.get('registry'),
            creation_date=lookup_data.get('creation_date'),
            expiry_date=lookup_data.get('expiry_date'),
            nameservers=lookup_data.get('nameservers', []),
            data_source=lookup_data.get('data_source'),
            timestamp=datetime.now(timezone.utc)
        )
        
        results.append(domain_result)
    
    finished_at = datetime.now(timezone.utc)
    
    # Store results for CSV export
    results_storage[run_id] = results
    
    # Create response
    response = LookupResponse(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        domains_count=len(request.domains),
        results=results,
        csv_download_url=f"/api/results/{run_id}/csv"
    )
    
    return response


@router.get("/results/{run_id}/csv")
async def get_results_csv(
    run_id: str,
    results_storage: dict = Depends(get_results_storage)
):
    """
    Get results as CSV export.
    
    Args:
        run_id: Unique run identifier
        results_storage: Results storage dictionary
        
    Returns:
        CSV file response
    """
    if run_id not in results_storage:
        raise HTTPException(status_code=404, detail="Run ID not found")
    
    results = results_storage[run_id]
    csv_content = CSVExporter.export_to_csv(results)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=domain_lookup_{run_id}.csv"
        }
    )

