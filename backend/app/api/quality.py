"""
backend/app/api/quality.py

FastAPI router for Automated Computational Analysis Quality Control (QC)
in the Cardiac Deformation Lab research prototype.
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

from app.services.history import get_history_by_id
from app.services.quality_control import evaluate_analysis_quality

router = APIRouter(
    prefix="/api/quality",
    tags=["Quality Control"]
)


@router.post("/{analysis_id}")
def compute_analysis_quality_endpoint(analysis_id: str) -> Dict[str, Any]:
    """
    Evaluate computational quality control metrics for a specific completed analysis.
    Updates the history record if quality assessment was not previously stored.
    """
    record = get_history_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with ID '{analysis_id}' not found in history."
        )

    qc_result = evaluate_analysis_quality(record)

    # Attach to in-memory record result and summary if not already present or updated
    result = record.get("result") or {}
    result["quality_control"] = qc_result

    summary = record.get("summary") or {}
    summary["quality_control"] = {
        "score": qc_result["score"],
        "level": qc_result["level"],
        "warnings_count": len(qc_result.get("warnings", [])),
    }

    return qc_result


@router.get("/{analysis_id}")
def get_analysis_quality_endpoint(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieve computational quality control assessment for a specific analysis.
    If not already evaluated, computes it on-the-fly.
    """
    record = get_history_by_id(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with ID '{analysis_id}' not found in history."
        )

    result = record.get("result") or {}
    if "quality_control" in result and result["quality_control"]:
        return result["quality_control"]

    # Compute if not present (backward compatibility for older records)
    qc_result = evaluate_analysis_quality(record)
    result["quality_control"] = qc_result

    summary = record.get("summary") or {}
    summary["quality_control"] = {
        "score": qc_result["score"],
        "level": qc_result["level"],
        "warnings_count": len(qc_result.get("warnings", [])),
    }

    return qc_result

