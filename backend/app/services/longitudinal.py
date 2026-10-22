"""
backend/app/services/longitudinal.py

Longitudinal and Multi-Session Study Analysis Service for Cardiac Deformation Lab.

Provides:
- Aggregation of chronological analysis sessions organized under a research study.
- Extraction of kinematic displacement, strain, coherence, anisotropy, and quality metrics.
- Deterministic trend computation (increasing, decreasing, stable, insufficient_data).
- First-vs-latest quantitative progression comparison.
- Cross-session calibration and ROI compatibility validation.
- Scientific non-diagnostic research prototype disclaimer constraints:
  Assesses computational variations in image-space kinematics across sessions.
  Does NOT provide clinical diagnosis, disease progression staging, or treatment assessment.
"""

from datetime import datetime, timezone
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from app.services.studies import get_study_by_id
from app.services.history import get_history_by_id


METRIC_DEFINITIONS = [
    {
        "key": "mean_displacement",
        "label": "Mean Displacement",
        "unit": "px",
        "description": "Average magnitude of the 2D displacement field across the evaluated field."
    },
    {
        "key": "max_displacement",
        "label": "Maximum Displacement",
        "unit": "px",
        "description": "Peak displacement magnitude observed within the evaluated region."
    },
    {
        "key": "mean_strain",
        "label": "Mean Strain",
        "unit": "",
        "description": "Spatial average of normal strain tensor components."
    },
    {
        "key": "max_strain",
        "label": "Maximum Strain",
        "unit": "",
        "description": "Peak absolute strain amplitude observed across coordinate directions."
    },
    {
        "key": "mean_principal_strain",
        "label": "Mean Principal Strain",
        "unit": "",
        "description": "Average dominant eigenvalue of infinitesimal continuum deformation."
    },
    {
        "key": "max_principal_strain",
        "label": "Maximum Principal Strain",
        "unit": "",
        "description": "Peak positive principal eigenvalue denoting maximum tensile stretch."
    },
    {
        "key": "anisotropy_index",
        "label": "Anisotropy Index",
        "unit": "",
        "description": "Directional eccentricity measuring preferential deformation orientation."
    },
    {
        "key": "strain_entropy",
        "label": "Strain Entropy",
        "unit": "",
        "description": "Information-theoretic dispersion and spatial heterogeneity of the strain field."
    },
    {
        "key": "strain_gradient",
        "label": "Strain Gradient",
        "unit": "",
        "description": "Spatial rate of change of normal deformation across adjacent pixels."
    },
    {
        "key": "motion_coherence",
        "label": "Motion Coherence",
        "unit": "",
        "description": "Local alignment of neighboring displacement vector angles."
    },
    {
        "key": "temporal_stability_index",
        "label": "Temporal Stability Index",
        "unit": "",
        "description": "Kinematic trajectory consistency across consecutive multi-frame cycles."
    },
    {
        "key": "roi_mean_displacement",
        "label": "ROI Mean Displacement",
        "unit": "px",
        "description": "Displacement magnitude bounded within the user-defined region of interest."
    },
    {
        "key": "roi_mean_strain",
        "label": "ROI Mean Strain",
        "unit": "",
        "description": "Average strain tensor magnitude within the active region of interest."
    },
    {
        "key": "roi_principal_strain",
        "label": "ROI Principal Strain",
        "unit": "",
        "description": "Dominant principal eigenvalue within the user-defined region of interest."
    },
    {
        "key": "quality_score",
        "label": "Computational Quality Score",
        "unit": "/100",
        "description": "Deterministic computational quality rating (0-100) of input and flow stability."
    }
]


def _safe_float(val: Any) -> Optional[float]:
    """Safely cast value to float or return None if missing/invalid."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 6)
    except (ValueError, TypeError):
        return None


def collect_study_analyses(study_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[str], List[str]]:
    """
    Retrieve all valid analysis records associated with a given study ID,
    sorted chronologically (oldest to newest).

    Returns
    -------
    study : dict or None
        Study record from studies service.
    analyses : list of dict
        Chronologically sorted list of complete history records.
    warnings : list of str
        Warnings about missing or invalid analyses.
    info : list of str
        Informational notes.
    """
    study = get_study_by_id(study_id)
    if not study:
        return None, [], ["Study not found."], []

    analysis_ids = study.get("analysis_ids") or []
    warnings: List[str] = []
    info: List[str] = []

    if not analysis_ids:
        info.append("Study currently has zero associated analysis sessions.")
        return study, [], warnings, info

    valid_records: List[Dict[str, Any]] = []
    missing_ids: List[str] = []

    for aid in analysis_ids:
        record = get_history_by_id(aid)
        if record is None:
            missing_ids.append(aid)
        else:
            valid_records.append(record)

    if missing_ids:
        warnings.append(
            f"{len(missing_ids)} analysis ID(s) linked to this study were not found in history "
            f"(they may have been cleared or deleted from the prototype cache)."
        )

    # Sort chronologically by timestamp ascending (earliest analysis first)
    def _parse_timestamp(rec: Dict[str, Any]) -> str:
        ts = rec.get("timestamp") or ""
        return str(ts)

    valid_records.sort(key=_parse_timestamp)

    return study, valid_records, warnings, info


def extract_longitudinal_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract standardized scalar deformation and quality metrics from
    a single-pair or temporal analysis record.
    """
    record_id = record.get("id")
    timestamp = record.get("timestamp")
    record_type = record.get("type", "single_pair")
    result = record.get("result") or {}
    summary = record.get("summary") or {}

    disp = result.get("displacement") or {}
    strain = result.get("strain_statistics") or {}
    adv = result.get("advanced_metrics") or {}
    fp_wrapper = result.get("cardiac_deformation_fingerprint") or {}
    fp = fp_wrapper.get("fingerprint") or {}

    p1_temp = result.get("principal_strain_1", {}).get("summary") if isinstance(result.get("principal_strain_1"), dict) else None

    # Quality control
    qc_data = result.get("quality_control") or summary.get("quality_control") or {}
    qc_score = _safe_float(qc_data.get("score"))
    qc_level = qc_data.get("level") if isinstance(qc_data, dict) else None

    # Calibration info
    cal_obj = result.get("calibration") or summary.get("calibration") or {}
    cal_enabled = bool(cal_obj.get("enabled"))
    cal_info = {
        "enabled": cal_enabled,
        "pixel_spacing_x": _safe_float(cal_obj.get("pixel_spacing_x")),
        "pixel_spacing_y": _safe_float(cal_obj.get("pixel_spacing_y")),
        "unit": cal_obj.get("unit", "mm") if cal_enabled else "px",
    }

    # ROI info and metrics
    roi_obj = result.get("roi") or summary.get("roi") or {}
    roi_enabled = bool(roi_obj.get("enabled"))
    roi_metrics_dict = result.get("roi_metrics") or {}
    roi_disp = roi_metrics_dict.get("displacement") or {}
    roi_strain = roi_metrics_dict.get("strain_statistics") or {}

    roi_info = {
        "enabled": roi_enabled,
        "mode": roi_obj.get("mode", "fixed") if roi_enabled else None,
        "type": roi_obj.get("type") if roi_enabled else None,
        "pixel_count": roi_obj.get("pixel_count") or roi_metrics_dict.get("pixel_count"),
    }

    def _extract_metric_val(val: Any) -> Any:
        if isinstance(val, dict):
            return val.get("mean") if val.get("mean") is not None else val.get("value")
        return val

    # Scalar values extraction
    d_mean = _safe_float(disp.get("mean_displacement") or disp.get("mean") or fp.get("D_mean"))
    d_max = _safe_float(disp.get("max_displacement") or disp.get("max") or fp.get("D_max"))

    # Mean and max strain
    s_mean = _safe_float(
        fp.get("epsilon_mean") or
        _extract_metric_val(strain.get("exx")) or
        strain.get("mean_exx") or
        strain.get("mean_strain")
    )
    s_max = _safe_float(
        fp.get("epsilon_max") or
        _extract_metric_val(strain.get("exx")) or
        strain.get("max_exx") or
        strain.get("max_strain")
    )

    p1_mean = _safe_float(
        _extract_metric_val(strain.get("principal_strain_1")) or
        strain.get("mean_principal_strain") or
        strain.get("mean_principal_strain_1") or
        (p1_temp.get("mean") if isinstance(p1_temp, dict) else p1_temp) or
        fp.get("epsilon_principal")
    )
    p1_max = _safe_float(
        _extract_metric_val(strain.get("principal_strain_1")) or
        strain.get("max_principal_strain") or
        strain.get("max_principal_strain_1") or
        (p1_temp.get("max") if isinstance(p1_temp, dict) else p1_temp) or
        fp.get("epsilon_max")
    )

    aniso = _safe_float(_extract_metric_val(adv.get("anisotropy")) or fp.get("AI"))
    entropy = _safe_float(_extract_metric_val(adv.get("entropy")) or fp.get("H"))
    grad = _safe_float(_extract_metric_val(adv.get("strain_gradient")) or fp.get("G_epsilon"))
    coh = _safe_float(_extract_metric_val(adv.get("motion_coherence")) or fp.get("C"))

    tsi = _safe_float(
        (p1_temp.get("temporal_stability_index") if isinstance(p1_temp, dict) else None) or
        result.get("temporal_stability", {}).get("temporal_stability_index") or
        fp.get("TSI")
    )

    roi_d_mean = _safe_float(roi_disp.get("mean_displacement") or roi_disp.get("mean"))
    roi_s_mean = _safe_float(
        roi_strain.get("mean_strain") or
        _extract_metric_val(roi_strain.get("exx"))
    )
    roi_p_mean = _safe_float(_extract_metric_val(roi_strain.get("principal_strain_1")))

    metrics = {
        "mean_displacement": d_mean,
        "max_displacement": d_max,
        "mean_strain": s_mean,
        "max_strain": s_max,
        "mean_principal_strain": p1_mean,
        "max_principal_strain": p1_max,
        "anisotropy_index": aniso,
        "strain_entropy": entropy,
        "strain_gradient": grad,
        "motion_coherence": coh,
        "temporal_stability_index": tsi,
        "roi_mean_displacement": roi_d_mean,
        "roi_mean_strain": roi_s_mean,
        "roi_principal_strain": roi_p_mean,
        "quality_score": qc_score,
    }

    return {
        "analysis_id": record_id,
        "timestamp": timestamp,
        "type": record_type,
        "quality_level": qc_level,
        "calibration": cal_info,
        "roi": roi_info,
        "metrics": metrics,
    }


def calculate_metric_trends(
    timeline: List[Dict[str, Any]],
    relative_stability_threshold: float = 0.05
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate statistical trends for each tracked metric across the longitudinal timeline.

    Parameters
    ----------
    timeline : list of dict
        Extracted timeline items from `extract_longitudinal_metrics`.
    relative_stability_threshold : float
        Fractional change threshold (default: 5% or 0.05) below which changes
        are designated as 'stable'.

    Returns
    -------
    dict
        Dictionary keyed by metric key with trend indicators and descriptive statistics.
    """
    trends: Dict[str, Dict[str, Any]] = {}

    for m_def in METRIC_DEFINITIONS:
        m_key = m_def["key"]
        values: List[float] = []

        for item in timeline:
            v = item.get("metrics", {}).get(m_key)
            if v is not None and isinstance(v, (int, float)):
                values.append(float(v))

        n_obs = len(values)

        if n_obs == 0:
            trends[m_key] = {
                "metric_key": m_key,
                "label": m_def["label"],
                "unit": m_def["unit"],
                "first_value": None,
                "latest_value": None,
                "absolute_change": None,
                "percentage_change": None,
                "minimum": None,
                "maximum": None,
                "mean": None,
                "standard_deviation": None,
                "observation_count": 0,
                "trend_direction": "insufficient_data",
            }
            continue

        if n_obs == 1:
            val = values[0]
            trends[m_key] = {
                "metric_key": m_key,
                "label": m_def["label"],
                "unit": m_def["unit"],
                "first_value": round(val, 6),
                "latest_value": round(val, 6),
                "absolute_change": 0.0,
                "percentage_change": 0.0,
                "minimum": round(val, 6),
                "maximum": round(val, 6),
                "mean": round(val, 6),
                "standard_deviation": 0.0,
                "observation_count": 1,
                "trend_direction": "insufficient_data",
            }
            continue

        # N >= 2 valid observations
        first_val = values[0]
        latest_val = values[-1]
        abs_change = round(latest_val - first_val, 6)

        pct_change: Optional[float] = None
        if abs(first_val) > 1e-7:
            pct_change = round(((latest_val - first_val) / abs(first_val)) * 100.0, 2)

        # Determine trend direction using transparent deterministic relative threshold
        rel_diff = abs(abs_change) / (abs(first_val) if abs(first_val) > 1e-7 else 1.0)
        
        # If absolute and relative change is tiny, designate as stable
        if (abs(first_val) > 1e-7 and rel_diff < relative_stability_threshold) or (abs(first_val) <= 1e-7 and abs(abs_change) < 1e-4):
            direction = "stable"
        elif latest_val > first_val:
            direction = "increasing"
        else:
            direction = "decreasing"

        mean_val = round(sum(values) / n_obs, 6)
        std_val = round(statistics.stdev(values), 6) if n_obs > 1 else 0.0

        trends[m_key] = {
            "metric_key": m_key,
            "label": m_def["label"],
            "unit": m_def["unit"],
            "first_value": round(first_val, 6),
            "latest_value": round(latest_val, 6),
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "minimum": round(min(values), 6),
            "maximum": round(max(values), 6),
            "mean": mean_val,
            "standard_deviation": std_val,
            "observation_count": n_obs,
            "trend_direction": direction,
        }

    return trends


def compare_first_and_latest(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a direct side-by-side comparison between the first (baseline)
    and latest (most recent) analysis in the study.
    """
    if len(timeline) < 2:
        return {
            "available": False,
            "reason": "Requires at least 2 analysis sessions to evaluate comparative progression.",
            "first": timeline[0] if timeline else None,
            "latest": timeline[-1] if timeline else None,
            "metrics": {},
        }

    first = timeline[0]
    latest = timeline[-1]
    comparison_metrics: Dict[str, Any] = {}

    for m_def in METRIC_DEFINITIONS:
        m_key = m_def["key"]
        v1 = first.get("metrics", {}).get(m_key)
        v2 = latest.get("metrics", {}).get(m_key)

        abs_diff: Optional[float] = None
        pct_diff: Optional[float] = None
        trend = "insufficient_data"

        if v1 is not None and v2 is not None:
            abs_diff = round(v2 - v1, 6)
            if abs(v1) > 1e-7:
                pct_diff = round(((v2 - v1) / abs(v1)) * 100.0, 2)

            rel_diff = abs(abs_diff) / (abs(v1) if abs(v1) > 1e-7 else 1.0)
            if (abs(v1) > 1e-7 and rel_diff < 0.05) or (abs(v1) <= 1e-7 and abs(abs_diff) < 1e-4):
                trend = "stable"
            elif v2 > v1:
                trend = "increasing"
            else:
                trend = "decreasing"

        comparison_metrics[m_key] = {
            "label": m_def["label"],
            "unit": m_def["unit"],
            "first_value": v1,
            "latest_value": v2,
            "absolute_change": abs_diff,
            "percentage_change": pct_diff,
            "trend": trend,
        }

    return {
        "available": True,
        "first_analysis_id": first.get("analysis_id"),
        "first_timestamp": first.get("timestamp"),
        "first_type": first.get("type"),
        "latest_analysis_id": latest.get("analysis_id"),
        "latest_timestamp": latest.get("timestamp"),
        "latest_type": latest.get("type"),
        "metrics": comparison_metrics,
    }


def evaluate_calibration_consistency(timeline: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Validate whether analyses across the study use identical spatial calibration.
    """
    warnings: List[str] = []
    info: List[str] = []

    if not timeline:
        return {"status": "none", "details": "No analyses."}, warnings, info

    cal_configs = [item.get("calibration", {}) for item in timeline]
    enabled_count = sum(1 for c in cal_configs if c.get("enabled"))

    if enabled_count == 0:
        status = "uncalibrated"
        details = "All sessions are uncalibrated (pixel-space)."
        info.append(
            "Longitudinal displacement comparisons are reported in image-space pixels because physical calibration is unavailable."
        )
    elif enabled_count == len(cal_configs):
        # All enabled, check if spacing and unit match
        first_c = cal_configs[0]
        mismatch = False
        for c in cal_configs[1:]:
            if (
                c.get("unit") != first_c.get("unit") or
                c.get("pixel_spacing_x") != first_c.get("pixel_spacing_x") or
                c.get("pixel_spacing_y") != first_c.get("pixel_spacing_y")
            ):
                mismatch = True
                break

        if mismatch:
            status = "mixed"
            details = "Analyses have differing physical calibration spacing or units."
            warnings.append(
                "Longitudinal physical-unit comparison may be unreliable because calibration settings differ between analyses."
            )
        else:
            status = "consistent"
            details = f"Consistent physical calibration applied across all sessions ({first_c.get('pixel_spacing_x')} x {first_c.get('pixel_spacing_y')} {first_c.get('unit')})."
    else:
        status = "mixed"
        details = f"{enabled_count} of {len(cal_configs)} analyses have physical calibration."
        warnings.append(
            "Longitudinal physical-unit comparison may be unreliable because calibration settings differ between analyses."
        )

    return {"status": status, "details": details, "calibrated_count": enabled_count, "total_count": len(timeline)}, warnings, info


def evaluate_roi_consistency(timeline: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Validate whether analyses across the study consistently use ROIs or full-image evaluations.
    """
    warnings: List[str] = []
    info: List[str] = []

    if not timeline:
        return {"status": "none", "details": "No analyses."}, warnings, info

    roi_configs = [item.get("roi", {}) for item in timeline]
    roi_count = sum(1 for r in roi_configs if r.get("enabled"))

    if roi_count == 0:
        status = "none"
        details = "All sessions evaluated full-image deformation fields."
    elif roi_count == len(roi_configs):
        status = "consistent"
        details = "All sessions evaluated user-defined Regions of Interest (ROI)."
    else:
        status = "mixed"
        details = f"{roi_count} of {len(roi_configs)} analyses used ROI masking."
        warnings.append(
            "Some analyses in this study used a Region of Interest (ROI) while others evaluated the full image. Comparisons between full-image and ROI metrics may not be directly comparable."
        )

    return {"status": status, "details": details, "roi_count": roi_count, "total_count": len(timeline)}, warnings, info


def summarize_study_quality(timeline: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Summarize Computational Quality Control (QC) status across the study.
    """
    warnings: List[str] = []
    info: List[str] = []

    qc_scores: List[float] = []
    high_count = 0
    mod_count = 0
    low_count = 0
    unassessed_count = 0

    for item in timeline:
        sc = item.get("metrics", {}).get("quality_score")
        lvl = item.get("quality_level")
        if sc is not None and isinstance(sc, (int, float)):
            qc_scores.append(float(sc))
            if lvl == "High" or sc >= 80:
                high_count += 1
            elif lvl == "Moderate" or sc >= 60:
                mod_count += 1
            else:
                low_count += 1
        else:
            unassessed_count += 1

    avg_score = round(sum(qc_scores) / len(qc_scores), 1) if qc_scores else None
    min_score = min(qc_scores) if qc_scores else None
    max_score = max(qc_scores) if qc_scores else None

    if low_count > 0:
        warnings.append(
            f"Study contains {low_count} low-quality computational analysis session(s). Technical artifacts may reduce longitudinal measurement reliability."
        )

    if unassessed_count > 0:
        info.append("Quality assessment not available for one or more historical analyses.")

    summary = {
        "average_score": avg_score,
        "min_score": min_score,
        "max_score": max_score,
        "high_count": high_count,
        "moderate_count": mod_count,
        "low_count": low_count,
        "unassessed_count": unassessed_count,
        "total_count": len(timeline),
    }

    return summary, warnings, info


def build_longitudinal_summary(study_id: str) -> Dict[str, Any]:
    """
    Construct complete longitudinal multi-session study analysis payload.

    Parameters
    ----------
    study_id : str
        Target study ID.

    Returns
    -------
    dict
        Full longitudinal summary response.
    """
    study, valid_records, study_warns, study_info = collect_study_analyses(study_id)
    if not study:
        return {
            "study_id": study_id,
            "error": "Study not found",
            "analysis_count": 0,
            "timeline": [],
            "trends": {},
            "first_vs_latest": {"available": False},
            "quality_summary": {},
            "calibration_consistency": {"status": "none"},
            "roi_consistency": {"status": "none"},
            "warnings": study_warns,
            "info": study_info,
        }

    # Extract metrics for each timeline item
    timeline = [extract_longitudinal_metrics(rec) for rec in valid_records]

    # Calculate trends
    trends = calculate_metric_trends(timeline)

    # First vs latest comparative analysis
    first_vs_latest = compare_first_and_latest(timeline)

    # Quality control summary
    quality_summary, qc_warns, qc_info = summarize_study_quality(timeline)

    # Calibration consistency
    cal_consistency, cal_warns, cal_info = evaluate_calibration_consistency(timeline)

    # ROI consistency
    roi_consistency, roi_warns, roi_info = evaluate_roi_consistency(timeline)

    all_warnings = study_warns + cal_warns + roi_warns + qc_warns
    all_info = study_info + cal_info + roi_info + qc_info

    first_date = timeline[0]["timestamp"] if timeline else None
    latest_date = timeline[-1]["timestamp"] if timeline else None

    return {
        "study_id": study.get("id"),
        "study_title": study.get("title", "Untitled Study"),
        "subject_code": study.get("subject_code", ""),
        "description": study.get("description", ""),
        "created_at": study.get("created_at"),
        "updated_at": study.get("updated_at"),
        "analysis_count": len(timeline),
        "first_analysis_date": first_date,
        "latest_analysis_date": latest_date,
        "timeline": timeline,
        "trends": trends,
        "first_vs_latest": first_vs_latest,
        "quality_summary": quality_summary,
        "calibration_consistency": cal_consistency,
        "roi_consistency": roi_consistency,
        "warnings": all_warnings,
        "info": all_info,
        "disclaimer": (
            "Longitudinal analysis describes computational changes in image-derived measurements "
            "across analysis sessions. It is an experimental research tool and NOT a clinical diagnosis, "
            "disease progression staging, or treatment response assessment."
        )
    }
