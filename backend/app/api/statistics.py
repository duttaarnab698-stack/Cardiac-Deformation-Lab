"""
backend/app/api/statistics.py

API router for Advanced Statistical and Research Analytics in Cardiac Deformation Lab.
Provides endpoints for:
- Full longitudinal descriptive and change statistics
- Metric correlation analysis and relationship matrix
- Computational statistical outlier detection (1.5xIQR)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.studies import get_study_by_id
from app.services.statistics import (
    calculate_study_statistics,
    calculate_metric_relationships,
    detect_computational_outliers,
)
from app.services.longitudinal import build_longitudinal_summary

router = APIRouter(
    prefix="/api/statistics",
    tags=["Statistical Analytics"]
)


@router.get("/study/{study_id}")
def get_study_statistics_endpoint(
    study_id: str,
    scope: str = Query("full_image", pattern="^(full_image|roi)$", description="Scope of metric analysis")
):
    """
    Retrieve comprehensive descriptive statistics, temporal progression changes,
    correlation matrix, and outlier detection for a longitudinal study cohort.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    stats = calculate_study_statistics(study_id=study_id, scope=scope)
    return stats


@router.get("/study/{study_id}/correlations")
def get_study_correlations_endpoint(
    study_id: str,
    scope: str = Query("full_image", pattern="^(full_image|roi)$", description="Scope of metric analysis")
):
    """
    Retrieve pairwise Pearson correlations and the metric relationship matrix.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    long_summary = build_longitudinal_summary(study_id)
    timeline = long_summary.get("timeline") or []
    correlations, matrix = calculate_metric_relationships(timeline, scope=scope)

    return {
        "study_id": study_id,
        "study_title": study.get("title", ""),
        "analysis_scope": scope,
        "observation_count": len(timeline),
        "correlations": correlations,
        "correlation_matrix": matrix,
        "disclaimer": "Correlation describes statistical association only and does not imply causation."
    }


@router.get("/study/{study_id}/outliers")
def get_study_outliers_endpoint(
    study_id: str,
    scope: str = Query("full_image", pattern="^(full_image|roi)$", description="Scope of metric analysis")
):
    """
    Retrieve computational statistical outliers flagged using the 1.5xIQR criterion.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    long_summary = build_longitudinal_summary(study_id)
    timeline = long_summary.get("timeline") or []
    outliers = detect_computational_outliers(timeline, scope=scope)
    total_count = sum(len(o) for o in outliers.values())

    return {
        "study_id": study_id,
        "study_title": study.get("title", ""),
        "analysis_scope": scope,
        "total_outliers": total_count,
        "outliers": outliers,
        "explanation": (
            "Outliers are identified using the standard 1.5xIQR rule. They are not automatically removed "
            "and may reflect image acquisition, preprocessing, motion estimation, ROI, calibration, or other computational differences."
        )
    }

