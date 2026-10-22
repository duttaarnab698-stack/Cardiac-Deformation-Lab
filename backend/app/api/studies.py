"""
backend/app/api/studies.py

FastAPI router for Study Management in Cardiac Deformation Lab.
Provides CRUD endpoints for studies and analysis-study relationships.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.studies import (
    create_study,
    get_studies,
    get_study_by_id,
    update_study,
    delete_study,
    add_analysis_to_study,
    remove_analysis_from_study,
)
from app.services.history import get_history_by_id
from app.core.auth import get_current_user_optional

router = APIRouter(
    prefix="/api/studies",
    tags=["Studies"]
)


class CreateStudyRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Study title")
    subject_code: Optional[str] = Field(None, description="Pseudonymous subject code (e.g. SUBJ-001)")
    description: Optional[str] = Field(None, description="Optional study notes or protocol metadata")


class UpdateStudyRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Updated study title")
    subject_code: Optional[str] = Field(None, description="Updated subject code")
    description: Optional[str] = Field(None, description="Updated study notes")


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_study_endpoint(
    payload: CreateStudyRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Create a new cardiac motion study owned by the current user."""
    if current_user and current_user.get("role") == "reviewer":
        raise HTTPException(
            status_code=403,
            detail="Reviewers have read-only access and cannot create studies."
        )
    owner_id = current_user.get("id") if current_user else None
    study = create_study(
        title=payload.title,
        subject_code=payload.subject_code,
        description=payload.description,
        owner_id=owner_id
    )
    return study


@router.get("")
@router.get("/")
def list_studies_endpoint(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieve cardiac motion studies accessible to the current user."""
    owner_id = current_user.get("id") if current_user else None
    role = current_user.get("role") if current_user else None
    return get_studies(owner_id=owner_id, role=role)


@router.get("/{study_id}")
def get_study_endpoint(
    study_id: str,
    include_analyses: bool = Query(False, description="Expand associated analysis records"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieve study details by ID with access control validation.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    # Access control: researcher cannot access another user's private study
    if current_user and current_user.get("role") == "researcher":
        study_owner = study.get("owner_id")
        if study_owner is not None and study_owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have access to this study."
            )

    if include_analyses:
        analyses_records = []
        for a_id in study.get("analysis_ids", []):
            rec = get_history_by_id(a_id)
            if rec:
                analyses_records.append(rec)
            else:
                analyses_records.append({
                    "id": a_id,
                    "deleted": True,
                    "type": "unknown",
                    "timestamp": None,
                    "summary": {}
                })
        return {
            **study,
            "analyses": analyses_records
        }

    return study


@router.put("/{study_id}")
def update_study_endpoint(
    study_id: str,
    payload: UpdateStudyRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Update study title, subject code, or description with permission validation."""
    existing_study = get_study_by_id(study_id)
    if not existing_study:
        raise HTTPException(status_code=404, detail=f"Study with ID '{study_id}' not found.")

    if current_user:
        role = current_user.get("role")
        if role == "reviewer":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Reviewers have read-only access and cannot modify studies."
            )
        if role == "researcher":
            owner_id = existing_study.get("owner_id")
            if owner_id is not None and owner_id != current_user.get("id"):
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You can only edit your own studies."
                )

    study = update_study(
        study_id=study_id,
        title=payload.title,
        subject_code=payload.subject_code,
        description=payload.description
    )
    return study


@router.delete("/{study_id}")
def delete_study_endpoint(
    study_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Delete a study with permission validation.
    """
    existing_study = get_study_by_id(study_id)
    if not existing_study:
        raise HTTPException(status_code=404, detail=f"Study with ID '{study_id}' not found.")

    if current_user:
        role = current_user.get("role")
        if role == "reviewer":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Reviewers cannot delete studies."
            )
        if role == "researcher":
            owner_id = existing_study.get("owner_id")
            if owner_id is not None and owner_id != current_user.get("id"):
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You can only delete your own studies."
                )

    success = delete_study(study_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )
    return {
        "message": f"Study '{study_id}' deleted successfully.",
        "id": study_id
    }


@router.post("/{study_id}/analyses/{analysis_id}")
def link_analysis_to_study(
    study_id: str,
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Link an existing analysis record to a study with permission check."""
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    if current_user:
        role = current_user.get("role")
        if role == "reviewer":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Reviewers cannot modify study analyses."
            )
        if role == "researcher":
            owner_id = study.get("owner_id")
            if owner_id is not None and owner_id != current_user.get("id"):
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You cannot modify studies belonging to another researcher."
                )

    updated = add_analysis_to_study(study_id, analysis_id)
    return {
        "message": f"Analysis '{analysis_id}' linked to study '{study_id}'",
        "study": updated
    }


@router.delete("/{study_id}/analyses/{analysis_id}")
def unlink_analysis_from_study(study_id: str, analysis_id: str):
    """
    Remove an analysis link from a study.
    NOTE: Does NOT delete the analysis from global history!
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    updated = remove_analysis_from_study(study_id, analysis_id)
    return {
        "message": f"Analysis '{analysis_id}' removed from study '{study_id}'",
        "study": updated
    }

