"""
TXT verification endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from src.models.domain import TXTVerificationStatus
from src.core.txt_verification import TXTVerificationManager
from src.api.dependencies import get_txt_manager

router = APIRouter(prefix="/api/txt-verification", tags=["txt-verification"])


@router.get("/{task_id}", response_model=TXTVerificationStatus)
async def get_txt_verification_status(
    task_id: str,
    txt_manager: TXTVerificationManager = Depends(get_txt_manager)
):
    """
    Get status of a TXT verification task.
    
    Args:
        task_id: TXT verification task ID
        txt_manager: TXT verification manager instance
        
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


@router.get("/results/{run_id}/tasks")
async def get_run_txt_tasks(
    run_id: str,
    txt_manager: TXTVerificationManager = Depends(get_txt_manager)
):
    """
    Get all TXT verification tasks for a run.
    
    Args:
        run_id: Run ID
        txt_manager: TXT verification manager instance
        
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

