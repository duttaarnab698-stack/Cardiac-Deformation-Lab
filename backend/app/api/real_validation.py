"""
backend/app/api/real_validation.py

API router for Real-Image Annotation Benchmarking in the Cardiac Deformation Lab.
Provides endpoint for evaluating algorithmic optical-flow and strain against
manual reference annotations.
"""

from fastapi import APIRouter, HTTPException
from app.services.history import get_history_by_id
from app.services.real_validation import benchmark_analysis_against_annotations

router = APIRouter(
    prefix="/api/validation/real",
    tags=["Real-Image Benchmarking"]
)


@router.post("/{analysis_id}")
def run_real_image_validation_endpoint(analysis_id: str):
    """
    Run computational benchmark comparing analysis motion and strain against
    associated manual reference annotations (landmarks, contours, and ROIs).
    """
    rec = get_history_by_id(analysis_id)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with ID '{analysis_id}' not found."
        )

    try:
        results = benchmark_analysis_against_annotations(analysis_id)
        return results
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail=str(val_err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Real-image validation benchmark failed: {str(err)}"
        )

