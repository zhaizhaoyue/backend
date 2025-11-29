"""
Complete pipeline endpoints for domain verification.
Includes Stage 1 (API), Stage 2 (Playwright), Stage 3 (TXT setup), and Stage 4 (TXT execution).
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from complete_domain_pipeline import CompleteDomainPipeline
from config.settings import settings

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


# Request/Response Models
class PipelineRunRequest(BaseModel):
    """Request model for running complete pipeline."""
    domains: List[str]
    enable_txt_verification: bool = False
    txt_wait_time: int = 30
    txt_max_attempts: int = 10
    txt_poll_interval: int = 30


class PipelineRunResponse(BaseModel):
    """Response model for pipeline run."""
    run_id: str
    status: str
    message: str
    domains_count: int
    csv_download_url: Optional[str] = None
    report_url: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline status."""
    run_id: str
    status: str
    stage: Optional[str] = None
    progress: Optional[dict] = None
    results_available: bool = False
    csv_url: Optional[str] = None
    report_url: Optional[str] = None


# In-memory storage for pipeline status (use Redis/DB in production)
pipeline_status = {}


async def run_pipeline_task(
    run_id: str,
    domains: List[str],
    enable_txt: bool,
    txt_wait: int,
    txt_attempts: int,
    txt_interval: int
):
    """Background task to run the pipeline."""
    try:
        pipeline_status[run_id] = {
            "status": "running",
            "stage": "initializing",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Create temporary CSV file with domains
        temp_csv = Path(f"data/temp_input_{run_id}.csv")
        temp_csv.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_csv, 'w') as f:
            for i, domain in enumerate(domains, 1):
                f.write(f"{i},{domain}\n")
        
        # Run pipeline
        pipeline = CompleteDomainPipeline(run_id)
        
        pipeline_status[run_id]["stage"] = "stage1_api"
        
        await pipeline.run_complete_pipeline(
            input_csv=str(temp_csv),
            enable_txt_verification=enable_txt,
            txt_wait_time=txt_wait,
            txt_max_attempts=txt_attempts,
            txt_poll_interval=txt_interval
        )
        
        # Clean up temp file
        temp_csv.unlink(missing_ok=True)
        
        # Update status
        pipeline_status[run_id] = {
            "status": "completed",
            "stage": "finished",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "results_available": True
        }
        
    except Exception as e:
        pipeline_status[run_id] = {
            "status": "failed",
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat()
        }


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    """
    Run the complete domain verification pipeline.
    
    This endpoint triggers a background task that runs:
    - Stage 1: RDAP/WHOIS API lookup
    - Stage 2: Playwright scraping (who.is + sidn.nl for .nl domains)
    - Stage 3: TXT verification setup
    - Stage 4: TXT verification execution (if enabled)
    
    Args:
        request: Pipeline run configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        Pipeline run response with run_id
    """
    if not request.domains:
        raise HTTPException(status_code=400, detail="No domains provided")
    
    # Generate run ID
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Start background task
    background_tasks.add_task(
        run_pipeline_task,
        run_id,
        request.domains,
        request.enable_txt_verification,
        request.txt_wait_time,
        request.txt_max_attempts,
        request.txt_poll_interval
    )
    
    return PipelineRunResponse(
        run_id=run_id,
        status="started",
        message=f"Pipeline started for {len(request.domains)} domains",
        domains_count=len(request.domains),
        csv_download_url=f"/api/pipeline/{run_id}/csv",
        report_url=f"/api/pipeline/{run_id}/report"
    )


@router.get("/status/{run_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(run_id: str):
    """
    Get the status of a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        
    Returns:
        Pipeline status information
    """
    if run_id not in pipeline_status:
        # Check if run directory exists
        run_dir = Path(f"data/run_{run_id}")
        if run_dir.exists():
            return PipelineStatusResponse(
                run_id=run_id,
                status="completed",
                results_available=True,
                csv_url=f"/api/pipeline/{run_id}/csv",
                report_url=f"/api/pipeline/{run_id}/report"
            )
        else:
            raise HTTPException(status_code=404, detail="Run ID not found")
    
    status_info = pipeline_status[run_id]
    
    return PipelineStatusResponse(
        run_id=run_id,
        status=status_info["status"],
        stage=status_info.get("stage"),
        results_available=status_info.get("results_available", False),
        csv_url=f"/api/pipeline/{run_id}/csv" if status_info.get("results_available") else None,
        report_url=f"/api/pipeline/{run_id}/report" if status_info.get("results_available") else None
    )


@router.get("/{run_id}/csv")
async def download_csv(run_id: str):
    """
    Download CSV results for a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        
    Returns:
        CSV file download
    """
    csv_file = Path(f"data/run_{run_id}/results/all_results_{run_id}.csv")
    
    if not csv_file.exists():
        raise HTTPException(status_code=404, detail="CSV file not found")
    
    return FileResponse(
        path=str(csv_file),
        media_type="text/csv",
        filename=f"domain_results_{run_id}.csv"
    )


@router.get("/{run_id}/report")
async def download_report(run_id: str):
    """
    Download text report for a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        
    Returns:
        Text report file download
    """
    report_file = Path(f"data/run_{run_id}/results/FINAL_REPORT.txt")
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        path=str(report_file),
        media_type="text/plain",
        filename=f"report_{run_id}.txt"
    )


@router.get("/{run_id}/report/json")
async def download_report_json(run_id: str):
    """
    Download JSON report for a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        
    Returns:
        JSON report file download
    """
    report_file = Path(f"data/run_{run_id}/results/FINAL_REPORT.json")
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="JSON report file not found")
    
    return FileResponse(
        path=str(report_file),
        media_type="application/json",
        filename=f"report_{run_id}.json"
    )


@router.get("/{run_id}/screenshots/{filename}")
async def download_screenshot(run_id: str, filename: str):
    """
    Download a screenshot from a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        filename: Screenshot filename
        
    Returns:
        Screenshot image file
    """
    screenshot_file = Path(f"data/run_{run_id}/screenshots/{filename}")
    
    if not screenshot_file.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(
        path=str(screenshot_file),
        media_type="image/png"
    )

