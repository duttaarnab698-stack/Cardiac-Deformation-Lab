"""
backend/app/services/quality_control.py

Automated Computational Analysis Quality Control (QC) and Validation Service
for the Cardiac Deformation Lab research prototype.

Evaluates measurable technical properties of input data and computed fields:
- Image quality (resolution, intensity distribution, dynamic range, sharpness via Laplacian variance)
- Image pair/sequence compatibility (dimensions, aspect ratio, grayscale consistency)
- Optical flow reliability (magnitude, valid vectors, non-finite checks, consistency)
- Strain tensor validity (infinitesimal bounds, finite numbers, tensor consistency)
- ROI geometry & boundary validity (pixel count, image bounds, coverage percentage)
- Tracked ROI trajectory quality (tracking confidence, failed frames, drift)
- Temporal dynamics quality (frame continuity, pair counts, trajectory stability)
- Spatial calibration integrity (positive spacing, physical units)

IMPORTANT SCIENTIFIC DISCLAIMER:
This module performs computational quality control only. It measures mathematical
and algorithmic consistency. It does NOT make clinical diagnoses, evaluate patient
health, or compute diagnostic confidence scores.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import math
import numpy as np
import cv2


# Standard search directories for images
UPLOAD_DIRS = [Path("uploads"), Path("backend/uploads")]


def _find_image_path(filename: str) -> Optional[Path]:
    """Locate an image filename in candidate upload directories."""
    if not filename:
        return None
    p = Path(filename)
    if p.exists() and p.is_file():
        return p
    for d in UPLOAD_DIRS:
        cand = d / filename
        if cand.exists() and cand.is_file():
            return cand
    return None


def _load_image_gray(filename: str) -> Optional[np.ndarray]:
    """Safely load image as 8-bit grayscale array."""
    path = _find_image_path(filename)
    if path is None:
        return None
    try:
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        return img
    except Exception:
        return None


def evaluate_image_quality(filename: str) -> Dict[str, Any]:
    """
    Evaluate technical quality metrics for an input image file:
    - Resolution (width, height, pixel count)
    - Grayscale intensity distribution (min, max, mean, std)
    - Contrast (dynamic range, RMS contrast / std)
    - Sharpness estimate (variance of Laplacian)
    """
    img = _load_image_gray(filename)
    if img is None:
        return {
            "available": False,
            "filename": filename,
            "score": 50,
            "status": "Unknown",
            "warnings": [f"Image file '{filename}' could not be loaded for technical inspection."],
            "info": [],
            "metrics": {}
        }

    h, w = img.shape[:2]
    total_pixels = int(h * w)
    min_val = float(np.min(img))
    max_val = float(np.max(img))
    mean_val = float(np.mean(img))
    std_val = float(np.std(img))
    intensity_range = float(max_val - min_val)

    # Sharpness via Laplacian variance
    try:
        laplacian_var = float(cv2.Laplacian(img, cv2.CV_64F).var())
    except Exception:
        laplacian_var = 0.0

    warnings = []
    info = []
    score = 100

    # 1. Resolution Check
    if w < 64 or h < 64 or total_pixels < 10000:
        warnings.append(
            f"Input image resolution is very low ({w}x{h}, {total_pixels} px); deformation field resolution will be coarse."
        )
        score -= 25
    elif w < 128 or h < 128:
        info.append(f"Input image resolution is moderate ({w}x{h}).")
        score -= 10

    # 2. Contrast & Intensity Range Check
    if std_val < 10.0 or intensity_range < 30.0:
        warnings.append(
            f"Input frame contrast is low (std={std_val:.1f}, range={intensity_range:.0f}); optical-flow gradients may be weak."
        )
        score -= 25
    elif std_val < 18.0:
        info.append(f"Input frame contrast is modest (std={std_val:.1f}).")
        score -= 10

    # 3. Blur / Sharpness Check
    if laplacian_var < 35.0:
        warnings.append(
            f"Input frame appears heavily blurred (Laplacian variance={laplacian_var:.1f}); edge localization may be diminished."
        )
        score -= 25
    elif laplacian_var < 80.0:
        info.append(f"Input frame sharpness index is moderate (Laplacian variance={laplacian_var:.1f}).")
        score -= 10

    score = max(0, min(100, score))
    status = "Good" if score >= 80 else ("Fair" if score >= 60 else "Poor")

    return {
        "available": True,
        "filename": filename,
        "score": score,
        "status": status,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "width": w,
            "height": h,
            "pixel_count": total_pixels,
            "min_intensity": round(min_val, 1),
            "max_intensity": round(max_val, 1),
            "mean_intensity": round(mean_val, 2),
            "std_intensity": round(std_val, 2),
            "intensity_range": round(intensity_range, 1),
            "laplacian_variance": round(laplacian_var, 2),
        }
    }


def evaluate_image_compatibility(image_filenames: List[str]) -> Dict[str, Any]:
    """
    Check dimension, aspect ratio, and format consistency across input frame pairs/sequences.
    """
    if not image_filenames or len(image_filenames) < 2:
        return {
            "compatible": True,
            "score": 100,
            "warnings": [],
            "info": ["Single image input; multi-frame compatibility check not required."]
        }

    warnings = []
    info = []
    score = 100
    dims = []

    for fn in image_filenames:
        img = _load_image_gray(fn)
        if img is not None:
            dims.append((img.shape[1], img.shape[0]))  # (width, height)
        else:
            dims.append(None)

    valid_dims = [d for d in dims if d is not None]
    if len(valid_dims) >= 2:
        w0, h0 = valid_dims[0]
        has_size_mismatch = any(d[0] != w0 or d[1] != h0 for d in valid_dims[1:])
        if has_size_mismatch:
            warnings.append("Input frames have different dimensions and were resized for analysis.")
            score -= 15

            # Check aspect ratio
            ar0 = float(w0) / float(h0) if h0 > 0 else 1.0
            ar_diff = any(abs((float(d[0]) / float(d[1])) - ar0) > 0.05 for d in valid_dims[1:] if d[1] > 0)
            if ar_diff:
                warnings.append("Input frames have differing aspect ratios; non-uniform spatial scaling may affect strain tensors.")
                score -= 10
        else:
            info.append(f"Input frames possess identical dimensions ({w0}x{h0}).")

    return {
        "compatible": len(warnings) == 0,
        "score": max(0, score),
        "warnings": warnings,
        "info": info
    }


def evaluate_motion_quality(
    disp_dict: Optional[Dict[str, Any]],
    advanced_dict: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate optical flow reliability:
    - Non-finite (NaN / Inf) vector detection
    - Motion magnitude distribution (near-zero, excessive, unstable velocity variance)
    - Vector field coherence
    """
    if not disp_dict or not isinstance(disp_dict, dict):
        return {
            "score": 50,
            "status": "Unknown",
            "warnings": ["Optical flow displacement records are unavailable."],
            "info": [],
            "metrics": {}
        }

    mean_disp = disp_dict.get("mean_displacement") or disp_dict.get("mean")
    max_disp = disp_dict.get("max_displacement") or disp_dict.get("max")
    std_disp = disp_dict.get("std_displacement") or disp_dict.get("std")
    min_disp = disp_dict.get("min_displacement") or disp_dict.get("min")

    warnings = []
    info = []
    score = 100

    # 1. Non-finite values check
    for k, v in [("mean", mean_disp), ("max", max_disp), ("std", std_disp)]:
        if v is not None and (math.isnan(float(v)) or math.isinf(float(v))):
            warnings.append(f"Optical flow contains non-finite values in {k} displacement.")
            score -= 40

    mean_f = float(mean_disp) if mean_disp is not None and math.isfinite(float(mean_disp)) else 0.0
    max_f = float(max_disp) if max_disp is not None and math.isfinite(float(max_disp)) else 0.0
    std_f = float(std_disp) if std_disp is not None and math.isfinite(float(std_disp)) else 0.0

    # 2. Extreme sparsity / near-zero motion
    if mean_f < 0.005:
        warnings.append(
            f"Optical-flow magnitude is near-zero (mean={mean_f:.4f} px); motion estimation may be unstable or static."
        )
        score -= 25
    elif mean_f < 0.05:
        info.append(f"Sub-pixel subtle motion detected (mean displacement={mean_f:.3f} px).")

    # 3. Velocity stability / extreme spikes
    if max_f > 120.0:
        warnings.append(
            f"Motion estimation may be unstable (extreme peak displacement of {max_f:.1f} px detected)."
        )
        score -= 20
    elif std_f > 0 and (max_f / (mean_f + 1e-4) > 15.0) and max_f > 15.0:
        warnings.append(
            f"Optical-flow vectors show high variability (peak {max_f:.1f} px vs mean {mean_f:.2f} px)."
        )
        score -= 15

    # 4. Motion coherence check
    coh_val = None
    if advanced_dict and isinstance(advanced_dict, dict):
        coh = advanced_dict.get("motion_coherence")
        if isinstance(coh, dict):
            coh_val = coh.get("mean")
        elif isinstance(coh, (int, float)):
            coh_val = float(coh)

    if coh_val is not None and math.isfinite(float(coh_val)):
        coh_f = float(coh_val)
        if coh_f < 0.25:
            warnings.append(f"Motion coherence is low ({coh_f:.2f}); flow field exhibits erratic local vectors.")
            score -= 15
        elif coh_f >= 0.70:
            info.append(f"High motion coherence ({coh_f:.2f}) indicates smooth flow alignment.")

    score = max(0, min(100, score))
    status = "Good" if score >= 80 else ("Fair" if score >= 60 else "Poor")

    return {
        "score": score,
        "status": status,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "mean_displacement_px": round(mean_f, 3),
            "max_displacement_px": round(max_f, 3),
            "std_displacement_px": round(std_f, 3),
            "motion_coherence": round(float(coh_val), 3) if coh_val is not None else None,
        }
    }


def evaluate_strain_quality(
    strain_dict: Optional[Dict[str, Any]],
    advanced_dict: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate small-deformation continuum strain calculation quality:
    - Finite numerical consistency
    - Infinitesimal continuum strain assumptions (|epsilon| < 0.5)
    - Correlation between tensor components
    """
    if not strain_dict or not isinstance(strain_dict, dict):
        return {
            "score": 50,
            "status": "Unknown",
            "warnings": ["Strain statistics are unavailable for quality assessment."],
            "info": [],
            "metrics": {}
        }

    warnings = []
    info = []
    score = 100

    p1 = strain_dict.get("principal_strain_1") or {}
    p1_mean = p1.get("mean") if isinstance(p1, dict) else strain_dict.get("mean_principal_strain_1")
    p1_max = p1.get("max") if isinstance(p1, dict) else strain_dict.get("max_principal_strain_1")
    exx = strain_dict.get("exx") or {}
    eyy = strain_dict.get("eyy") or {}

    # Check finite numbers
    for name, val in [("principal strain mean", p1_mean), ("principal strain max", p1_max)]:
        if val is not None and (math.isnan(float(val)) or math.isinf(float(val))):
            warnings.append(f"Strain tensor calculations contain non-finite values in {name}.")
            score -= 40

    p1_mean_f = float(p1_mean) if p1_mean is not None and math.isfinite(float(p1_mean)) else 0.0
    p1_max_f = float(p1_max) if p1_max is not None and math.isfinite(float(p1_max)) else 0.0

    # Infinitesimal strain continuum threshold check
    # Infinitesimal strain theory assumes small displacement gradients.
    if abs(p1_mean_f) > 0.8 or abs(p1_max_f) > 3.0:
        warnings.append(
            f"Calculated strain magnitudes exceed infinitesimal continuum assumptions (peak ε₁={p1_max_f:.2f}); small-strain approximations may degrade."
        )
        score -= 25
    elif abs(p1_mean_f) > 0.4:
        info.append(f"Elevated mean principal strain observed (ε₁={p1_mean_f:.3f}).")

    # Check strain tensor shear vs normal balance
    exx_m = exx.get("mean") if isinstance(exx, dict) else None
    eyy_m = eyy.get("mean") if isinstance(eyy, dict) else None
    if exx_m is not None and eyy_m is not None:
        info.append(f"Normal strain components evaluated (Exx={float(exx_m):.3f}, Eyy={float(eyy_m):.3f}).")

    score = max(0, min(100, score))
    status = "Good" if score >= 80 else ("Fair" if score >= 60 else "Poor")

    return {
        "score": score,
        "status": status,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "mean_principal_strain": round(p1_mean_f, 4),
            "max_principal_strain": round(p1_max_f, 4),
        }
    }


def evaluate_roi_quality(
    roi_config: Optional[Dict[str, Any]],
    image_shape: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]:
    """
    Evaluate Region of Interest (ROI) quality and boundaries:
    - ROI enabled state
    - Pixel count and coverage percentage
    - Extremely small or near-total image area flags
    """
    if not roi_config or not isinstance(roi_config, dict) or not roi_config.get("enabled"):
        return {
            "score": 100,
            "status": "Not Applicable",
            "applicable": False,
            "warnings": [],
            "info": ["Full-image analysis mode active; no localized ROI masking applied."],
            "metrics": {"enabled": False}
        }

    warnings = []
    info = []
    score = 100

    pixel_count = roi_config.get("pixel_count")
    roi_type = roi_config.get("type", "Custom")
    mode = roi_config.get("mode", "fixed")

    total_pixels = None
    pct_area = None
    if image_shape:
        h, w = image_shape
        total_pixels = h * w
        if pixel_count is not None and total_pixels > 0:
            pct_area = (float(pixel_count) / float(total_pixels)) * 100.0

    if pixel_count is not None:
        if pixel_count == 0:
            warnings.append("The selected Region of Interest (ROI) is empty (0 pixels); regional metrics cannot be evaluated.")
            score = 0
        elif pixel_count < 50:
            warnings.append(
                f"The selected ROI contains a small number of pixels ({pixel_count} px); summary statistics may be sensitive to local variation."
            )
            score -= 30
        elif pct_area is not None and pct_area < 0.5:
            warnings.append(
                f"The selected ROI occupies less than 0.5% of total image area ({pct_area:.2f}%); local metrics may exhibit high variance."
            )
            score -= 20
        elif pct_area is not None and pct_area > 96.0:
            info.append(f"Selected ROI covers {pct_area:.1f}% of image area, approximating full-frame analysis.")

    info.append(f"ROI mode: {mode.capitalize()} ({roi_type.capitalize()}), {pixel_count or 'N/A'} px.")
    score = max(0, min(100, score))
    status = "Good" if score >= 80 else ("Fair" if score >= 60 else "Poor")

    return {
        "score": score,
        "status": status,
        "applicable": True,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "enabled": True,
            "type": roi_type,
            "mode": mode,
            "pixel_count": pixel_count,
            "area_percentage": round(pct_area, 2) if pct_area is not None else None,
        }
    }


def evaluate_tracking_quality(tracking_summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate automated ROI tracking across temporal frames:
    - Mean and minimum tracking confidence scores
    - Failed frame count and success percentage
    - Kinematic displacement and drift
    """
    if not tracking_summary or not isinstance(tracking_summary, dict):
        return {
            "score": 100,
            "status": "Not Applicable",
            "applicable": False,
            "warnings": [],
            "info": ["Automated ROI tracking was not active for this analysis."],
            "metrics": {}
        }

    warnings = []
    info = []
    score = 100

    mean_conf = tracking_summary.get("mean_confidence")
    min_conf = tracking_summary.get("min_confidence")
    failed_frames = tracking_summary.get("failed_frames", 0)
    total_tracked = tracking_summary.get("total_tracked_frames", 0)
    max_drift = tracking_summary.get("max_drift")
    success_rate = tracking_summary.get("success_rate", 1.0)

    # 1. Failed frames check
    if failed_frames > 0:
        warnings.append(
            f"ROI tracking failed for {failed_frames} of {total_tracked} frame(s); position was held fixed during failures."
        )
        score -= min(40, failed_frames * 15)

    # 2. Confidence scores check
    if mean_conf is not None:
        mean_c = float(mean_conf)
        if mean_c < 0.50:
            warnings.append(
                f"Mean ROI tracking confidence is low ({mean_c:.2f}); template matching may be drifting."
            )
            score -= 25
        elif mean_c < 0.70:
            info.append(f"Moderate ROI tracking confidence ({mean_c:.2f}).")
            score -= 10
        else:
            info.append(f"High tracking confidence (mean={mean_c:.2f}).")

    if min_conf is not None and float(min_conf) < 0.35 and failed_frames == 0:
        warnings.append(f"Minimum frame tracking confidence dipped to {float(min_conf):.2f}.")
        score -= 10

    # 3. Maximum drift check
    if max_drift is not None and float(max_drift) > 40.0:
        warnings.append(
            f"Large frame-to-frame ROI shift detected ({float(max_drift):.1f} px); verify kinematic continuity."
        )
        score -= 15

    score = max(0, min(100, score))
    status = "Good" if score >= 80 else ("Fair" if score >= 60 else "Poor")

    return {
        "score": score,
        "status": status,
        "applicable": True,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "mean_confidence": round(float(mean_conf), 3) if mean_conf is not None else None,
            "min_confidence": round(float(min_conf), 3) if min_conf is not None else None,
            "failed_frames": failed_frames,
            "total_frames": total_tracked,
            "success_rate_pct": round(float(success_rate) * 100.0, 1),
            "max_drift_px": round(float(max_drift), 2) if max_drift is not None else None,
        }
    }


def evaluate_temporal_quality(
    record_type: str,
    temporal_summary: Optional[Dict[str, Any]],
    frame_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Evaluate temporal multi-frame sequence quality:
    - Number of frames and pair count
    - Single pair limitation notice
    - Temporal stability index (TSI) consistency
    """
    if record_type != "temporal":
        return {
            "score": 100,
            "status": "Not Applicable",
            "applicable": False,
            "warnings": [],
            "info": ["Single-pair evaluation; multi-frame temporal continuity not applicable."],
            "metrics": {}
        }

    warnings = []
    info = []
    score = 100
    fc = frame_count or 0

    if fc == 2:
        warnings.append("Temporal stability metrics are limited because only one frame pair was analyzed.")
        score -= 25
    elif fc >= 3:
        info.append(f"Temporal cine sequence analyzed across {fc} sequential frames.")

    tsi = None
    if temporal_summary and isinstance(temporal_summary, dict):
        tsi = temporal_summary.get("temporal_stability_index")
        if tsi is not None and math.isfinite(float(tsi)):
            tsi_f = float(tsi)
            if tsi_f < 0.20:
                warnings.append(f"Temporal Stability Index is low ({tsi_f:.2f}); frame-to-frame strain trajectory shows substantial fluctuation.")
                score -= 15
            elif tsi_f >= 0.70:
                info.append(f"High temporal trajectory stability observed (TSI={tsi_f:.2f}).")

    score = max(0, min(100, score))
    status = "Good" if score >= 80 else ("Fair" if score >= 60 else "Poor")

    return {
        "score": score,
        "status": status,
        "applicable": True,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "frame_count": fc,
            "temporal_stability_index": round(float(tsi), 3) if tsi is not None else None,
        }
    }


def evaluate_calibration_quality(cal_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate spatial calibration validity:
    - Positive finite pixel spacing (X and Y)
    - Valid distance unit
    - If missing: informational notice (does not penalize score)
    """
    warnings = []
    info = []

    if not cal_config or not isinstance(cal_config, dict) or not cal_config.get("enabled"):
        return {
            "score": 100,
            "status": "Uncalibrated",
            "calibrated": False,
            "warnings": [],
            "info": ["Spatial calibration was not provided; displacement remains in image-space units."],
            "metrics": {"calibrated": False}
        }

    sp_x = cal_config.get("pixel_spacing_x")
    sp_y = cal_config.get("pixel_spacing_y")
    unit = cal_config.get("unit", "mm")

    is_valid = True
    if sp_x is None or sp_y is None or float(sp_x) <= 0 or float(sp_y) <= 0:
        warnings.append("Spatial calibration spacing values are invalid or non-positive; physical units cannot be verified.")
        score = 50
        status = "Invalid Calibration"
        is_valid = False
    else:
        score = 100
        status = "Calibrated"
        info.append(f"Spatial calibration active ({float(sp_x):.3f} x {float(sp_y):.3f} {unit}/pixel).")

    return {
        "score": score,
        "status": status,
        "calibrated": is_valid,
        "warnings": warnings,
        "info": info,
        "metrics": {
            "calibrated": is_valid,
            "pixel_spacing_x": sp_x,
            "pixel_spacing_y": sp_y,
            "unit": unit,
        }
    }


def evaluate_analysis_quality(
    analysis_record_or_result: Dict[str, Any],
    record_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute comprehensive Computational Analysis Quality Control evaluation.

    Parameters
    ----------
    analysis_record_or_result : dict
        Analysis result dict (from strain endpoint) or full history record.
    record_type : str, optional
        "single_pair" or "temporal". Inferred if omitted.

    Returns
    -------
    dict
        {
            "score": int (0 - 100),
            "level": "High" | "Moderate" | "Low",
            "components": {
                "image_quality": {...},
                "compatibility": {...},
                "motion_quality": {...},
                "strain_quality": {...},
                "roi_quality": {...},
                "tracking_quality": {...},
                "temporal_quality": {...},
                "calibration_quality": {...}
            },
            "warnings": [...],
            "info": [...],
            "weights": {...},
            "disclaimer": str
        }
    """
    # Normalize input
    res = analysis_record_or_result.get("result") or analysis_record_or_result
    rec_type = record_type or analysis_record_or_result.get("type") or ("temporal" if "frame_count" in res else "single_pair")

    # 1. Gather image filenames
    image_filenames = []
    if "image1" in res and res["image1"]:
        image_filenames.append(res["image1"])
    if "image2" in res and res["image2"]:
        image_filenames.append(res["image2"])
    if "filenames" in res and isinstance(res["filenames"], list):
        image_filenames.extend(res["filenames"])

    # Unique filenames preserving order
    unique_filenames = []
    for fn in image_filenames:
        if fn and fn not in unique_filenames:
            unique_filenames.append(fn)

    # 2. Component evaluations
    # (a) Image technical quality (evaluates up to first 2 primary frames)
    img_evals = []
    for fn in unique_filenames[:2]:
        img_evals.append(evaluate_image_quality(fn))

    if img_evals:
        # Average score among inspected frames
        avg_img_score = round(sum(e["score"] for e in img_evals) / len(img_evals))
        img_warnings = [w for e in img_evals for w in e["warnings"]]
        img_info = [inf for e in img_evals for inf in e["info"]]
        img_status = "Good" if avg_img_score >= 80 else ("Fair" if avg_img_score >= 60 else "Poor")
        image_quality = {
            "score": avg_img_score,
            "status": img_status,
            "evaluated_frames": len(img_evals),
            "warnings": img_warnings,
            "info": img_info,
            "frame_details": img_evals
        }
    else:
        image_quality = {
            "score": 85,
            "status": "Unverified",
            "evaluated_frames": 0,
            "warnings": [],
            "info": ["Input frame files were not present on disk for pixel-level quality inspection."],
            "frame_details": []
        }

    # (b) Image compatibility
    compat_eval = evaluate_image_compatibility(unique_filenames)

    # (c) Optical flow displacement quality
    disp_dict = res.get("displacement")
    adv_dict = res.get("advanced_metrics")
    motion_quality = evaluate_motion_quality(disp_dict, adv_dict)

    # (d) Strain calculation quality
    strain_dict = res.get("strain_statistics")
    strain_quality = evaluate_strain_quality(strain_dict, adv_dict)

    # (e) ROI geometry quality
    roi_config = res.get("roi")
    img_shape = None
    if img_evals and img_evals[0].get("available"):
        m = img_evals[0]["metrics"]
        img_shape = (m["height"], m["width"])
    roi_quality = evaluate_roi_quality(roi_config, image_shape=img_shape)

    # (f) Tracked ROI quality
    track_sum = res.get("tracking_summary") or (roi_config.get("tracking_summary") if isinstance(roi_config, dict) else None)
    tracking_quality = evaluate_tracking_quality(track_sum)

    # (g) Temporal dynamics quality
    frame_count = res.get("frame_count") or (len(unique_filenames) if rec_type == "temporal" else None)
    p1_summary = res.get("principal_strain_1", {}).get("summary") if isinstance(res.get("principal_strain_1"), dict) else None
    temporal_quality = evaluate_temporal_quality(rec_type, p1_summary, frame_count=frame_count)

    # (h) Calibration consistency
    cal_config = res.get("calibration")
    cal_quality = evaluate_calibration_quality(cal_config)

    # 3. Transparent Weighted Score Calculation
    # Weights adapt dynamically based on which features are active in the analysis
    active_weights: Dict[str, float] = {}

    active_weights["image"] = 0.25
    active_weights["motion"] = 0.35
    active_weights["strain"] = 0.40

    if roi_quality["applicable"]:
        active_weights["image"] = 0.20
        active_weights["motion"] = 0.25
        active_weights["strain"] = 0.25
        active_weights["roi"] = 0.30

    if tracking_quality["applicable"]:
        active_weights["image"] = 0.15
        active_weights["motion"] = 0.25
        active_weights["strain"] = 0.25
        active_weights["roi"] = 0.15
        active_weights["tracking"] = 0.20

    if temporal_quality["applicable"]:
        # Distribute temporal weight
        t_weight = 0.25
        scale = 1.0 - t_weight
        for k in list(active_weights.keys()):
            active_weights[k] *= scale
        active_weights["temporal"] = t_weight

    # Normalize weights so sum is exactly 1.0
    total_w = sum(active_weights.values())
    for k in active_weights:
        active_weights[k] /= total_w

    # Calculate weighted score
    comp_score_map = {
        "image": image_quality["score"],
        "motion": motion_quality["score"],
        "strain": strain_quality["score"],
        "roi": roi_quality["score"],
        "tracking": tracking_quality["score"],
        "temporal": temporal_quality["score"],
    }

    raw_score = sum(active_weights[k] * comp_score_map[k] for k in active_weights)
    final_score = int(round(max(0.0, min(100.0, raw_score))))

    # Quality Level: 80-100 High, 60-79 Moderate, 0-59 Low
    if final_score >= 80:
        level = "High"
    elif final_score >= 60:
        level = "Moderate"
    else:
        level = "Low"

    # 4. Aggregated Warnings & Info (deduplicated)
    all_warnings = []
    for item in (
        image_quality["warnings"]
        + compat_eval["warnings"]
        + motion_quality["warnings"]
        + strain_quality["warnings"]
        + roi_quality["warnings"]
        + tracking_quality["warnings"]
        + temporal_quality["warnings"]
        + cal_quality["warnings"]
    ):
        if item and item not in all_warnings:
            all_warnings.append(item)

    all_info = []
    for item in (
        image_quality["info"]
        + compat_eval["info"]
        + motion_quality["info"]
        + strain_quality["info"]
        + roi_quality["info"]
        + tracking_quality["info"]
        + temporal_quality["info"]
        + cal_quality["info"]
    ):
        if item and item not in all_info:
            all_info.append(item)

    return {
        "score": final_score,
        "level": level,
        "components": {
            "image_quality": {
                "name": "Image Quality",
                "score": image_quality["score"],
                "status": image_quality["status"],
                "weight_pct": round(active_weights.get("image", 0.0) * 100, 1),
                "metrics": image_quality.get("frame_details", [{}])[0].get("metrics", {}) if image_quality.get("frame_details") else {},
            },
            "motion_quality": {
                "name": "Optical Flow Quality",
                "score": motion_quality["score"],
                "status": motion_quality["status"],
                "weight_pct": round(active_weights.get("motion", 0.0) * 100, 1),
                "metrics": motion_quality["metrics"],
            },
            "strain_quality": {
                "name": "Strain Tensor Consistency",
                "score": strain_quality["score"],
                "status": strain_quality["status"],
                "weight_pct": round(active_weights.get("strain", 0.0) * 100, 1),
                "metrics": strain_quality["metrics"],
            },
            "roi_quality": {
                "name": "Region of Interest (ROI)",
                "score": roi_quality["score"],
                "status": roi_quality["status"],
                "applicable": roi_quality["applicable"],
                "weight_pct": round(active_weights.get("roi", 0.0) * 100, 1),
                "metrics": roi_quality["metrics"],
            },
            "tracking_quality": {
                "name": "ROI Tracking Reliability",
                "score": tracking_quality["score"],
                "status": tracking_quality["status"],
                "applicable": tracking_quality["applicable"],
                "weight_pct": round(active_weights.get("tracking", 0.0) * 100, 1),
                "metrics": tracking_quality["metrics"],
            },
            "temporal_quality": {
                "name": "Temporal Sequence Dynamics",
                "score": temporal_quality["score"],
                "status": temporal_quality["status"],
                "applicable": temporal_quality["applicable"],
                "weight_pct": round(active_weights.get("temporal", 0.0) * 100, 1),
                "metrics": temporal_quality["metrics"],
            },
            "calibration_consistency": {
                "name": "Spatial Calibration Consistency",
                "score": cal_quality["score"],
                "status": cal_quality["status"],
                "calibrated": cal_quality["calibrated"],
                "metrics": cal_quality["metrics"],
            },
        },
        "warnings": all_warnings,
        "info": all_info,
        "weights": {k: round(v * 100, 1) for k, v in active_weights.items()},
        "disclaimer": (
            "This Computational Analysis Quality Score describes the technical consistency and numerical validity "
            "of the image-analysis pipeline. It is NOT a clinical confidence score, diagnostic measure, or patient health indicator."
        )
    }

