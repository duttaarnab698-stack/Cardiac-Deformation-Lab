"""
backend/app/api/comparison.py

Comparison API router for Cardiac Deformation Lab.
Provides endpoints for comparing multiple completed analyses, saving comparison history,
and generating comparison PDF reports.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.history import get_history_by_id
from app.services.comparison import compare_analyses
from app.services.comparison_history import (
    get_all_comparisons,
    get_comparison_by_id,
    save_comparison,
    delete_comparison_by_id,
)
from app.services.comparison_report import generate_comparison_report
from app.core.auth import get_current_user_optional

router = APIRouter(
    prefix="/api/comparison",
    tags=["Comparison"]
)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class CompareRequest(BaseModel):
    analysis_ids: List[str] = Field(..., description="List of 2 to 5 analysis IDs to compare.")


class SaveComparisonRequest(BaseModel):
    analysis_ids: List[str]
    title: Optional[str] = None
    notes: Optional[str] = None
    comparison: Optional[Dict[str, Any]] = None


class ComparisonReportRequest(BaseModel):
    comparison_id: Optional[str] = None
    analysis_ids: Optional[List[str]] = None
    comparison: Optional[Dict[str, Any]] = None
    title: Optional[str] = None


@router.post("")
def execute_comparison(
    req: CompareRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Compare 2 to 5 completed analyses retrieved from the history service.
    Returns quantitative differences, category tables, and compatibility evaluations.
    """
    ids = req.analysis_ids
    if not ids or len(ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 analysis IDs are required for quantitative comparison."
        )

    if len(ids) > 5:
        raise HTTPException(
            status_code=400,
            detail="Comparison supports at most 5 analyses concurrently."
        )

    # Check for duplicate IDs
    if len(ids) != len(set(ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate analysis IDs provided. Analyses to compare must be unique."
        )

    records = []
    for aid in ids:
        rec = get_history_by_id(aid)
        if not rec:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID '{aid}' not found in history."
            )
        if current_user and current_user.get("role") == "researcher":
            rec_owner = rec.get("owner_id")
            if rec_owner is not None and rec_owner != current_user.get("id"):
                raise HTTPException(
                    status_code=403,
                    detail=f"Forbidden: You do not have permission to access analysis '{aid}'."
                )
        records.append(rec)

    try:
        comparison_res = compare_analyses(records)

        # Build response compatible with Part 3 specification
        differences = {
            "largest_differences": comparison_res.get("largest_differences", []),
            "pair_count": 1 if len(ids) == 2 else None,
        }

        return {
            "analysis_count": comparison_res["analysis_count"],
            "analyses": comparison_res["analyses"],
            "comparison": comparison_res,
            "differences": differences,
            "study_context": comparison_res["study_context"],
            "calibration_compatibility": comparison_res["calibration_compatibility"],
            "roi_compatibility": comparison_res["roi_compatibility"],
            "comparison_table": comparison_res["comparison_table"],
            "category_tables": comparison_res["category_tables"],
            "fingerprint_comparison": comparison_res["fingerprint_comparison"],
            "compatible_maps": comparison_res["compatible_maps"],
            "chart_metrics": comparison_res["chart_metrics"],
            "disclaimer": comparison_res["disclaimer"],
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail=str(val_err)
        )
    except Exception as err:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate analysis comparison: {str(err)}"
        )


@router.post("/save")
def save_comparison_endpoint(
    req: SaveComparisonRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Persist an analysis comparison to backend/data/comparisons.json.
    """
    ids = req.analysis_ids
    if not ids or len(ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 analysis IDs are required to save a comparison."
        )

    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    # Validate ownership of referenced analyses
    for aid in ids:
        rec = get_history_by_id(aid)
        if not rec:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID '{aid}' not found."
            )
        if user_role == "researcher" and user_id:
            rec_owner = rec.get("owner_id")
            if rec_owner is not None and rec_owner != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Forbidden: You do not have permission to access analysis '{aid}'."
                )

    comparison_data = req.comparison
    if not comparison_data:
        # Re-compute comparison from history records if not provided
        records = [get_history_by_id(aid) for aid in ids]
        comparison_data = compare_analyses(records)

    saved_rec = save_comparison(
        analysis_ids=ids,
        comparison_data=comparison_data,
        title=req.title,
        notes=req.notes,
        owner_id=user_id
    )

    return {
        "message": "Comparison saved successfully",
        "comparison": saved_rec
    }


@router.get("/history")
def get_comparison_history_endpoint(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieve list of all saved comparisons.
    """
    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None
    return get_all_comparisons(owner_id=user_id, role=user_role)


@router.get("/history/{comparison_id}")
def get_comparison_by_id_endpoint(
    comparison_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieve a specific saved comparison by ID.
    """
    record = get_comparison_by_id(comparison_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Comparison with ID '{comparison_id}' not found."
        )
    if current_user and current_user.get("role") == "researcher":
        owner = record.get("owner_id")
        if owner is not None and owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to view this comparison."
            )
    return record


@router.delete("/history/{comparison_id}")
def delete_comparison_endpoint(
    comparison_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Delete a saved comparison by ID.
    """
    record = get_comparison_by_id(comparison_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Comparison with ID '{comparison_id}' not found."
        )
    if current_user and current_user.get("role") == "researcher":
        owner = record.get("owner_id")
        if owner is not None and owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to delete this comparison."
            )

    success = delete_comparison_by_id(comparison_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Comparison with ID '{comparison_id}' not found."
        )
    return {"message": "Comparison deleted successfully", "id": comparison_id}


@router.post("/report")
def create_comparison_report(
    req: ComparisonReportRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a PDF comparison report from comparison data, comparison ID, or analysis IDs.
    """
    comp_data = req.comparison
    title = req.title

    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    if not comp_data and req.comparison_id:
        saved_comp = get_comparison_by_id(req.comparison_id)
        if not saved_comp:
            raise HTTPException(
                status_code=404,
                detail=f"Comparison record '{req.comparison_id}' not found."
            )
        if user_role == "researcher" and user_id:
            c_owner = saved_comp.get("owner_id")
            if c_owner is not None and c_owner != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You do not have permission to generate reports for this comparison."
                )
        comp_data = saved_comp.get("comparison")
        if not title:
            title = saved_comp.get("title")

    if not comp_data and req.analysis_ids:
        records = []
        for aid in req.analysis_ids:
            rec = get_history_by_id(aid)
            if not rec:
                raise HTTPException(
                    status_code=404,
                    detail=f"Analysis '{aid}' not found."
                )
            if user_role == "researcher" and user_id:
                rec_owner = rec.get("owner_id")
                if rec_owner is not None and rec_owner != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Forbidden: You do not have permission to access analysis '{aid}'."
                    )
            records.append(rec)
        comp_data = compare_analyses(records)

    if not comp_data:
        raise HTTPException(
            status_code=400,
            detail="Comparison data, comparison_id, or analysis_ids must be provided to generate report."
        )

    # If comp_data is wrapped inside "comparison" key
    if "comparison" in comp_data and "analyses" in comp_data["comparison"]:
        comp_data = comp_data["comparison"]

    import uuid
    report_id = str(uuid.uuid4())[:8]
    filename = f"comparison_report_{report_id}.pdf"
    file_path = REPORTS_DIR / filename

    try:
        generate_comparison_report(
            comparison_data=comp_data,
            output_pdf_path=str(file_path),
            title=title
        )
    except Exception as err:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate comparison PDF report: {str(err)}"
        )

    return {
        "message": "Comparison report generated successfully",
        "report_filename": filename,
        "report_path": str(file_path),
        "url": f"/reports/{filename}"
    }

