"""
backend/app/api/longitudinal.py

API router for Longitudinal / Multi-Session Study Analysis in Cardiac Deformation Lab.
Provides endpoints for retrieving:
- Complete longitudinal analysis summaries
- Timeline series data for charting
- Metric trend statistics
"""

from fastapi import APIRouter, HTTPException

from app.services.studies import get_study_by_id
from app.services.longitudinal import (
    build_longitudinal_summary,
    collect_study_analyses,
    extract_longitudinal_metrics,
    calculate_metric_trends,
)

router = APIRouter(
    prefix="/api/longitudinal",
    tags=["Longitudinal Analysis"]
)


@router.get("/study/{study_id}")
def get_study_longitudinal_summary(study_id: str):
    """
    Retrieve comprehensive longitudinal summary for a study, including
    chronological timeline, statistical trends, first-vs-latest delta,
    and computational quality/calibration consistency indicators.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    summary = build_longitudinal_summary(study_id)
    return summary


@router.get("/study/{study_id}/timeline")
def get_study_longitudinal_timeline(study_id: str):
    """
    Retrieve timeline-optimized sequence data formatted directly for frontend charts.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    study, valid_records, warnings, info = collect_study_analyses(study_id)
    timeline = [extract_longitudinal_metrics(rec) for rec in valid_records]

    return {
        "study_id": study_id,
        "study_title": study.get("title", ""),
        "analysis_count": len(timeline),
        "timeline": timeline,
        "warnings": warnings,
        "info": info,
    }


@router.get("/study/{study_id}/trends")
def get_study_longitudinal_trends(study_id: str):
    """
    Retrieve aggregated trend statistics (first, latest, delta, pct_change, mean, std, direction)
    for all tracked deformation metrics across the study.
    """
    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    study, valid_records, warnings, info = collect_study_analyses(study_id)
    timeline = [extract_longitudinal_metrics(rec) for rec in valid_records]
    trends = calculate_metric_trends(timeline)

    return {
        "study_id": study_id,
        "study_title": study.get("title", ""),
        "analysis_count": len(timeline),
        "trends": trends,
        "warnings": warnings,
        "info": info,
    }

