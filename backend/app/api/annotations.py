"""
backend/app/api/annotations.py

API router for Real-Image Annotation and Reference Benchmark Workflow
in the Cardiac Deformation Lab.

Provides CRUD endpoints, import/export, and ROI conversion for annotations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.annotations import (
    create_annotation,
    get_annotation,
    get_annotations,
    update_annotation,
    delete_annotation,
    delete_annotations_by_analysis,
    convert_annotation_to_roi,
    export_annotations,
    import_annotations,
    SUPPORTED_ANNOTATION_TYPES
)
from app.core.auth import get_current_user_optional

router = APIRouter(
    prefix="/api/annotations",
    tags=["Annotations & Benchmarking"]
)


class PointModel(BaseModel):
    x: float
    y: float


class AnnotationCreateModel(BaseModel):
    id: Optional[str] = None
    analysis_id: Optional[str] = None
    study_id: Optional[str] = None
    image_filename: str = Field(..., description="Target image filename")
    image_type: Optional[str] = "analysis_image"
    annotation_type: str = Field("point", description=f"One of: {', '.join(SUPPORTED_ANNOTATION_TYPES)}")
    annotator_label: str = Field("manual_reference", description="Descriptor or anatomical reference label")
    points: List[PointModel] = Field(..., description="List of (x, y) coordinates in original image pixel space")
    frame_index: Optional[int] = Field(0, description="Temporal frame index")
    metadata: Optional[Dict[str, Any]] = None


class AnnotationUpdateModel(BaseModel):
    annotation_type: Optional[str] = None
    annotator_label: Optional[str] = None
    points: Optional[List[PointModel]] = None
    frame_index: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_annotation_endpoint(
    payload: AnnotationCreateModel,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Create a new manual reference annotation owned by the current user."""
    if current_user and current_user.get("role") == "reviewer":
        raise HTTPException(
            status_code=403,
            detail="Reviewers have read-only access and cannot create annotations."
        )
    try:
        data = payload.dict()
        if current_user:
            data["owner_id"] = current_user.get("id")
        record = create_annotation(data)
        return record
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.get("")
def list_annotations_endpoint(
    analysis_id: Optional[str] = Query(None),
    study_id: Optional[str] = Query(None),
    image_filename: Optional[str] = Query(None),
    annotation_type: Optional[str] = Query(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieve annotations matching optional query filters and user permissions."""
    owner_id = current_user.get("id") if current_user else None
    role = current_user.get("role") if current_user else None
    return get_annotations(
        analysis_id=analysis_id,
        image_filename=image_filename,
        study_id=study_id,
        annotation_type=annotation_type,
        owner_id=owner_id,
        role=role
    )


@router.get("/image/{image_filename}")
def get_image_annotations_endpoint(
    image_filename: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieve all annotations associated with a specific image filename."""
    owner_id = current_user.get("id") if current_user else None
    role = current_user.get("role") if current_user else None
    return get_annotations(image_filename=image_filename, owner_id=owner_id, role=role)


@router.get("/analysis/{analysis_id}")
def get_analysis_annotations_endpoint(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieve all annotations associated with a specific analysis ID."""
    owner_id = current_user.get("id") if current_user else None
    role = current_user.get("role") if current_user else None
    return get_annotations(analysis_id=analysis_id, owner_id=owner_id, role=role)


@router.get("/analysis/{analysis_id}/export")
def export_annotations_endpoint(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Export all annotations for an analysis as a portable JSON package."""
    return export_annotations(analysis_id=analysis_id)


@router.post("/import")
def import_annotations_endpoint(
    package: Dict[str, Any],
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Import a previously exported annotation JSON package."""
    try:
        return import_annotations(package)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )


@router.get("/{annotation_id}")
def get_annotation_endpoint(
    annotation_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Retrieve a single annotation by ID."""
    ann = get_annotation(annotation_id)
    if not ann:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation with ID '{annotation_id}' not found."
        )

    if current_user and current_user.get("role") == "researcher":
        ann_owner = ann.get("owner_id")
        if ann_owner is not None and ann_owner != current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to view this annotation."
            )

    return ann


@router.put("/{annotation_id}")
def update_annotation_endpoint(
    annotation_id: str,
    payload: AnnotationUpdateModel,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Update an existing annotation with permission validation."""
    ann = get_annotation(annotation_id)
    if not ann:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation with ID '{annotation_id}' not found."
        )

    if current_user:
        role = current_user.get("role")
        if role == "reviewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Reviewers have read-only access and cannot modify annotations."
            )
        if role == "researcher":
            ann_owner = ann.get("owner_id")
            if ann_owner is not None and ann_owner != current_user.get("id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You can only edit your own annotations."
                )

    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    updated = update_annotation(annotation_id, update_data)
    return updated


@router.delete("/{annotation_id}")
def delete_annotation_endpoint(
    annotation_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Delete a single annotation by ID with permission check."""
    ann = get_annotation(annotation_id)
    if not ann:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation with ID '{annotation_id}' not found."
        )

    if current_user:
        role = current_user.get("role")
        if role == "reviewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Reviewers cannot delete annotations."
            )
        if role == "researcher":
            ann_owner = ann.get("owner_id")
            if ann_owner is not None and ann_owner != current_user.get("id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You can only delete your own annotations."
                )

    success = delete_annotation(annotation_id)
    return {"message": f"Annotation '{annotation_id}' deleted successfully.", "id": annotation_id}


@router.delete("/analysis/{analysis_id}")
def delete_analysis_annotations_endpoint(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Delete all annotations associated with a specific analysis."""
    if current_user and current_user.get("role") == "reviewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Reviewers cannot delete annotations."
        )

    count = delete_annotations_by_analysis(analysis_id)
    return {
        "message": f"Deleted {count} annotation(s) associated with analysis '{analysis_id}'.",
        "analysis_id": analysis_id,
        "deleted_count": count
    }


@router.post("/{annotation_id}/to-roi")
def convert_to_roi_endpoint(annotation_id: str):
    """Convert a polygon/contour annotation into an ROI configuration."""
    try:
        roi_config = convert_annotation_to_roi(annotation_id)
        return roi_config
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )

