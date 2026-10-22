"""
backend/app/api/history.py

History API routes for Cardiac Deformation Lab.
Provides endpoints for querying, fetching single records, deleting individual records,
and clearing history.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional

from app.services.history import (
    get_all_history,
    get_history_by_id,
    delete_history_by_id,
    clear_all_history,
)
from app.core.auth import get_current_user_optional

router = APIRouter(
    prefix="/api/history",
    tags=["History"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def list_history(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Get saved analysis history items accessible to the current user (most recent first).
    Enriches records with associated study title if linked.
    """
    from app.services.studies import get_study_for_analysis
    owner_id = current_user.get("id") if current_user else None
    role = current_user.get("role") if current_user else None
    history = get_all_history(owner_id=owner_id, role=role)
    for item in history:
        study_info = get_study_for_analysis(item["id"])
        item["study"] = study_info
    return history


@router.get("/{analysis_id}")
def get_analysis_record(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieve a specific analysis record by ID with ownership access check.
    """
    record = get_history_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis record with ID '{analysis_id}' not found."
        )

    if current_user and current_user.get("role") == "researcher":
        rec_owner = record.get("owner_id")
        if rec_owner is not None and rec_owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to view this analysis record."
            )

    return record


@router.delete("/{analysis_id}")
def delete_analysis_record(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Delete a specific analysis record by ID with permission validation.
    """
    record = get_history_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis record with ID '{analysis_id}' not found."
        )

    if current_user:
        role = current_user.get("role")
        if role == "reviewer":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Reviewers have read-only access and cannot delete analyses."
            )
        if role == "researcher":
            rec_owner = record.get("owner_id")
            if rec_owner is not None and rec_owner != current_user.get("id"):
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You can only delete your own analysis records."
                )

    deleted = delete_history_by_id(analysis_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis record with ID '{analysis_id}' not found."
        )
    return {
        "message": f"Analysis record '{analysis_id}' deleted successfully.",
        "id": analysis_id
    }


@router.delete("")
@router.delete("/")
def clear_history(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Clear analysis history records (Admin only or all records for legacy/test).
    """
    if current_user and current_user.get("role") not in ("admin",):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only administrators can clear all analysis history."
        )

    count = clear_all_history()
    return {
        "message": "All analysis history cleared successfully.",
        "deleted_count": count
    }

