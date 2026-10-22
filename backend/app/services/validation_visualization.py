"""
backend/app/services/validation_visualization.py

Visualization service for synthetic validation benchmarks.
Generates publication-quality side-by-side and error heatmaps for:
- Displacement (Ground Truth, Estimated, Absolute Error)
- Principal Strain (Ground Truth, Estimated, Absolute Error)
- Radial Deformation (Ground Truth, Estimated, Absolute Error)
- Circumferential Deformation (Ground Truth, Estimated, Absolute Error)

Saves output maps under backend/outputs/validation/{dataset_id}/
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

OUTPUTS_VALIDATION_DIR = Path("outputs/validation")
OUTPUTS_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def _render_heatmap(
    data: np.ndarray,
    output_path: Path,
    colormap: int = cv2.COLORMAP_JET,
    v_min: Optional[float] = None,
    v_max: Optional[float] = None
) -> str:
    """
    Render 2D float array into a colored heatmap PNG image.
    Uses consistent normalization bounds when provided.
    """
    arr = np.nan_to_num(data.copy(), nan=0.0, posinf=0.0, neginf=0.0)

    if v_min is None:
        v_min = float(np.min(arr))
    if v_max is None:
        v_max = float(np.max(arr))

    if abs(v_max - v_min) < 1e-7:
        norm = np.zeros_like(arr, dtype=np.uint8)
    else:
        clipped = np.clip(arr, v_min, v_max)
        norm = ((clipped - v_min) / (v_max - v_min) * 255.0).astype(np.uint8)

    colored = cv2.applyColorMap(norm, colormap)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), colored)
    return str(output_path)


def _compute_error_statistics(error_field: np.ndarray, mask: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Calculate descriptive error statistics: mean, median, max, RMSE."""
    arr = np.abs(error_field)
    if mask is not None:
        valid = arr[mask > 0]
    else:
        valid = arr.flatten()

    valid = valid[np.isfinite(valid)]
    if len(valid) == 0:
        return {"mean_error": 0.0, "median_error": 0.0, "max_error": 0.0, "rmse": 0.0}

    return {
        "mean_error": round(float(np.mean(valid)), 6),
        "median_error": round(float(np.median(valid)), 6),
        "max_error": round(float(np.max(valid)), 6),
        "rmse": round(float(np.sqrt(np.mean(valid**2))), 6)
    }


def generate_validation_visualizations(
    dataset_id: str,
    estimated: Dict[str, Any],
    ground_truth: Dict[str, Any],
    mask: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Generate ground truth, estimated, and absolute error heatmaps
    for displacement, strain, radial, and circumferential deformation.
    """
    out_dir = OUTPUTS_VALIDATION_DIR / f"dataset_{dataset_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    web_base = f"/outputs/validation/dataset_{dataset_id}"

    results: Dict[str, Any] = {}

    # 1. Displacement Heatmaps
    gt_disp = ground_truth.get("displacement_magnitude")
    est_disp = estimated.get("displacement_magnitude")
    if gt_disp is not None and est_disp is not None:
        # Match dimensions if needed
        if est_disp.shape != gt_disp.shape:
            est_disp = cv2.resize(est_disp, (gt_disp.shape[1], gt_disp.shape[0]))

        err_disp = np.abs(est_disp - gt_disp)
        max_d = max(float(np.max(gt_disp)), float(np.max(est_disp)), 1e-4)

        p_gt = out_dir / "gt_displacement.png"
        p_est = out_dir / "est_displacement.png"
        p_err = out_dir / "err_displacement.png"

        _render_heatmap(gt_disp, p_gt, cv2.COLORMAP_JET, v_min=0.0, v_max=max_d)
        _render_heatmap(est_disp, p_est, cv2.COLORMAP_JET, v_min=0.0, v_max=max_d)
        _render_heatmap(err_disp, p_err, cv2.COLORMAP_HOT, v_min=0.0, v_max=None)

        results["displacement"] = {
            "gt_url": f"{web_base}/gt_displacement.png",
            "est_url": f"{web_base}/est_displacement.png",
            "error_url": f"{web_base}/err_displacement.png",
            "statistics": _compute_error_statistics(err_disp, mask)
        }

    # 2. Strain Heatmaps (Principal Strain 1)
    gt_strain = ground_truth.get("strain", {}).get("principal_1")
    est_strain = estimated.get("strain", {}).get("principal_1")
    if gt_strain is not None and est_strain is not None:
        if est_strain.shape != gt_strain.shape:
            est_strain = cv2.resize(est_strain, (gt_strain.shape[1], gt_strain.shape[0]))

        err_strain = np.abs(est_strain - gt_strain)
        v_min = min(float(np.min(gt_strain)), float(np.min(est_strain)))
        v_max = max(float(np.max(gt_strain)), float(np.max(est_strain)), v_min + 1e-4)

        p_gt_s = out_dir / "gt_strain.png"
        p_est_s = out_dir / "est_strain.png"
        p_err_s = out_dir / "err_strain.png"

        _render_heatmap(gt_strain, p_gt_s, cv2.COLORMAP_JET, v_min=v_min, v_max=v_max)
        _render_heatmap(est_strain, p_est_s, cv2.COLORMAP_JET, v_min=v_min, v_max=v_max)
        _render_heatmap(err_strain, p_err_s, cv2.COLORMAP_HOT, v_min=0.0, v_max=None)

        results["strain"] = {
            "gt_url": f"{web_base}/gt_strain.png",
            "est_url": f"{web_base}/est_strain.png",
            "error_url": f"{web_base}/err_strain.png",
            "statistics": _compute_error_statistics(err_strain, mask)
        }

    # 3. Radial Deformation Heatmaps
    gt_rad = ground_truth.get("radial")
    est_rad = estimated.get("radial")
    if gt_rad is not None and est_rad is not None:
        if est_rad.shape != gt_rad.shape:
            est_rad = cv2.resize(est_rad, (gt_rad.shape[1], gt_rad.shape[0]))

        err_rad = np.abs(est_rad - gt_rad)
        v_min_r = min(float(np.min(gt_rad)), float(np.min(est_rad)))
        v_max_r = max(float(np.max(gt_rad)), float(np.max(est_rad)), v_min_r + 1e-4)

        p_gt_r = out_dir / "gt_radial.png"
        p_est_r = out_dir / "est_radial.png"
        p_err_r = out_dir / "err_radial.png"

        _render_heatmap(gt_rad, p_gt_r, cv2.COLORMAP_JET, v_min=v_min_r, v_max=v_max_r)
        _render_heatmap(est_rad, p_est_r, cv2.COLORMAP_JET, v_min=v_min_r, v_max=v_max_r)
        _render_heatmap(err_rad, p_err_r, cv2.COLORMAP_HOT, v_min=0.0, v_max=None)

        results["radial"] = {
            "gt_url": f"{web_base}/gt_radial.png",
            "est_url": f"{web_base}/est_radial.png",
            "error_url": f"{web_base}/err_radial.png",
            "statistics": _compute_error_statistics(err_rad, mask)
        }

    # 4. Circumferential Deformation Heatmaps
    gt_circ = ground_truth.get("circumferential")
    est_circ = estimated.get("circumferential")
    if gt_circ is not None and est_circ is not None:
        if est_circ.shape != gt_circ.shape:
            est_circ = cv2.resize(est_circ, (gt_circ.shape[1], gt_circ.shape[0]))

        err_circ = np.abs(est_circ - gt_circ)
        v_min_c = min(float(np.min(gt_circ)), float(np.min(est_circ)))
        v_max_c = max(float(np.max(gt_circ)), float(np.max(est_circ)), v_min_c + 1e-4)

        p_gt_c = out_dir / "gt_circumferential.png"
        p_est_c = out_dir / "est_circumferential.png"
        p_err_c = out_dir / "err_circumferential.png"

        _render_heatmap(gt_circ, p_gt_c, cv2.COLORMAP_JET, v_min=v_min_c, v_max=v_max_c)
        _render_heatmap(est_circ, p_est_c, cv2.COLORMAP_JET, v_min=v_min_c, v_max=v_max_c)
        _render_heatmap(err_circ, p_err_c, cv2.COLORMAP_HOT, v_min=0.0, v_max=None)

        results["circumferential"] = {
            "gt_url": f"{web_base}/gt_circumferential.png",
            "est_url": f"{web_base}/est_circumferential.png",
            "error_url": f"{web_base}/err_circumferential.png",
            "statistics": _compute_error_statistics(err_circ, mask)
        }

    return results

