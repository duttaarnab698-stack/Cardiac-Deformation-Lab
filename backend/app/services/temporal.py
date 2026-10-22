"""
backend/app/services/temporal.py

Temporal strain analysis across a sequence of cardiac image frames.

Processes consecutive frame pairs, computes optical flow and strain
tensors, then summarises the per-pair metrics with temporal stability
descriptors.

Supports:
- Full frame temporal analysis.
- Fixed ROI temporal analysis (same mask across frames).
- Tracked ROI temporal analysis (rigid translation across frames using robust median flow).
- Keyframe preview generation (first, middle, last frame overlays).

These are experimental, image-space research descriptors and are NOT
clinically validated cardiac metrics.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from app.services.motion import calculate_optical_flow
from app.services.strain import (
    calculate_strain_tensor,
    calculate_principal_strains,
)
from app.services.metrics import (
    calculate_temporal_metric_summary,
    calculate_motion_coherence,
    calculate_strain_anisotropy as calculate_anisotropy,
    calculate_strain_gradient,
    calculate_deformation_energy,
    calculate_strain_entropy,
)
from app.services.calibration import calculate_calibrated_motion_statistics
from app.services.roi import (
    calculate_masked_displacement_statistics,
    calculate_masked_strain_statistics,
    calculate_masked_advanced_metrics,
    validate_and_create_roi_mask,
)
from app.services.roi_tracking import track_roi_across_frames
from app.services.roi_tracking_visualization import generate_tracking_visualizations


def analyze_temporal_strain(
    frames: list,
    pixel_spacing_x: float = None,
    pixel_spacing_y: float = None,
    unit: str = "mm",
    roi_mask: np.ndarray = None,
    roi_config: dict = None,
    output_dir: Optional[Path] = None,
    stem_prefix: str = "tracked_roi"
) -> dict:
    """
    Compute temporal strain statistics across a sequence of image frames.

    For every consecutive frame pair (frame_i, frame_i+1) the function:
    1. Calculates dense Farneback optical flow.
    2. Derives the small-deformation strain tensor (exx, eyy, exy).
    3. Computes principal strains (e1, e2) and advanced metrics.
    4. Evaluates masked metrics using either fixed or tracked ROI masks.

    Parameters
    ----------
    frames : list of np.ndarray
        Ordered list of BGR or grayscale images representing consecutive
        cardiac frames. Must contain at least 2 frames.
    pixel_spacing_x, pixel_spacing_y : float, optional
        Physical pixel spacing.
    unit : str, optional
        Physical measurement unit (default: "mm").
    roi_mask : np.ndarray, optional
        Static 2D boolean mask.
    roi_config : dict, optional
        Full ROI configuration specifying mode: "fixed" or "tracked".
    output_dir : Path, optional
        Directory for saving keyframe tracking preview overlays.
    stem_prefix : str, optional
        Prefix for tracking output filenames.

    Returns
    -------
    dict containing:
        - frame_count, pair_count
        - principal_strain_1, principal_strain_2, displacement
        - full_image_metrics, full_frame_temporal_metrics
        - roi_metrics, roi_temporal_metrics
        - tracking_path, tracking_summary, tracking_previews, tracking_warning
    """
    if len(frames) < 2:
        raise ValueError(
            "At least 2 frames are required for temporal strain analysis."
        )

    h, w = frames[0].shape[:2]

    # ── ROI Tracking Setup ──────────────────────────────────────────────
    is_tracked = bool(roi_config and roi_config.get("enabled") and roi_config.get("mode") == "tracked")
    is_fixed_roi = bool(
        roi_mask is not None or
        (roi_config and roi_config.get("enabled") and roi_config.get("mode") != "tracked")
    )

    tracked_masks: Optional[List[np.ndarray]] = None
    tracking_path: Optional[List[Dict[str, Any]]] = None
    tracking_summary: Optional[Dict[str, Any]] = None
    tracking_previews: Optional[Dict[str, Any]] = None
    tracking_warning: Optional[str] = None

    if is_tracked:
        # Execute robust ROI translation across all frames
        track_res = track_roi_across_frames(frames, roi_config)
        tracked_masks = track_res["masks"]
        tracking_path = track_res["tracking_path"]
        tracking_summary = track_res["tracking_summary"]
        tracking_warning = track_res.get("warning")

        # Generate keyframe tracking visualizations (first, middle, last)
        if output_dir is not None:
            tracking_previews = generate_tracking_visualizations(
                frames=frames,
                tracking_path=tracking_path,
                masks=tracked_masks,
                output_dir=output_dir,
                stem_prefix=stem_prefix
            )
    elif is_fixed_roi:
        if roi_mask is None and roi_config:
            _, _, roi_mask = validate_and_create_roi_mask(roi_config, h, w)
        if roi_mask is not None:
            tracked_masks = [roi_mask] * len(frames)

    # ── Accumulators for full-image metrics ─────────────────────────────
    p1_mean_values: list[float] = []
    p2_mean_values: list[float] = []
    p1_max_values: list[float] = []
    pair_displacement_stats: list[dict] = []
    p_coherence_values: list[float] = []
    p_anisotropy_values: list[float] = []
    p_entropy_values: list[float] = []
    p_energy_values: list[float] = []

    # ── Accumulators for ROI metrics ────────────────────────────────────
    roi_p1_mean_values: list[float] = []
    roi_p2_mean_values: list[float] = []
    roi_p1_max_values: list[float] = []
    roi_pair_displacement_stats: list[dict] = []
    roi_coherence_values: list[float] = []
    roi_anisotropy_values: list[float] = []
    roi_entropy_values: list[float] = []
    roi_energy_values: list[float] = []

    pair_count = len(frames) - 1

    for i in range(pair_count):
        frame_a = frames[i]
        frame_b = frames[i + 1]

        # 1. Optical flow between consecutive pair
        flow = calculate_optical_flow(frame_a, frame_b)

        # 2. Calibrated displacement statistics
        disp_stat = calculate_calibrated_motion_statistics(
            flow,
            pixel_spacing_x=pixel_spacing_x,
            pixel_spacing_y=pixel_spacing_y,
            unit=unit
        )
        pair_displacement_stats.append(disp_stat)

        # 3. Small-deformation strain tensor (dimensionless)
        exx, eyy, exy = calculate_strain_tensor(flow)
        principal_1, principal_2 = calculate_principal_strains(exx, eyy, exy)

        p1_mean = float(np.mean(principal_1))
        p2_mean = float(np.mean(principal_2))
        p1_max = float(np.max(principal_1))
        p1_mean_values.append(p1_mean)
        p2_mean_values.append(p2_mean)
        p1_max_values.append(p1_max)

        # 4. Advanced full-frame metrics
        coh_res = calculate_motion_coherence(flow)
        ani_res = calculate_anisotropy(principal_1, principal_2)
        grad_res = calculate_strain_gradient(principal_1)
        energy_res = calculate_deformation_energy(exx, eyy, exy)
        entropy_res = calculate_strain_entropy(principal_1)

        p_coherence_values.append(float(coh_res["mean"]))
        p_anisotropy_values.append(float(ani_res["mean"]))
        p_entropy_values.append(float(entropy_res["entropy"]))
        p_energy_values.append(float(energy_res["mean"]))

        # 5. Masked metrics (Fixed or Tracked ROI)
        if tracked_masks is not None:
            cur_roi_mask = tracked_masks[i]

            m_disp = calculate_masked_displacement_statistics(
                flow=flow,
                mask=cur_roi_mask,
                pixel_spacing_x=pixel_spacing_x,
                pixel_spacing_y=pixel_spacing_y,
                unit=unit
            )
            roi_pair_displacement_stats.append(m_disp)

            m_strain = calculate_masked_strain_statistics(
                exx=exx,
                eyy=eyy,
                exy=exy,
                principal_1=principal_1,
                principal_2=principal_2,
                mask=cur_roi_mask
            )
            roi_p1_mean = m_strain["principal_strain_1"]["mean"]
            roi_p2_mean = m_strain["principal_strain_2"]["mean"]
            roi_p1_mx = m_strain["principal_strain_1"]["max"]
            roi_p1_mean_values.append(roi_p1_mean)
            roi_p2_mean_values.append(roi_p2_mean)
            roi_p1_max_values.append(roi_p1_mx)

            m_adv = calculate_masked_advanced_metrics(
                coherence_map=coh_res["map"],
                gradient_map=grad_res["map"],
                anisotropy_map=ani_res["map"],
                energy_map=energy_res["map"],
                principal_strain_1=principal_1,
                mask=cur_roi_mask
            )
            roi_coherence_values.append(float(m_adv["motion_coherence"]["mean"]))
            roi_anisotropy_values.append(float(m_adv["anisotropy"]["mean"]))
            roi_entropy_values.append(float(m_adv["entropy"]))
            roi_energy_values.append(float(m_adv["deformation_energy"]["mean"]))

    # ── Temporal summaries for full image ───────────────────────────────
    p1_summary = calculate_temporal_metric_summary(p1_mean_values)
    p2_summary = calculate_temporal_metric_summary(p2_mean_values)
    coh_summary = calculate_temporal_metric_summary(p_coherence_values)
    ani_summary = calculate_temporal_metric_summary(p_anisotropy_values)
    entropy_summary = calculate_temporal_metric_summary(p_entropy_values)
    energy_summary = calculate_temporal_metric_summary(p_energy_values)

    overall_disp_pixel_means = [d["pixel_space"]["mean_displacement"] for d in pair_displacement_stats]
    overall_disp_pixel_maxs = [d["pixel_space"]["max_displacement"] for d in pair_displacement_stats]

    disp_pixel_space = {
        "mean_displacement": float(np.mean(overall_disp_pixel_means)) if overall_disp_pixel_means else 0.0,
        "max_displacement": float(np.max(overall_disp_pixel_maxs)) if overall_disp_pixel_maxs else 0.0,
        "min_displacement": float(np.min([d["pixel_space"]["min_displacement"] for d in pair_displacement_stats])) if pair_displacement_stats else 0.0,
        "std_displacement": float(np.std(overall_disp_pixel_means)) if overall_disp_pixel_means else 0.0,
        "unit": "px",
    }

    disp_physical_space = None
    if pixel_spacing_x is not None and pixel_spacing_y is not None:
        overall_disp_phys_means = [d["physical_space"]["mean_displacement"] for d in pair_displacement_stats]
        overall_disp_phys_maxs = [d["physical_space"]["max_displacement"] for d in pair_displacement_stats]
        clean_unit = unit.strip().lower() if isinstance(unit, str) else "mm"
        disp_physical_space = {
            "mean_displacement": float(np.mean(overall_disp_phys_means)) if overall_disp_phys_means else 0.0,
            "max_displacement": float(np.max(overall_disp_phys_maxs)) if overall_disp_phys_maxs else 0.0,
            "min_displacement": float(np.min([d["physical_space"]["min_displacement"] for d in pair_displacement_stats])) if pair_displacement_stats else 0.0,
            "std_displacement": float(np.std(overall_disp_phys_means)) if overall_disp_phys_means else 0.0,
            "unit": clean_unit,
        }

    displacement_summary = {
        "mean_displacement": disp_pixel_space["mean_displacement"],
        "max_displacement": disp_pixel_space["max_displacement"],
        "min_displacement": disp_pixel_space["min_displacement"],
        "std_displacement": disp_pixel_space["std_displacement"],
        "pixel_space": disp_pixel_space,
        "physical_space": disp_physical_space,
    }

    full_image_metrics = {
        "principal_strain_1": {
            "values":  p1_mean_values,
            "max_values": p1_max_values,
            "summary": p1_summary
        },
        "principal_strain_2": {
            "values":  p2_mean_values,
            "summary": p2_summary
        },
        "displacement": displacement_summary,
        "motion_coherence": {
            "values": p_coherence_values,
            "summary": coh_summary
        },
        "anisotropy": {
            "values": p_anisotropy_values,
            "summary": ani_summary
        },
        "entropy": {
            "values": p_entropy_values,
            "summary": entropy_summary
        },
        "deformation_energy": {
            "values": p_energy_values,
            "summary": energy_summary
        },
        "pixel_count": int(h * w),
    }

    full_frame_temporal_metrics = {
        "mean_displacement": overall_disp_pixel_means,
        "max_displacement": overall_disp_pixel_maxs,
        "mean_principal_strain": p1_mean_values,
        "max_principal_strain": p1_max_values,
        "motion_coherence": p_coherence_values,
        "anisotropy": p_anisotropy_values,
        "summary": {
            "mean_displacement": displacement_summary["mean_displacement"],
            "max_displacement": displacement_summary["max_displacement"],
            "principal_strain": p1_summary.get("mean"),
            "temporal_stability_index": p1_summary.get("temporal_stability_index"),
            "motion_coherence": coh_summary.get("mean"),
            "anisotropy": ani_summary.get("mean"),
        }
    }

    # ── Temporal summaries for ROI (Fixed or Tracked) ───────────────────
    roi_metrics = None
    roi_temporal_metrics = None

    if tracked_masks is not None:
        roi_p1_summary = calculate_temporal_metric_summary(roi_p1_mean_values)
        roi_p2_summary = calculate_temporal_metric_summary(roi_p2_mean_values)
        roi_coh_summary = calculate_temporal_metric_summary(roi_coherence_values)
        roi_ani_summary = calculate_temporal_metric_summary(roi_anisotropy_values)
        roi_entropy_summary = calculate_temporal_metric_summary(roi_entropy_values)
        roi_energy_summary = calculate_temporal_metric_summary(roi_energy_values)

        roi_disp_px_means = [d["pixel_space"]["mean_displacement"] for d in roi_pair_displacement_stats]
        roi_disp_px_maxs = [d["pixel_space"]["max_displacement"] for d in roi_pair_displacement_stats]
        roi_disp_px = {
            "mean_displacement": float(np.mean(roi_disp_px_means)) if roi_disp_px_means else 0.0,
            "max_displacement": float(np.max(roi_disp_px_maxs)) if roi_disp_px_maxs else 0.0,
            "min_displacement": float(np.min([d["pixel_space"]["min_displacement"] for d in roi_pair_displacement_stats])) if roi_pair_displacement_stats else 0.0,
            "std_displacement": float(np.std(roi_disp_px_means)) if roi_disp_px_means else 0.0,
            "unit": "px",
        }

        roi_disp_phys = None
        if pixel_spacing_x is not None and pixel_spacing_y is not None:
            clean_unit = unit.strip().lower() if isinstance(unit, str) else "mm"
            roi_phys_means = [d["physical_space"]["mean_displacement"] for d in roi_pair_displacement_stats]
            roi_phys_maxs = [d["physical_space"]["max_displacement"] for d in roi_pair_displacement_stats]
            roi_disp_phys = {
                "mean_displacement": float(np.mean(roi_phys_means)) if roi_phys_means else 0.0,
                "max_displacement": float(np.max(roi_phys_maxs)) if roi_phys_maxs else 0.0,
                "min_displacement": float(np.min([d["physical_space"]["min_displacement"] for d in roi_pair_displacement_stats])) if roi_pair_displacement_stats else 0.0,
                "std_displacement": float(np.std(roi_phys_means)) if roi_phys_means else 0.0,
                "unit": clean_unit,
            }

        roi_displacement_summary = {
            "mean_displacement": roi_disp_px["mean_displacement"],
            "max_displacement": roi_disp_px["max_displacement"],
            "min_displacement": roi_disp_px["min_displacement"],
            "std_displacement": roi_disp_px["std_displacement"],
            "pixel_space": roi_disp_px,
            "physical_space": roi_disp_phys,
        }

        initial_px_count = int(np.count_nonzero(tracked_masks[0]))

        roi_metrics = {
            "principal_strain_1": {
                "values": roi_p1_mean_values,
                "max_values": roi_p1_max_values,
                "summary": roi_p1_summary,
            },
            "principal_strain_2": {
                "values": roi_p2_mean_values,
                "summary": roi_p2_summary,
            },
            "displacement": roi_displacement_summary,
            "motion_coherence": {
                "values": roi_coherence_values,
                "summary": roi_coh_summary
            },
            "anisotropy": {
                "values": roi_anisotropy_values,
                "summary": roi_ani_summary
            },
            "entropy": {
                "values": roi_entropy_values,
                "summary": roi_entropy_summary
            },
            "deformation_energy": {
                "values": roi_energy_values,
                "summary": roi_energy_summary
            },
            "pixel_count": initial_px_count,
            "tracking_mode": "tracked" if is_tracked else "fixed",
        }

        roi_temporal_metrics = {
            "mean_displacement": roi_disp_px_means,
            "max_displacement": roi_disp_px_maxs,
            "mean_principal_strain": roi_p1_mean_values,
            "max_principal_strain": roi_p1_max_values,
            "motion_coherence": roi_coherence_values,
            "anisotropy": roi_anisotropy_values,
            "summary": {
                "mean_displacement": roi_displacement_summary["mean_displacement"],
                "max_displacement": roi_displacement_summary["max_displacement"],
                "principal_strain": roi_p1_summary.get("mean"),
                "temporal_stability_index": roi_p1_summary.get("temporal_stability_index"),
                "motion_coherence": roi_coh_summary.get("mean"),
                "anisotropy": roi_ani_summary.get("mean"),
            }
        }

    out = {
        "frame_count": len(frames),
        "pair_count":  pair_count,

        "principal_strain_1": full_image_metrics["principal_strain_1"],
        "principal_strain_2": full_image_metrics["principal_strain_2"],
        "displacement": displacement_summary,

        "full_image_metrics": full_image_metrics,
        "full_frame_temporal_metrics": full_frame_temporal_metrics,

        "roi_metrics": roi_metrics,
        "roi_temporal_metrics": roi_temporal_metrics,

        "tracking_path": tracking_path,
        "tracking_summary": tracking_summary,
        "tracking_previews": tracking_previews,
        "tracking_warning": tracking_warning,
    }

    return out
