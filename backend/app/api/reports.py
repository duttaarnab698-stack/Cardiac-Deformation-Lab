"""
backend/app/api/reports.py

Report generation API router for Cardiac Deformation Lab.
Provides endpoint for creating PDF reports from historical analyses.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.services.history import get_history_by_id
from app.services.report import generate_analysis_report
from app.core.auth import get_current_user_optional

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"]
)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/{analysis_id}")
def create_report(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a PDF summary report from a saved analysis record with ownership check.
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
                detail="Forbidden: You do not have permission to generate reports for this analysis."
            )

    report_filename = f"cardiac_analysis_{analysis_id}.pdf"
    report_path = REPORTS_DIR / report_filename

    try:
        generate_analysis_report(
            history_record=record,
            output_pdf_path=str(report_path)
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analysis report: {str(error)}"
        )

    return {
        "message": "Report generated successfully",
        "analysis_id": analysis_id,
        "report_filename": report_filename,
        "report_path": str(report_path),
        "url": f"/reports/{report_filename}"
    }


@router.post("/longitudinal/{study_id}")
def create_longitudinal_report(
    study_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a publication-grade longitudinal PDF study report from all associated analyses.
    """
    from app.services.studies import get_study_by_id
    from app.services.longitudinal import build_longitudinal_summary
    from app.services.longitudinal_report import generate_longitudinal_report

    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    if current_user and current_user.get("role") == "researcher":
        st_owner = study.get("owner_id")
        if st_owner is not None and st_owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to generate reports for this study."
            )

    summary = build_longitudinal_summary(study_id)
    if summary.get("analysis_count", 0) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate longitudinal report: Study '{study_id}' has no associated analysis sessions."
        )

    report_filename = f"longitudinal_study_{study_id}.pdf"
    report_path = REPORTS_DIR / report_filename

    try:
        generate_longitudinal_report(
            summary_data=summary,
            output_pdf_path=str(report_path)
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate longitudinal report: {str(error)}"
        )

    return {
        "message": "Longitudinal report generated successfully",
        "study_id": study_id,
        "report_filename": report_filename,
        "report_path": str(report_path),
        "url": f"/reports/{report_filename}"
    }


@router.post("/statistics/{study_id}")
def create_statistics_report(
    study_id: str,
    scope: str = "full_image",
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a publication-grade PDF research statistics report from longitudinal study analyses.
    """
    from app.services.studies import get_study_by_id
    from app.services.statistics import calculate_study_statistics
    from app.services.statistics_report import generate_statistics_report

    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    if current_user and current_user.get("role") == "researcher":
        st_owner = study.get("owner_id")
        if st_owner is not None and st_owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to generate reports for this study."
            )

    stats = calculate_study_statistics(study_id=study_id, scope=scope)
    if stats.get("analysis_count", 0) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate statistics report: Study '{study_id}' has no associated analysis sessions."
        )

    report_filename = f"statistics_study_{study_id}_{scope}.pdf"
    report_path = REPORTS_DIR / report_filename

    try:
        generate_statistics_report(
            stats_data=stats,
            output_pdf_path=str(report_path)
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate statistics report: {str(error)}"
        )

    return {
        "message": "Statistics report generated successfully",
        "study_id": study_id,
        "analysis_scope": scope,
        "report_filename": report_filename,
        "report_path": str(report_path),
        "url": f"/reports/{report_filename}"
    }


@router.post("/validation/{dataset_id}")
def create_validation_report_endpoint(dataset_id: str):
    """
    Generate a publication-grade PDF validation report evaluating algorithmic motion and strain
    estimation against synthetic phantom mathematical ground truth.
    """
    from app.services.synthetic_data import get_synthetic_dataset_metadata
    from app.services.validation_report import generate_validation_report
    from app.api.synthetic import validate_synthetic_dataset_endpoint

    meta = get_synthetic_dataset_metadata(dataset_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Synthetic dataset with ID '{dataset_id}' not found."
        )

    # Run validation to obtain latest metrics & visualization paths
    val_data = validate_synthetic_dataset_endpoint(dataset_id)

    report_filename = f"validation_benchmark_{dataset_id}.pdf"
    report_path = REPORTS_DIR / report_filename

    try:
        generate_validation_report(
            validation_data=val_data,
            output_pdf_path=str(report_path)
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate validation report: {str(error)}"
        )

    return {
        "message": "Validation benchmark report generated successfully",
        "dataset_id": dataset_id,
        "report_filename": report_filename,
        "report_path": str(report_path),
        "url": f"/reports/{report_filename}"
    }


@router.post("/real-validation/{analysis_id}")
def create_real_validation_report_endpoint(
    analysis_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a publication-grade PDF validation report comparing algorithmic optical-flow and strain
    against manual reference annotations for a specific analysis.
    """
    from app.services.history import get_history_by_id
    from app.services.real_validation import benchmark_analysis_against_annotations
    from app.services.real_validation_report import generate_real_validation_report

    rec = get_history_by_id(analysis_id)
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with ID '{analysis_id}' not found."
        )

    if current_user and current_user.get("role") == "researcher":
        rec_owner = rec.get("owner_id")
        if rec_owner is not None and rec_owner != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to generate reports for this analysis."
            )

    bench_data = benchmark_analysis_against_annotations(analysis_id)
    if bench_data.get("annotation_count", 0) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate report: No manual reference annotations found for analysis '{analysis_id}'."
        )

    report_filename = f"real_validation_{analysis_id}.pdf"
    report_path = REPORTS_DIR / report_filename

    try:
        generate_real_validation_report(
            benchmark_data=bench_data,
            analysis_record=rec,
            output_pdf_path=str(report_path)
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate real validation report: {str(error)}"
        )

    return {
        "message": "Real-image reference validation report generated successfully",
        "analysis_id": analysis_id,
        "report_filename": report_filename,
        "report_path": str(report_path),
        "url": f"/reports/{report_filename}"
    }


@router.post("/research/{study_id}")
def create_comprehensive_research_report_endpoint(
    study_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a complete 21-section publication-ready Comprehensive Research Report for a study.
    """
    from app.services.studies import get_study_by_id
    from app.services.research_report import generate_comprehensive_research_report

    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    if user_role == "researcher" and user_id:
        st_owner = study.get("owner_id")
        if st_owner is not None and st_owner != user_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to generate reports for this study."
            )

    report_filename = f"comprehensive_research_{study_id}.pdf"
    report_path = REPORTS_DIR / report_filename

    try:
        meta = generate_comprehensive_research_report(
            study_id=study_id,
            output_pdf_path=str(report_path),
            owner_id=user_id
        )
    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate comprehensive research report: {str(error)}"
        )

    return {
        "message": "Comprehensive research report generated successfully",
        "report": meta,
        "study_id": study_id,
        "report_filename": report_filename,
        "report_path": str(report_path),
        "url": f"/reports/{report_filename}"
    }


@router.post("/research/{study_id}/package")
def create_research_package_endpoint(
    study_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Generate a ZIP research export package containing PDF, CSV summaries, JSON metadata, and figures.
    """
    from app.services.studies import get_study_by_id
    from app.services.research_report import create_research_export_package

    study = get_study_by_id(study_id)
    if not study:
        raise HTTPException(
            status_code=404,
            detail=f"Study with ID '{study_id}' not found."
        )

    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    if user_role == "researcher" and user_id:
        st_owner = study.get("owner_id")
        if st_owner is not None and st_owner != user_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You do not have permission to export research packages for this study."
            )

    pkg_filename = f"research_package_{study_id}.zip"
    pkg_path = REPORTS_DIR / pkg_filename

    try:
        pkg_res = create_research_export_package(
            study_id=study_id,
            output_zip_path=str(pkg_path),
            owner_id=user_id
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create research export package: {str(error)}"
        )

    return {
        "message": "Research export package generated successfully",
        "package": pkg_res,
        "study_id": study_id,
        "filename": pkg_filename,
        "path": str(pkg_path),
        "url": f"/reports/{pkg_filename}"
    }


@router.get("/history/{study_id}")
def get_reports_history_by_study_endpoint(
    study_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieve report history records associated with a specific study.
    """
    from app.services.research_report import get_reports_by_study
    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    history = get_reports_by_study(study_id, owner_id=user_id, role=user_role)
    return {
        "study_id": study_id,
        "reports": history
    }


@router.get("/history")
def get_all_reports_history_endpoint(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Retrieve all report history records accessible to the authenticated researcher.
    """
    from app.services.research_report import get_all_reports_metadata
    user_id = current_user.get("id") if current_user else None
    user_role = current_user.get("role") if current_user else None

    history = get_all_reports_metadata(owner_id=user_id, role=user_role)
    return {
        "total_reports": len(history),
        "reports": history
    }






