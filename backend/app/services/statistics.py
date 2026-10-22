"""
backend/app/services/statistics.py

Advanced Statistical and Research Analytics Service for Cardiac Deformation Lab.
Provides:
- Reusable descriptive statistics (mean, median, std, variance, min, max, p25, p75, iqr)
- Temporal measurement change analysis (delta, pct_change, consecutive diffs, CV, standardized difference)
- Pearson correlation analysis & metric relationship matrix
- Computational outlier detection via 1.5 * IQR rule with Quality Control context
- Dual analysis scope support: Full Image vs. Region of Interest (ROI)
- Strict non-diagnostic research prototype constraints:
  Summarizes mathematical image-derived properties across sessions.
  Does NOT assert clinical disease progression, treatment response, or medical diagnoses.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.services.studies import get_study_by_id
from app.services.longitudinal import (
    build_longitudinal_summary,
    collect_study_analyses,
    extract_longitudinal_metrics,
    evaluate_calibration_consistency,
    evaluate_roi_consistency,
    summarize_study_quality,
)

# Core tracked metrics for statistical research modeling
METRIC_REGISTRY = [
    {
        "key": "mean_displacement",
        "label": "Mean Displacement",
        "unit": "px",
        "category": "displacement",
        "roi_key": "roi_mean_displacement"
    },
    {
        "key": "max_displacement",
        "label": "Max Displacement",
        "unit": "px",
        "category": "displacement",
        "roi_key": None
    },
    {
        "key": "mean_strain",
        "label": "Mean Normal Strain",
        "unit": "",
        "category": "strain",
        "roi_key": "roi_mean_strain"
    },
    {
        "key": "max_strain",
        "label": "Max Normal Strain",
        "unit": "",
        "category": "strain",
        "roi_key": None
    },
    {
        "key": "mean_principal_strain",
        "label": "Mean Principal Strain",
        "unit": "",
        "category": "strain",
        "roi_key": "roi_principal_strain"
    },
    {
        "key": "max_principal_strain",
        "label": "Max Principal Strain",
        "unit": "",
        "category": "strain",
        "roi_key": None
    },
    {
        "key": "anisotropy_index",
        "label": "Anisotropy Index",
        "unit": "",
        "category": "advanced",
        "roi_key": None
    },
    {
        "key": "strain_entropy",
        "label": "Strain Entropy",
        "unit": "",
        "category": "advanced",
        "roi_key": None
    },
    {
        "key": "strain_gradient",
        "label": "Strain Gradient",
        "unit": "",
        "category": "advanced",
        "roi_key": None
    },
    {
        "key": "motion_coherence",
        "label": "Motion Coherence",
        "unit": "",
        "category": "advanced",
        "roi_key": None
    },
    {
        "key": "temporal_stability_index",
        "label": "Temporal Stability Index",
        "unit": "",
        "category": "temporal",
        "roi_key": None
    },
    {
        "key": "quality_score",
        "label": "Quality Control Score",
        "unit": "/100",
        "category": "quality",
        "roi_key": None
    }
]


def _filter_valid_floats(values: List[Any]) -> List[float]:
    """Filter out None, NaN, Infinite, and non-numeric values."""
    valid: List[float] = []
    for v in values:
        if v is None:
            continue
        try:
            f = float(v)
            if not math.isnan(f) and not math.isinf(f):
                valid.append(f)
        except (ValueError, TypeError):
            continue
    return valid


def calculate_percentiles(values: List[float]) -> Dict[str, Optional[float]]:
    """
    Calculate 25th, 50th (median), and 75th percentiles and Interquartile Range (IQR).
    """
    valid = _filter_valid_floats(values)
    if not valid:
        return {
            "p25": None,
            "median": None,
            "p75": None,
            "iqr": None
        }

    arr = np.array(valid, dtype=float)
    p25 = float(np.percentile(arr, 25))
    median = float(np.percentile(arr, 50))
    p75 = float(np.percentile(arr, 75))
    iqr = float(p75 - p25)

    return {
        "p25": round(p25, 6),
        "median": round(median, 6),
        "p75": round(p75, 6),
        "iqr": round(iqr, 6)
    }


def calculate_variability(values: List[float]) -> Dict[str, Optional[float]]:
    """
    Calculate variance, standard deviation, coefficient of variation (CV), and IQR.
    """
    valid = _filter_valid_floats(values)
    n = len(valid)
    if n == 0:
        return {"std": None, "variance": None, "cv": None, "iqr": None}
    if n == 1:
        return {"std": 0.0, "variance": 0.0, "cv": 0.0, "iqr": 0.0}

    arr = np.array(valid, dtype=float)
    mean_val = float(np.mean(arr))
    var_val = float(np.var(arr, ddof=1))
    std_val = float(np.std(arr, ddof=1))

    # Coefficient of Variation = (std / |mean|) * 100
    cv_val = None
    if abs(mean_val) > 1e-7:
        cv_val = round((std_val / abs(mean_val)) * 100.0, 2)

    pct_dict = calculate_percentiles(valid)

    return {
        "std": round(std_val, 6),
        "variance": round(var_val, 6),
        "cv": cv_val,
        "iqr": pct_dict["iqr"]
    }


def calculate_descriptive_statistics(values: List[Any]) -> Dict[str, Any]:
    """
    Calculate standard univariate descriptive statistics for a series.
    """
    valid = _filter_valid_floats(values)
    n = len(valid)

    if n == 0:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "std": None,
            "variance": None,
            "min": None,
            "max": None,
            "range": None,
            "p25": None,
            "p75": None,
            "iqr": None,
            "status": "insufficient_data"
        }

    arr = np.array(valid, dtype=float)
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))
    range_v = float(max_v - min_v)
    mean_v = float(np.mean(arr))

    var_dict = calculate_variability(valid)
    pct_dict = calculate_percentiles(valid)

    return {
        "count": n,
        "mean": round(mean_v, 6),
        "median": pct_dict["median"],
        "std": var_dict["std"],
        "variance": var_dict["variance"],
        "min": round(min_v, 6),
        "max": round(max_v, 6),
        "range": round(range_v, 6),
        "p25": pct_dict["p25"],
        "p75": pct_dict["p75"],
        "iqr": pct_dict["iqr"],
        "status": "computed" if n >= 2 else "single_observation"
    }


def calculate_effect_size(first_values: List[float], latest_values: List[float]) -> Optional[float]:
    """
    Calculate a transparent Cohen-style standardized computational difference:
    d = (latest_val - first_val) / pooled_std
    """
    v1 = _filter_valid_floats(first_values)
    v2 = _filter_valid_floats(latest_values)

    if not v1 or not v2:
        return None

    # For longitudinal baseline vs terminal observations
    mean1 = float(np.mean(v1))
    mean2 = float(np.mean(v2))

    all_vals = v1 + v2
    if len(all_vals) < 2:
        return None

    std_pooled = float(np.std(all_vals, ddof=1))
    if std_pooled <= 1e-7:
        return 0.0

    d = (mean2 - mean1) / std_pooled
    return round(d, 4)


def calculate_change_statistics(values: List[Any]) -> Dict[str, Any]:
    """
    Calculate longitudinal change metrics across chronological sessions.
    """
    valid = _filter_valid_floats(values)
    n = len(valid)

    if n < 2:
        first_v = round(valid[0], 6) if n == 1 else None
        return {
            "observation_count": n,
            "first_value": first_v,
            "latest_value": first_v,
            "absolute_change": 0.0 if n == 1 else None,
            "percentage_change": 0.0 if n == 1 else None,
            "mean_consecutive_change": None,
            "std_consecutive_change": None,
            "coefficient_of_variation": None,
            "standardized_difference": None,
            "trend_direction": "insufficient_data"
        }

    first_val = valid[0]
    latest_val = valid[-1]
    abs_change = round(latest_val - first_val, 6)

    # Safe percentage difference
    pct_change: Optional[float] = None
    if abs(first_val) > 1e-7:
        pct_change = round(((latest_val - first_val) / abs(first_val)) * 100.0, 2)

    # Consecutive deltas
    consec_diffs = [abs(valid[i] - valid[i - 1]) for i in range(1, n)]
    mean_consec = round(float(np.mean(consec_diffs)), 6) if consec_diffs else None
    std_consec = round(float(np.std(consec_diffs, ddof=1)), 6) if len(consec_diffs) > 1 else 0.0

    # Overall CV
    var_res = calculate_variability(valid)
    cv = var_res.get("cv")

    # Standardized computational difference
    std_diff = calculate_effect_size([first_val], valid)

    # Deterministic trend
    rel_diff = abs(abs_change) / (abs(first_val) if abs(first_val) > 1e-7 else 1.0)
    if (abs(first_val) > 1e-7 and rel_diff < 0.05) or (abs(first_val) <= 1e-7 and abs(abs_change) < 1e-4):
        trend = "stable"
    elif latest_val > first_val:
        trend = "increasing"
    else:
        trend = "decreasing"

    return {
        "observation_count": n,
        "first_value": round(first_val, 6),
        "latest_value": round(latest_val, 6),
        "absolute_change": abs_change,
        "percentage_change": pct_change,
        "mean_consecutive_change": mean_consec,
        "std_consecutive_change": std_consec,
        "coefficient_of_variation": cv,
        "standardized_difference": std_diff,
        "trend_direction": trend
    }


def calculate_correlation(x: List[Any], y: List[Any]) -> Dict[str, Any]:
    """
    Calculate Pearson correlation coefficient r between two paired series.
    Requires at least 3 valid paired observations.
    """
    paired_x = []
    paired_y = []

    for vx, vy in zip(x, y):
        if vx is None or vy is None:
            continue
        try:
            fx = float(vx)
            fy = float(vy)
            if not math.isnan(fx) and not math.isinf(fx) and not math.isnan(fy) and not math.isinf(fy):
                paired_x.append(fx)
                paired_y.append(fy)
        except (ValueError, TypeError):
            continue

    n = len(paired_x)
    if n < 3:
        return {
            "correlation": None,
            "observation_count": n,
            "status": "insufficient_data",
            "reason": "Requires at least 3 valid paired observations for Pearson correlation."
        }

    arr_x = np.array(paired_x, dtype=float)
    arr_y = np.array(paired_y, dtype=float)

    std_x = float(np.std(arr_x))
    std_y = float(np.std(arr_y))

    if std_x <= 1e-8 or std_y <= 1e-8:
        return {
            "correlation": 0.0,
            "observation_count": n,
            "status": "zero_variance",
            "reason": "One or both series exhibited zero variance."
        }

    r_matrix = np.corrcoef(arr_x, arr_y)
    r = float(r_matrix[0, 1])

    if math.isnan(r) or math.isinf(r):
        return {
            "correlation": None,
            "observation_count": n,
            "status": "numerical_indeterminacy",
            "reason": "Correlation computation yielded non-finite result."
        }

    return {
        "correlation": round(r, 4),
        "observation_count": n,
        "status": "computed",
        "reason": None
    }


def calculate_metric_relationships(
    timeline: List[Dict[str, Any]],
    scope: str = "full_image"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Calculate correlation pairs and correlation matrix for tracked deformation metrics.
    """
    # Build series for each metric
    series_by_key: Dict[str, List[Optional[float]]] = {}
    metric_labels: Dict[str, str] = {}

    for m_def in METRIC_REGISTRY:
        m_key = m_def["key"]
        if scope == "roi" and m_def.get("roi_key"):
            active_key = m_def["roi_key"]
        else:
            active_key = m_key

        vals = []
        for item in timeline:
            v = item.get("metrics", {}).get(active_key)
            vals.append(v)

        series_by_key[m_key] = vals
        metric_labels[m_key] = m_def["label"]

    # Filter keys that have at least 3 valid values
    usable_keys = []
    for k, v in series_by_key.items():
        if len(_filter_valid_floats(v)) >= 3:
            usable_keys.append(k)

    # 1. Pairwise correlations
    pair_results: List[Dict[str, Any]] = []
    matrix_data: Dict[str, Dict[str, Optional[float]]] = {}

    for k1 in usable_keys:
        matrix_data[k1] = {}
        for k2 in usable_keys:
            if k1 == k2:
                matrix_data[k1][k2] = 1.0
            else:
                corr_res = calculate_correlation(series_by_key[k1], series_by_key[k2])
                matrix_data[k1][k2] = corr_res.get("correlation")

    # Gather non-redundant distinct pairs for table (upper triangle)
    for i in range(len(usable_keys)):
        for j in range(i + 1, len(usable_keys)):
            k1 = usable_keys[i]
            k2 = usable_keys[j]
            c_val = matrix_data[k1][k2]
            n_obs = len([1 for v1, v2 in zip(series_by_key[k1], series_by_key[k2]) if v1 is not None and v2 is not None])
            if c_val is not None:
                pair_results.append({
                    "metric_x": k1,
                    "label_x": metric_labels[k1],
                    "metric_y": k2,
                    "label_y": metric_labels[k2],
                    "correlation": c_val,
                    "abs_correlation": abs(c_val),
                    "observation_count": n_obs,
                    "association": "positive" if c_val > 0.2 else ("negative" if c_val < -0.2 else "near_zero")
                })

    # Sort strongest absolute correlations first
    pair_results.sort(key=lambda p: p["abs_correlation"], reverse=True)

    matrix_bundle = {
        "metrics": [
            {"key": k, "label": metric_labels[k]} for k in usable_keys
        ],
        "values": matrix_data,
        "available": len(usable_keys) >= 2
    }

    return pair_results, matrix_bundle


def detect_computational_outliers(
    timeline: List[Dict[str, Any]],
    scope: str = "full_image"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect statistical outliers using the standard 1.5 * IQR rule.
    Lower Bound = Q1 - 1.5 * IQR
    Upper Bound = Q3 + 1.5 * IQR
    """
    outliers_by_metric: Dict[str, List[Dict[str, Any]]] = {}

    for m_def in METRIC_REGISTRY:
        m_key = m_def["key"]
        active_key = m_def["roi_key"] if (scope == "roi" and m_def.get("roi_key")) else m_key

        observations: List[Tuple[int, Dict[str, Any], float]] = []
        for idx, item in enumerate(timeline):
            v = item.get("metrics", {}).get(active_key)
            if v is not None:
                try:
                    f = float(v)
                    if not math.isnan(f) and not math.isinf(f):
                        observations.append((idx + 1, item, f))
                except (ValueError, TypeError):
                    pass

        raw_values = [o[2] for o in observations]
        if len(raw_values) < 4:
            # Standard statistical convention: IQR outlier detection is unreliable on N < 4
            outliers_by_metric[m_key] = []
            continue

        pct = calculate_percentiles(raw_values)
        p25 = pct.get("p25")
        p75 = pct.get("p75")
        iqr = pct.get("iqr")

        if p25 is None or p75 is None or iqr is None or iqr <= 1e-7:
            outliers_by_metric[m_key] = []
            continue

        lower_bound = round(p25 - 1.5 * iqr, 6)
        upper_bound = round(p75 + 1.5 * iqr, 6)

        flagged: List[Dict[str, Any]] = []
        for session_idx, item, val in observations:
            if val < lower_bound or val > upper_bound:
                qc_sc = item.get("metrics", {}).get("quality_score")
                qc_lvl = item.get("quality_level")
                flagged.append({
                    "session_number": session_idx,
                    "analysis_id": item.get("analysis_id"),
                    "timestamp": item.get("timestamp"),
                    "type": item.get("type"),
                    "metric_key": m_key,
                    "metric_label": m_def["label"],
                    "unit": m_def["unit"],
                    "value": round(val, 6),
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "iqr": iqr,
                    "deviation_direction": "high" if val > upper_bound else "low",
                    "qc_score": qc_sc,
                    "qc_level": qc_lvl,
                    "quality_context": (
                        f"Analysis has {qc_lvl} QC score ({qc_sc}/100); artifacts may contribute to outlier status."
                        if (qc_lvl in ("Low", "Moderate") and qc_sc is not None)
                        else "High/Normal computational quality verified."
                    )
                })

        outliers_by_metric[m_key] = flagged

    return outliers_by_metric


def calculate_study_statistics(
    study_id: str,
    scope: str = "full_image"
) -> Dict[str, Any]:
    """
    Construct complete advanced statistical research analysis for a study.
    """
    long_summary = build_longitudinal_summary(study_id)
    if "error" in long_summary or long_summary.get("analysis_count", 0) == 0:
        return {
            "study_id": study_id,
            "study_title": long_summary.get("study_title", "Untitled Study"),
            "subject_code": long_summary.get("subject_code", ""),
            "analysis_count": 0,
            "analysis_scope": scope,
            "descriptive_statistics": {},
            "change_statistics": {},
            "correlations": [],
            "correlation_matrix": {"metrics": [], "values": {}, "available": False},
            "outliers": {},
            "total_outliers_count": 0,
            "quality_summary": {},
            "warnings": ["Study has no completed analyses available for statistical analysis."],
            "info": long_summary.get("info", []),
            "disclaimer": (
                "These statistics summarize computational image-derived measurements "
                "and should not be interpreted as clinical findings."
            )
        }

    timeline = long_summary.get("timeline") or []
    warnings: List[str] = list(long_summary.get("warnings") or [])
    info: List[str] = list(long_summary.get("info") or [])

    # Check if ROI is requested and available
    roi_consistency = long_summary.get("roi_consistency", {})
    has_roi = bool(roi_consistency.get("roi_count", 0) > 0)
    effective_scope = "roi" if (scope == "roi" and has_roi) else "full_image"

    if scope == "roi" and not has_roi:
        info.append("ROI scope was requested, but no ROI masked analyses were found. Evaluated full-image metrics instead.")
        effective_scope = "full_image"

    # 1. Descriptive & Change Statistics
    descriptive_stats: Dict[str, Any] = {}
    change_stats: Dict[str, Any] = {}

    for m_def in METRIC_REGISTRY:
        m_key = m_def["key"]
        active_key = m_def["roi_key"] if (effective_scope == "roi" and m_def.get("roi_key")) else m_key

        values = [item.get("metrics", {}).get(active_key) for item in timeline]

        desc = calculate_descriptive_statistics(values)
        desc["label"] = m_def["label"]
        desc["unit"] = m_def["unit"]
        desc["category"] = m_def["category"]
        descriptive_stats[m_key] = desc

        chg = calculate_change_statistics(values)
        chg["label"] = m_def["label"]
        chg["unit"] = m_def["unit"]
        change_stats[m_key] = chg

    # 2. Correlations & Matrix
    correlations, corr_matrix = calculate_metric_relationships(timeline, scope=effective_scope)

    if not corr_matrix.get("available"):
        info.append("Insufficient paired observations (<3 sessions) for Pearson metric correlation matrix.")

    # 3. Outlier Detection
    outliers_dict = detect_computational_outliers(timeline, scope=effective_scope)
    total_outliers = sum(len(o_list) for o_list in outliers_dict.values())

    if total_outliers > 0:
        warnings.append(
            f"Detected {total_outliers} computational statistical outlier observation(s) across metrics. "
            "Outliers reflect 1.5xIQR dispersion and may result from image quality, motion estimation, or ROI boundary differences."
        )

    # 4. Scope & Calibration notes
    cal_consistency = long_summary.get("calibration_consistency", {})
    if cal_consistency.get("status") == "mixed":
        warnings.append("Physical-unit statistical comparison may be unreliable because calibration settings differ.")
    elif cal_consistency.get("status") == "uncalibrated":
        info.append("Displacement statistics are reported in image-space pixels. Strain statistics remain dimensionless.")

    return {
        "study_id": study_id,
        "study_title": long_summary.get("study_title"),
        "subject_code": long_summary.get("subject_code"),
        "analysis_count": len(timeline),
        "analysis_scope": effective_scope,
        "roi_available": has_roi,
        "descriptive_statistics": descriptive_stats,
        "change_statistics": change_stats,
        "correlations": correlations,
        "correlation_matrix": corr_matrix,
        "outliers": outliers_dict,
        "total_outliers_count": total_outliers,
        "quality_summary": long_summary.get("quality_summary"),
        "calibration_consistency": cal_consistency,
        "roi_consistency": roi_consistency,
        "warnings": warnings,
        "info": info,
        "disclaimer": (
            "These statistics summarize computational image-derived measurements "
            "and should not be interpreted as clinical findings."
        )
    }

