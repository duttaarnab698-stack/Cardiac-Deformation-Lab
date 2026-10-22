"""
backend/app/services/comparison.py

Quantitative Analysis Comparison Service for Cardiac Deformation Lab.
Calculates objective differences and compatibility assessments across 2 to 5
completed cardiac deformation analyses without making clinical or diagnostic assertions.
"""

from typing import Any, Dict, List, Optional
import math
import numpy as np

from app.services.studies import get_studies


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


def _calc_diff(val1: Optional[float], val2: Optional[float]) -> Optional[float]:
    """Calculate absolute difference val2 - val1."""
    if val1 is None or val2 is None:
        return None
    return round(val2 - val1, 6)


def _calc_pct_diff(val1: Optional[float], val2: Optional[float]) -> Optional[float]:
    """
    Calculate percentage difference ((val2 - val1) / abs(val1)) * 100.
    Returns None if val1 is zero or near-zero (|val1| <= 1e-7) or either is None.
    """
    if val1 is None or val2 is None:
        return None
    if abs(val1) <= 1e-7:
        return None
    pct = ((val2 - val1) / abs(val1)) * 100.0
    return round(pct, 2)


def extract_comparable_metrics(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured comparable metrics from an analysis history record.
    Supports both single_pair and temporal analyses, as well as full-frame and ROI scopes.
    """
    result = record.get("result") or {}
    record_type = record.get("type", "single_pair")
    cal = result.get("calibration") or record.get("summary", {}).get("calibration") or {}
    roi = result.get("roi") or record.get("summary", {}).get("roi") or {}
    disp = result.get("displacement") or {}
    phys_disp = disp.get("physical_space") if isinstance(disp, dict) else None
    strain = result.get("strain_statistics") or {}
    adv = result.get("advanced_metrics") or {}
    cardiac = result.get("cardiac_deformation") or {}
    fp_wrapper = result.get("cardiac_deformation_fingerprint") or {}
    fp = fp_wrapper.get("fingerprint") or {}
    fp_vector = fp_wrapper.get("vector") or []

    # Temporal specific extractions
    p1_temp = result.get("principal_strain_1", {}).get("summary") if isinstance(result.get("principal_strain_1"), dict) else None
    p2_temp = result.get("principal_strain_2", {}).get("summary") if isinstance(result.get("principal_strain_2"), dict) else None
    track_sum = result.get("tracking_summary") or record.get("summary", {}).get("tracking_summary")

    # 1. Displacement metrics
    d_mean = _safe_float(disp.get("mean_displacement") or disp.get("mean") or fp.get("D_mean"))
    d_max = _safe_float(disp.get("max_displacement") or disp.get("max") or fp.get("D_max"))
    d_min = _safe_float(disp.get("min_displacement") or disp.get("min"))
    d_std = _safe_float(disp.get("std_displacement") or disp.get("std"))

    # Physical displacement (if calibrated)
    phys_d_mean = _safe_float(phys_disp.get("mean_displacement")) if phys_disp else None
    phys_d_max = _safe_float(phys_disp.get("max_displacement")) if phys_disp else None
    phys_d_min = _safe_float(phys_disp.get("min_displacement")) if phys_disp else None
    phys_d_std = _safe_float(phys_disp.get("std_displacement")) if phys_disp else None
    phys_unit = phys_disp.get("unit", "mm") if phys_disp else None

    def _extract_metric_val(val: Any) -> Any:
        if isinstance(val, dict):
            return val.get("mean") if val.get("mean") is not None else val.get("value")
        return val

    # 2. Strain metrics
    exx_mean = _safe_float(_extract_metric_val(strain.get("exx")) or strain.get("mean_exx"))
    eyy_mean = _safe_float(_extract_metric_val(strain.get("eyy")) or strain.get("mean_eyy"))
    exy_mean = _safe_float(_extract_metric_val(strain.get("exy")) or strain.get("mean_exy"))
    
    p1_mean = _safe_float(
        _extract_metric_val(strain.get("principal_strain_1")) or
        strain.get("mean_principal_strain_1") or
        strain.get("mean_principal_strain") or
        (p1_temp.get("mean") if isinstance(p1_temp, dict) else p1_temp) or
        fp.get("epsilon_principal")
    )
    p1_max = _safe_float(
        _extract_metric_val(strain.get("principal_strain_1")) or
        strain.get("max_principal_strain_1") or
        strain.get("max_principal_strain") or
        (p1_temp.get("max") if isinstance(p1_temp, dict) else p1_temp) or
        fp.get("epsilon_max")
    )

    # 3. Advanced metrics
    coh_mean = _safe_float(_extract_metric_val(adv.get("motion_coherence")) or fp.get("C"))
    grad_mean = _safe_float(_extract_metric_val(adv.get("strain_gradient")) or fp.get("G_epsilon"))
    aniso_mean = _safe_float(_extract_metric_val(adv.get("anisotropy")) or fp.get("AI"))
    entropy = _safe_float(_extract_metric_val(adv.get("entropy")) or fp.get("H"))
    energy_mean = _safe_float(_extract_metric_val(adv.get("deformation_energy")))

    # 4. Cardiac deformation
    radial_mean = _safe_float(_extract_metric_val(cardiac.get("radial")))
    circ_mean = _safe_float(_extract_metric_val(cardiac.get("circumferential")))

    # 5. Temporal metrics
    tsi = _safe_float(
        (p1_temp.get("temporal_stability_index") if p1_temp else None) or
        result.get("temporal_stability", {}).get("temporal_stability_index") or
        fp.get("TSI")
    )
    temp_mean = _safe_float(p1_temp.get("mean") if p1_temp else None)
    temp_std = _safe_float(p1_temp.get("std") if p1_temp else None)
    temp_min = _safe_float(p1_temp.get("min") if p1_temp else None)
    temp_max = _safe_float(p1_temp.get("max") if p1_temp else None)

    # Visualization output paths
    outputs = result.get("outputs") or {}
    adv_outputs = result.get("advanced_outputs") or {}
    card_outputs = result.get("cardiac_deformation_outputs") or {}
    tracking_previews = result.get("tracking_previews") or {}

    # Quality control
    qc_data = result.get("quality_control") or record.get("summary", {}).get("quality_control")
    qc_score = _safe_float(qc_data.get("score")) if isinstance(qc_data, dict) else None
    qc_level = qc_data.get("level") if isinstance(qc_data, dict) else None

    return {
        "metadata": {
            "id": record.get("id"),
            "timestamp": record.get("timestamp"),
            "type": record_type,
            "image1": result.get("image1"),
            "image2": result.get("image2"),
            "frame_count": result.get("frame_count"),
            "pair_count": result.get("pair_count"),
            "quality_control": {
                "score": qc_score,
                "level": qc_level,
                "warnings_count": len(qc_data.get("warnings", [])) if isinstance(qc_data, dict) and "warnings" in qc_data else (qc_data.get("warnings_count", 0) if isinstance(qc_data, dict) else 0),
            } if qc_data else None,
            "calibration": {
                "enabled": bool(cal.get("enabled")),
                "pixel_spacing_x": cal.get("pixel_spacing_x"),
                "pixel_spacing_y": cal.get("pixel_spacing_y"),
                "unit": cal.get("unit", "mm"),
            },
            "roi": {
                "enabled": bool(roi.get("enabled")),
                "mode": roi.get("mode", "fixed") if roi.get("enabled") else "full_image",
                "type": roi.get("type"),
                "pixel_count": roi.get("pixel_count"),
            },
            "tracking_summary": track_sum,
        },
        "metrics": {
            "quality": {
                "quality_score": {"name": "Computational Quality Score", "value": qc_score, "unit": "points (0-100)"},
            },
            "displacement": {
                "mean_displacement": {"name": "Mean Displacement", "value": d_mean, "unit": "px"},
                "max_displacement": {"name": "Maximum Displacement", "value": d_max, "unit": "px"},
                "min_displacement": {"name": "Minimum Displacement", "value": d_min, "unit": "px"},
                "std_displacement": {"name": "Displacement Std Dev", "value": d_std, "unit": "px"},
                "physical_mean_displacement": {"name": "Physical Mean Displacement", "value": phys_d_mean, "unit": phys_unit},
                "physical_max_displacement": {"name": "Physical Maximum Displacement", "value": phys_d_max, "unit": phys_unit},
                "physical_min_displacement": {"name": "Physical Minimum Displacement", "value": phys_d_min, "unit": phys_unit},
                "physical_std_displacement": {"name": "Physical Displacement Std Dev", "value": phys_d_std, "unit": phys_unit},
            },
            "strain": {
                "mean_exx": {"name": "Mean Exx (Normal X)", "value": exx_mean, "unit": "dimensionless"},
                "mean_eyy": {"name": "Mean Eyy (Normal Y)", "value": eyy_mean, "unit": "dimensionless"},
                "mean_exy": {"name": "Mean Exy (Shear)", "value": exy_mean, "unit": "dimensionless"},
                "mean_principal_strain": {"name": "Mean Principal Strain (ε₁)", "value": p1_mean, "unit": "dimensionless"},
                "max_principal_strain": {"name": "Maximum Principal Strain (ε₁)", "value": p1_max, "unit": "dimensionless"},
            },
            "advanced": {
                "motion_coherence": {"name": "Motion Coherence", "value": coh_mean, "unit": "dimensionless [0-1]"},
                "strain_gradient": {"name": "Strain Gradient Magnitude", "value": grad_mean, "unit": "px⁻¹"},
                "anisotropy": {"name": "Strain Anisotropy Index", "value": aniso_mean, "unit": "dimensionless [0-1]"},
                "strain_entropy": {"name": "Strain Entropy", "value": entropy, "unit": "bits"},
                "deformation_energy": {"name": "Deformation Energy Proxy", "value": energy_mean, "unit": "dimensionless"},
            },
            "cardiac": {
                "radial_mean": {"name": "Mean Radial Strain", "value": radial_mean, "unit": "dimensionless"},
                "circumferential_mean": {"name": "Mean Circumferential Strain", "value": circ_mean, "unit": "dimensionless"},
            },
            "temporal": {
                "temporal_stability_index": {"name": "Temporal Stability Index (TSI)", "value": tsi, "unit": "dimensionless [0-1]"},
                "temporal_mean": {"name": "Temporal Mean Principal Strain", "value": temp_mean, "unit": "dimensionless"},
                "temporal_std": {"name": "Temporal Strain Std Dev", "value": temp_std, "unit": "dimensionless"},
                "temporal_min": {"name": "Temporal Minimum Strain", "value": temp_min, "unit": "dimensionless"},
                "temporal_max": {"name": "Temporal Maximum Strain", "value": temp_max, "unit": "dimensionless"},
            },
        },
        "fingerprint": {
            "dimensions": {k: _safe_float(v) for k, v in fp.items()} if fp else {},
            "vector": [(_safe_float(x) or 0.0) for x in fp_vector] if fp_vector else [],
            "normalized_vector": [(_safe_float(x) or 0.0) for x in (fp_wrapper.get("normalized_vector") or [])],
        },
        "maps": {
            "displacement_heatmap": outputs.get("displacement_heatmap"),
            "motion_vector_map": outputs.get("motion_vector_map"),
            "principal_strain_heatmap": outputs.get("principal_strain_heatmap"),
            "principal_direction_map": outputs.get("principal_direction_map"),
            "radial_map": card_outputs.get("radial_map"),
            "circumferential_map": card_outputs.get("circumferential_map"),
            "motion_coherence_map": adv_outputs.get("motion_coherence_map"),
            "strain_gradient_map": adv_outputs.get("strain_gradient_map"),
            "anisotropy_map": adv_outputs.get("anisotropy_map"),
            "deformation_energy_map": adv_outputs.get("deformation_energy_map"),
            "roi_overlay": outputs.get("roi_overlay"),
            "tracking_first": tracking_previews.get("first"),
            "tracking_middle": tracking_previews.get("middle"),
            "tracking_last": tracking_previews.get("last"),
        }
    }


def assess_study_context(analysis_ids: List[str]) -> Dict[str, Any]:
    """
    Check if the selected analyses belong to the same research study,
    different studies, or have no study association.
    """
    studies = get_studies()
    study_map: Dict[str, List[Dict[str, Any]]] = {}

    for aid in analysis_ids:
        found_studies = []
        for s in studies:
            if aid in s.get("analysis_ids", []):
                found_studies.append({"id": s["id"], "title": s["title"], "subject_code": s.get("subject_code")})
        study_map[aid] = found_studies

    # Collect unique study IDs
    all_study_ids = set()
    for s_list in study_map.values():
        for s in s_list:
            all_study_ids.add(s["id"])

    # Determine status
    if len(all_study_ids) == 1 and all(len(s_list) > 0 for s_list in study_map.values()):
        study_id = list(all_study_ids)[0]
        study_info = next((s for s in studies if s["id"] == study_id), {})
        return {
            "status": "same_study",
            "badge": "Same Study",
            "study_id": study_id,
            "study_title": study_info.get("title"),
            "subject_code": study_info.get("subject_code"),
            "message": f"All selected analyses belong to the same study: '{study_info.get('title')}'."
        }
    elif len(all_study_ids) > 1:
        return {
            "status": "different_studies",
            "badge": "Different Studies",
            "study_count": len(all_study_ids),
            "study_details": study_map,
            "message": f"Selected analyses belong to {len(all_study_ids)} different studies (Contextual comparison only)."
        }
    else:
        return {
            "status": "standalone",
            "badge": "Standalone Analyses",
            "study_details": study_map,
            "message": "Selected analyses are standalone without assigned research studies."
        }


def assess_calibration_compatibility(extracted_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess whether physical displacement can be compared or if a calibration warning must be rendered.
    """
    calibrations = [a["metadata"]["calibration"] for a in extracted_analyses]
    all_enabled = all(c.get("enabled") for c in calibrations)
    none_enabled = all(not c.get("enabled") for c in calibrations)

    if none_enabled:
        return {
            "status": "pixel_space",
            "badge": "Image-Space Only",
            "allow_physical_comparison": False,
            "unit": "px",
            "warning": None,
            "message": "All analyses use native image-space pixels (px). Displacement values are compared in pixels."
        }

    if all_enabled:
        # Check units
        units = {c.get("unit", "").lower() for c in calibrations}
        spacings_x = {c.get("pixel_spacing_x") for c in calibrations}
        spacings_y = {c.get("pixel_spacing_y") for c in calibrations}

        if len(units) == 1 and len(spacings_x) == 1 and len(spacings_y) == 1:
            return {
                "status": "compatible_physical",
                "badge": "Spatially Calibrated",
                "allow_physical_comparison": True,
                "unit": list(units)[0],
                "warning": None,
                "message": f"All analyses share identical spatial calibration ({list(spacings_x)[0]} {list(units)[0]}/px). Physical displacement comparison is valid."
            }
        else:
            return {
                "status": "discrepant_calibration",
                "badge": "Calibration Mismatch",
                "allow_physical_comparison": False,
                "unit": "px",
                "warning": "Physical displacement values use different calibration settings and should not be directly compared.",
                "message": "Selected analyses have different physical pixel spacing or units. Comparing in pixel-space."
            }

    # Mixed calibrated / uncalibrated
    return {
        "status": "mixed_calibration",
        "badge": "Mixed Calibration",
        "allow_physical_comparison": False,
        "unit": "px",
        "warning": "Some analyses have spatial calibration while others are uncalibrated. Physical displacement values cannot be compared directly.",
        "message": "Uncalibrated analyses lack physical distance definitions. Falling back to pixel-space comparison."
    }


def assess_roi_compatibility(extracted_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess whether ROI geometries or Full Image scopes differ across analyses.
    """
    rois = [a["metadata"]["roi"] for a in extracted_analyses]
    all_full = all(not r.get("enabled") for r in rois)
    all_roi = all(r.get("enabled") for r in rois)

    if all_full:
        return {
            "status": "full_image",
            "badge": "Full Image",
            "warning": None,
            "message": "All analyses evaluate full image-space pixel frames."
        }

    if all_roi:
        modes = {r.get("mode", "fixed") for r in rois}
        types = {r.get("type", "Custom") for r in rois}
        mode_str = "Tracked ROI" if "tracked" in modes else "Fixed ROI"
        if len(modes) == 1 and len(types) == 1:
            return {
                "status": "consistent_roi",
                "badge": f"{mode_str} ({list(types)[0].capitalize()})",
                "warning": None,
                "message": f"All analyses use {mode_str} with matching geometry ({list(types)[0]})."
            }
        else:
            return {
                "status": "varying_roi",
                "badge": "Varying ROI Geometries",
                "warning": "Selected analyses use different ROI geometries or tracking modes. Differences may reflect region boundaries.",
                "message": "Analyses use varied ROI geometries or tracking modes."
            }

    # Mixed Full Image vs ROI
    return {
        "status": "mixed_scope",
        "badge": "Full Image vs ROI",
        "warning": "These analyses use different analysis regions (Full Frame vs ROI) and may not be directly comparable.",
        "message": "One or more analyses evaluate a restricted Region of Interest, while others evaluate full frames."
    }


def compute_largest_quantitative_differences(
    comparison_table: List[Dict[str, Any]],
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    Find up to top_n metrics with the largest valid percentage differences
    (or absolute differences if percentage is unavailable).
    """
    valid_diffs = []
    for row in comparison_table:
        pct = row.get("pct_difference")
        diff = row.get("difference")
        if pct is not None:
            valid_diffs.append({
                "category": row["category"],
                "metric_key": row["metric_key"],
                "metric_name": row["metric_name"],
                "unit": row["unit"],
                "val1": row["val1"],
                "val2": row["val2"],
                "difference": diff,
                "pct_difference": pct,
                "sort_key": abs(pct)
            })
        elif diff is not None:
            valid_diffs.append({
                "category": row["category"],
                "metric_key": row["metric_key"],
                "metric_name": row["metric_name"],
                "unit": row["unit"],
                "val1": row["val1"],
                "val2": row["val2"],
                "difference": diff,
                "pct_difference": None,
                "sort_key": abs(diff)
            })

    valid_diffs.sort(key=lambda x: x["sort_key"], reverse=True)
    return valid_diffs[:top_n]


def compare_analyses(analysis_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute quantitative comparison across 2 to 5 analysis history records.

    Parameters
    ----------
    analysis_records : list of dict
        2 to 5 history record dictionaries containing 'id', 'type', 'result', 'summary'.

    Returns
    -------
    dict
        Comprehensive comparison payload with structured tables, pair differences,
        fingerprint multi-series, compatibility warnings, and largest differences.
    """
    n = len(analysis_records)
    if n < 2:
        raise ValueError("At least 2 analyses are required for comparison.")
    if n > 5:
        raise ValueError("Comparison supports at most 5 analyses concurrently.")

    extracted = [extract_comparable_metrics(r) for r in analysis_records]
    analysis_ids = [e["metadata"]["id"] for e in extracted]

    # Context and compatibility assessments
    study_context = assess_study_context(analysis_ids)
    calibration_compatibility = assess_calibration_compatibility(extracted)
    roi_compatibility = assess_roi_compatibility(extracted)

    # Categories to compare
    categories = [
        ("quality", "Computational Quality Control"),
        ("displacement", "Displacement Kinematics"),
        ("strain", "Small-Deformation Continuum Strain"),
        ("advanced", "Advanced Deformation Descriptors"),
        ("cardiac", "Ventricular Geometric Deformation"),
        ("temporal", "Multi-Frame Temporal Trajectory"),
    ]

    # Build comparison table
    comparison_table: List[Dict[str, Any]] = []
    category_tables: Dict[str, List[Dict[str, Any]]] = {}

    for cat_key, cat_title in categories:
        category_rows = []
        # Get all metric keys present in any of the analyses for this category
        metric_keys = []
        for a in extracted:
            for k in a["metrics"].get(cat_key, {}).keys():
                if k not in metric_keys:
                    metric_keys.append(k)

        for m_key in metric_keys:
            # Skip physical displacement rows if physical comparison is disallowed
            if m_key.startswith("physical_") and not calibration_compatibility["allow_physical_comparison"]:
                continue

            # Gather values across all analyses
            row_values = []
            m_name = m_key
            m_unit = ""

            for a in extracted:
                m_info = a["metrics"].get(cat_key, {}).get(m_key)
                if m_info:
                    m_name = m_info["name"]
                    m_unit = m_info["unit"] or ""
                    row_values.append(m_info["value"])
                else:
                    row_values.append(None)

            # Differences between Analysis 2 and Analysis 1 (if exactly 2 analyses)
            diff = None
            pct_diff = None
            if n == 2:
                diff = _calc_diff(row_values[0], row_values[1])
                pct_diff = _calc_pct_diff(row_values[0], row_values[1])

            row_data = {
                "category": cat_title,
                "category_key": cat_key,
                "metric_key": m_key,
                "metric_name": m_name,
                "unit": m_unit,
                "values": row_values,
                "val1": row_values[0] if len(row_values) > 0 else None,
                "val2": row_values[1] if len(row_values) > 1 else None,
                "difference": diff,
                "pct_difference": pct_diff,
            }
            comparison_table.append(row_data)
            category_rows.append(row_data)

        category_tables[cat_key] = category_rows

    # Largest quantitative differences (for 2 analyses, or general variance)
    largest_differences = []
    if n == 2:
        largest_differences = compute_largest_quantitative_differences(comparison_table, top_n=5)

    # Fingerprint multi-series comparison (10-D radar)
    fp_dimensions = [
        "D_mean", "D_max", "epsilon_mean", "epsilon_max",
        "epsilon_principal", "AI", "H", "G_epsilon", "C", "TSI"
    ]
    fp_series = []
    for idx, a in enumerate(extracted, start=1):
        fp_data = a["fingerprint"]
        vec = fp_data.get("vector", [])
        norm_vec = fp_data.get("normalized_vector", [])
        dims = fp_data.get("dimensions", {})
        radar_values = {}
        for dim_idx, dim_key in enumerate(fp_dimensions):
            val = norm_vec[dim_idx] if dim_idx < len(norm_vec) else 0.0
            radar_values[dim_key] = round(float(val) * 100.0, 2) if val is not None else 0.0

        fp_series.append({
            "analysis_id": a["metadata"]["id"],
            "label": f"Analysis {idx} ({a['metadata']['type']})",
            "vector": vec,
            "normalized_vector": norm_vec,
            "dimensions": dims,
            "values": radar_values,
        })

    # Compatible visualization maps
    map_keys = [
        ("principal_strain_heatmap", "Principal Strain"),
        ("displacement_heatmap", "Displacement Magnitude"),
        ("motion_vector_map", "Motion Vectors"),
        ("motion_coherence_map", "Motion Coherence"),
        ("deformation_energy_map", "Deformation Energy"),
        ("radial_map", "Radial Strain"),
        ("circumferential_map", "Circumferential Strain"),
    ]
    compatible_maps = []
    for m_key, m_title in map_keys:
        map_paths = [a["maps"].get(m_key) for a in extracted]
        # At least one analysis has this map
        if any(map_paths):
            compatible_maps.append({
                "key": m_key,
                "title": m_title,
                "paths": map_paths,
            })

    # Summary metrics for Recharts visual comparison cards
    chart_metrics = [
        {
            "key": "mean_displacement",
            "title": "Mean Displacement",
            "unit": "px",
            "data": [
                {"label": f"Analysis {i+1}", "value": a["metrics"]["displacement"]["mean_displacement"]["value"]}
                for i, a in enumerate(extracted)
            ]
        },
        {
            "key": "mean_principal_strain",
            "title": "Mean Principal Strain (ε₁)",
            "unit": "dimensionless",
            "data": [
                {"label": f"Analysis {i+1}", "value": a["metrics"]["strain"]["mean_principal_strain"]["value"]}
                for i, a in enumerate(extracted)
            ]
        },
        {
            "key": "motion_coherence",
            "title": "Motion Coherence",
            "unit": "dimensionless",
            "data": [
                {"label": f"Analysis {i+1}", "value": a["metrics"]["advanced"]["motion_coherence"]["value"]}
                for i, a in enumerate(extracted)
            ]
        },
        {
            "key": "anisotropy",
            "title": "Strain Anisotropy Index",
            "unit": "dimensionless",
            "data": [
                {"label": f"Analysis {i+1}", "value": a["metrics"]["advanced"]["anisotropy"]["value"]}
                for i, a in enumerate(extracted)
            ]
        },
        {
            "key": "temporal_stability_index",
            "title": "Temporal Stability Index (TSI)",
            "unit": "dimensionless",
            "data": [
                {"label": f"Analysis {i+1}", "value": a["metrics"]["temporal"]["temporal_stability_index"]["value"]}
                for i, a in enumerate(extracted)
            ]
        },
    ]

    return {
        "analysis_count": n,
        "analyses": extracted,
        "analysis_ids": analysis_ids,
        "study_context": study_context,
        "calibration_compatibility": calibration_compatibility,
        "roi_compatibility": roi_compatibility,
        "comparison_table": comparison_table,
        "category_tables": category_tables,
        "largest_differences": largest_differences,
        "fingerprint_comparison": {
            "dimensions": fp_dimensions,
            "parameters": fp_dimensions,
            "series": fp_series,
        },
        "compatible_maps": compatible_maps,
        "chart_metrics": chart_metrics,
        "disclaimer": (
            "This quantitative comparison summarizes mathematical variations in computed image-space "
            "and calibrated physical fields. Quantitative differences do NOT imply clinical significance, "
            "pathological abnormality, or diagnostic conclusions. Research prototype use only."
        )
    }
