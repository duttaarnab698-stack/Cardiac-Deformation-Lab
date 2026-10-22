"""
backend/app/services/validation.py

Quantitative Validation and Benchmarking Service for Cardiac Deformation Lab.
Evaluates algorithmic optical flow displacement and strain estimation accuracy
against known analytical mathematical ground-truth fields.

Calculates:
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- Pearson correlation coefficient (r)
- Relative Error
- Mean and Maximum Endpoint Error (EPE)
- Radial and Circumferential component accuracy

Handles:
- Dimensional mismatches
- NaN / Infinite values
- Region of interest / myocardial masking
- Small samples and zero variance
- Never crashes
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np


def _safe_float(val: Any) -> Optional[float]:
    """Safely convert value to finite float or None."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 6)
    except (ValueError, TypeError):
        return None


def _align_and_mask_fields(
    estimated: np.ndarray,
    ground_truth: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Ensure estimated and ground truth arrays match in shape,
    apply optional binary mask, and filter out any non-finite values.
    Returns 1D flattened arrays of valid paired observations: (est_valid, gt_valid).
    """
    est = estimated.copy().astype(np.float64)
    gt = ground_truth.copy().astype(np.float64)

    # Resize estimated if dimensions differ
    if est.shape != gt.shape:
        est = cv2.resize(est, (gt.shape[1], gt.shape[0]), interpolation=cv2.INTER_LINEAR)

    # Valid mask
    finite_mask = np.isfinite(est) & np.isfinite(gt)
    if mask is not None:
        m = mask.astype(bool)
        if m.shape != gt.shape:
            m = cv2.resize(m.astype(np.uint8), (gt.shape[1], gt.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
        finite_mask = finite_mask & m

    est_valid = est[finite_mask]
    gt_valid = gt[finite_mask]

    return est_valid, gt_valid


def calculate_field_mae(
    estimated: np.ndarray,
    ground_truth: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> Optional[float]:
    """Calculate Mean Absolute Error (MAE): (1/N) * sum |est - gt|."""
    est, gt = _align_and_mask_fields(estimated, ground_truth, mask)
    if len(est) == 0:
        return None
    return _safe_float(np.mean(np.abs(est - gt)))


def calculate_field_rmse(
    estimated: np.ndarray,
    ground_truth: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> Optional[float]:
    """Calculate Root Mean Squared Error (RMSE): sqrt( (1/N) * sum (est - gt)^2 )."""
    est, gt = _align_and_mask_fields(estimated, ground_truth, mask)
    if len(est) == 0:
        return None
    return _safe_float(np.sqrt(np.mean((est - gt)**2)))


def calculate_field_correlation(
    estimated: np.ndarray,
    ground_truth: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> Optional[float]:
    """
    Calculate Pearson correlation coefficient r between estimated and ground truth.
    Requires at least 3 points and non-zero variance.
    """
    est, gt = _align_and_mask_fields(estimated, ground_truth, mask)
    if len(est) < 3:
        return None

    std_est = np.std(est)
    std_gt = np.std(gt)

    if std_est <= 1e-8 or std_gt <= 1e-8:
        # One or both fields have near-zero variance
        return 1.0 if np.allclose(est, gt, atol=1e-5) else 0.0

    r_mat = np.corrcoef(est, gt)
    r_val = float(r_mat[0, 1])
    return _safe_float(r_val)


def calculate_relative_error(
    estimated: np.ndarray,
    ground_truth: np.ndarray,
    mask: Optional[np.ndarray] = None,
    epsilon: float = 1e-5
) -> Optional[float]:
    """
    Calculate normalized relative error: sum |est - gt| / (sum |gt| + epsilon).
    Returns ratio or percentage.
    """
    est, gt = _align_and_mask_fields(estimated, ground_truth, mask)
    if len(est) == 0:
        return None

    numerator = np.sum(np.abs(est - gt))
    denominator = np.sum(np.abs(gt)) + epsilon
    return _safe_float(numerator / denominator)


def calculate_endpoint_error(
    estimated_u: np.ndarray,
    estimated_v: np.ndarray,
    gt_u: np.ndarray,
    gt_v: np.ndarray,
    mask: Optional[np.ndarray] = None
) -> Dict[str, Optional[float]]:
    """
    Calculate optical flow End-Point Error (EPE):
        EPE(x, y) = sqrt( (u_est - u_gt)^2 + (v_est - v_gt)^2 )
    Returns mean, median, max, and rmse endpoint error.
    """
    eu, gu = _align_and_mask_fields(estimated_u, gt_u, mask)
    ev, gv = _align_and_mask_fields(estimated_v, gt_v, mask)

    min_len = min(len(eu), len(ev))
    if min_len == 0:
        return {
            "mean_endpoint_error": None,
            "median_endpoint_error": None,
            "max_endpoint_error": None,
            "rmse_endpoint_error": None
        }

    eu = eu[:min_len]
    gu = gu[:min_len]
    ev = ev[:min_len]
    gv = gv[:min_len]

    epe = np.sqrt((eu - gu)**2 + (ev - gv)**2)

    return {
        "mean_endpoint_error": _safe_float(np.mean(epe)),
        "median_endpoint_error": _safe_float(np.median(epe)),
        "max_endpoint_error": _safe_float(np.max(epe)),
        "rmse_endpoint_error": _safe_float(np.sqrt(np.mean(epe**2)))
    }


def calculate_strain_error(
    estimated_strains: Dict[str, np.ndarray],
    ground_truth_strains: Dict[str, np.ndarray],
    mask: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Compare estimated strain fields against ground truth."""
    metrics_by_component = {}

    for comp in ["principal_1", "principal_2", "exx", "eyy", "exy"]:
        est = estimated_strains.get(comp)
        gt = ground_truth_strains.get(comp)

        if est is not None and gt is not None:
            mae = calculate_field_mae(est, gt, mask)
            rmse = calculate_field_rmse(est, gt, mask)
            corr = calculate_field_correlation(est, gt, mask)
            rel_err = calculate_relative_error(est, gt, mask)

            metrics_by_component[comp] = {
                "mae": mae,
                "rmse": rmse,
                "correlation": corr,
                "relative_error": rel_err
            }

    # Aggregate primary strain validation metric
    p1_metrics = metrics_by_component.get("principal_1", {})
    return {
        "components": metrics_by_component,
        "mean_absolute_error": p1_metrics.get("mae"),
        "rmse": p1_metrics.get("rmse"),
        "correlation": p1_metrics.get("correlation"),
        "relative_error": p1_metrics.get("relative_error")
    }


def compare_estimated_vs_ground_truth(
    estimated: Dict[str, Any],
    ground_truth: Dict[str, Any],
    myocardial_mask: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Comprehensive quantitative benchmark comparing estimated flow and strain
    against known mathematical ground truth.
    Evaluates both full image and myocardial region.
    """
    # 1. Displacement validation
    est_u = estimated.get("displacement_u")
    est_v = estimated.get("displacement_v")
    est_mag = estimated.get("displacement_magnitude")

    gt_u = ground_truth.get("displacement_u")
    gt_v = ground_truth.get("displacement_v")
    gt_mag = ground_truth.get("displacement_magnitude")

    disp_val = {}
    if est_u is not None and gt_u is not None and est_v is not None and gt_v is not None:
        # Full image EPE & metrics
        epe_full = calculate_endpoint_error(est_u, est_v, gt_u, gt_v, mask=None)
        mag_mae_full = calculate_field_mae(est_mag, gt_mag, mask=None)
        mag_rmse_full = calculate_field_rmse(est_mag, gt_mag, mask=None)
        mag_corr_full = calculate_field_correlation(est_mag, gt_mag, mask=None)

        disp_val["full_image"] = {
            "mae": mag_mae_full,
            "rmse": mag_rmse_full,
            "correlation": mag_corr_full,
            "mean_endpoint_error": epe_full["mean_endpoint_error"],
            "max_endpoint_error": epe_full["max_endpoint_error"],
            "median_endpoint_error": epe_full["median_endpoint_error"],
            "rmse_endpoint_error": epe_full["rmse_endpoint_error"]
        }

        # Myocardial ring region if mask available
        if myocardial_mask is not None and np.any(myocardial_mask > 0):
            epe_myo = calculate_endpoint_error(est_u, est_v, gt_u, gt_v, mask=myocardial_mask)
            mag_mae_myo = calculate_field_mae(est_mag, gt_mag, mask=myocardial_mask)
            mag_rmse_myo = calculate_field_rmse(est_mag, gt_mag, mask=myocardial_mask)
            mag_corr_myo = calculate_field_correlation(est_mag, gt_mag, mask=myocardial_mask)

            disp_val["myocardium"] = {
                "mae": mag_mae_myo,
                "rmse": mag_rmse_myo,
                "correlation": mag_corr_myo,
                "mean_endpoint_error": epe_myo["mean_endpoint_error"],
                "max_endpoint_error": epe_myo["max_endpoint_error"],
                "median_endpoint_error": epe_myo["median_endpoint_error"],
                "rmse_endpoint_error": epe_myo["rmse_endpoint_error"]
            }

    # 2. Strain validation
    strain_est = estimated.get("strain", {})
    strain_gt = ground_truth.get("strain", {})
    strain_val = {}

    if strain_est and strain_gt:
        strain_val["full_image"] = calculate_strain_error(strain_est, strain_gt, mask=None)
        if myocardial_mask is not None and np.any(myocardial_mask > 0):
            strain_val["myocardium"] = calculate_strain_error(strain_est, strain_gt, mask=myocardial_mask)

    # 3. Radial and Circumferential deformation validation
    rad_val = {}
    circ_val = {}

    est_rad = estimated.get("radial")
    gt_rad = ground_truth.get("radial")
    if est_rad is not None and gt_rad is not None:
        rad_val = {
            "mae": calculate_field_mae(est_rad, gt_rad, mask=myocardial_mask),
            "rmse": calculate_field_rmse(est_rad, gt_rad, mask=myocardial_mask),
            "correlation": calculate_field_correlation(est_rad, gt_rad, mask=myocardial_mask)
        }

    est_circ = estimated.get("circumferential")
    gt_circ = ground_truth.get("circumferential")
    if est_circ is not None and gt_circ is not None:
        circ_val = {
            "mae": calculate_field_mae(est_circ, gt_circ, mask=myocardial_mask),
            "rmse": calculate_field_rmse(est_circ, gt_circ, mask=myocardial_mask),
            "correlation": calculate_field_correlation(est_circ, gt_circ, mask=myocardial_mask)
        }

    # Determine summary metrics (prefer myocardium region if available, else full_image)
    active_disp = disp_val.get("myocardium") or disp_val.get("full_image") or {}
    active_strain = strain_val.get("myocardium") or strain_val.get("full_image") or {}

    summary = {
        "displacement_mae": active_disp.get("mae"),
        "displacement_rmse": active_disp.get("rmse"),
        "displacement_correlation": active_disp.get("correlation"),
        "mean_endpoint_error": active_disp.get("mean_endpoint_error"),
        "max_endpoint_error": active_disp.get("max_endpoint_error"),
        "strain_mae": active_strain.get("mean_absolute_error"),
        "strain_rmse": active_strain.get("rmse"),
        "strain_correlation": active_strain.get("correlation"),
        "radial_rmse": rad_val.get("rmse"),
        "circumferential_rmse": circ_val.get("rmse")
    }

    return {
        "summary": summary,
        "displacement": disp_val,
        "strain": strain_val,
        "radial": rad_val,
        "circumferential": circ_val
    }

