"""
Domain Ownership Due Diligence Tool - FastAPI Backend
"""
import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from models import (
    LookupRequest,
    LookupResponse,
    DomainResult,
    TXTVerificationTask,
    TXTVerificationStatus
)
from rdap_client import RDAPClient
from csv_exporter import CSVExporter
from txt_verification import TXTVerificationManager


app = FastAPI(
    title="Domain Ownership Due Diligence API",
    description="Automated WHOIS/RDAP lookups with legal risk classification",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
API_NINJAS_KEY = os.environ.get("API_NINJAS_KEY")

# Initialize clients
rdap_client = RDAPClient(api_ninjas_key=API_NINJAS_KEY)
txt_manager = TXTVerificationManager()

# Storage for run results (in production, use a database)
results_storage = {}


def generate_run_id() -> str:
    """Generate a unique run ID."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S-") + os.urandom(4).hex()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Domain Ownership Due Diligence API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/domains/lookup", response_model=LookupResponse)
async def lookup_domains(request: LookupRequest):
    """
    Perform domain lookups and return structured data.
    
    Args:
        request: Lookup request with domains and configuration
        
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


@app.get("/api/results/{run_id}/csv")
async def get_results_csv(run_id: str):
    """
    Get results as CSV export.
    
    Args:
        run_id: Unique run identifier
        
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


@app.get("/api/txt-verification/{task_id}", response_model=TXTVerificationStatus)
async def get_txt_verification_status(task_id: str):
    """
    Get status of a TXT verification task.
    
    Args:
        task_id: TXT verification task ID
        
    Returns:
        TXT verification status
    """
    task = txt_manager.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="TXT verification task not found")
    
    instructions = txt_manager.get_verification_instructions(task_id)
    
    return TXTVerificationStatus(
        task_id=task['id'],
        domain=task['domain'],
        status=task['status'],
        expected_token=task['expected_token'],
        txt_name=task['txt_name'],
        attempts=task['attempts'],
        max_attempts=task['max_attempts'],
        instructions=instructions,
        verified_at=task.get('verified_at'),
        fail_reason=task.get('fail_reason')
    )


@app.get("/api/results/{run_id}/txt-tasks")
async def get_run_txt_tasks(run_id: str):
    """
    Get all TXT verification tasks for a run.
    
    Args:
        run_id: Run ID
        
    Returns:
        List of TXT verification tasks
    """
    tasks = txt_manager.get_tasks_by_case(run_id)
    
    return {
        "run_id": run_id,
        "tasks_count": len(tasks),
        "tasks": [
            {
                "task_id": task['id'],
                "domain": task['domain'],
                "status": task['status'],
                "expected_token": task['expected_token'],
                "txt_name": task['txt_name'],
                "attempts": task['attempts'],
                "max_attempts": task['max_attempts'],
                "created_at": task['created_at'],
                "verified_at": task.get('verified_at'),
                "fail_reason": task.get('fail_reason')
            }
            for task in tasks
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    # Install Playwright browsers on first run
    print("Checking Playwright browsers...")
    os.system("playwright install chromium")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

