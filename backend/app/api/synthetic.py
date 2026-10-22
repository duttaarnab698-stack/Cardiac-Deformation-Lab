"""
backend/app/api/synthetic.py

API router for Synthetic / Phantom Data Generation and Quantitative Validation Benchmarks
for the Cardiac Deformation Lab.

Provides endpoints for:
- Generating controllable synthetic cardiac phantom datasets
- Retrieving dataset metadata, frames, and ground-truth descriptors
- Running quantitative validation benchmarks against analytical ground truth
- Running robustness sweeps across noise and blur levels
- Querying validation benchmark history
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.synthetic_data import (
    generate_synthetic_dataset,
    save_synthetic_dataset,
    get_synthetic_dataset_metadata,
    load_synthetic_dataset,
    generate_reference_image,
    generate_deformed_image,
    generate_ground_truth_displacement,
    generate_ground_truth_strain,
    SUPPORTED_DEFORMATION_MODES
)
from app.services.motion import calculate_optical_flow, calculate_displacement_magnitude
from app.services.strain import calculate_strain_tensor, calculate_principal_strains
from app.services.validation import (
    compare_estimated_vs_ground_truth,
    calculate_field_mae,
    calculate_field_rmse,
    calculate_field_correlation,
    calculate_endpoint_error
)
from app.services.validation_visualization import generate_validation_visualizations
from app.services.validation_history import (
    get_all_validation_history,
    save_validation_record,
    get_validation_record_by_id
)
import numpy as np

router = APIRouter(
    prefix="/api/synthetic",
    tags=["Synthetic Validation Benchmark"]
)


class SyntheticConfigModel(BaseModel):
    width: int = Field(256, ge=64, le=1024, description="Image width in pixels")
    height: int = Field(256, ge=64, le=1024, description="Image height in pixels")
    center_x: Optional[float] = Field(None, description="Phantom center X")
    center_y: Optional[float] = Field(None, description="Phantom center Y")
    inner_radius: float = Field(45.0, ge=5.0, description="Cavity inner radius in pixels")
    outer_radius: float = Field(75.0, ge=10.0, description="Epicardial outer radius in pixels")
    deformation_mode: str = Field(
        "radial_expansion",
        description=f"Deformation mode: {', '.join(SUPPORTED_DEFORMATION_MODES)}"
    )
    deformation_strength: float = Field(0.05, ge=0.001, le=0.30, description="Deformation strength factor")
    noise_level: float = Field(0.0, ge=0.0, le=0.20, description="Additive Gaussian noise sigma fraction")
    blur_sigma: float = Field(0.0, ge=0.0, le=5.0, description="Gaussian blur filter sigma")
    frame_count: int = Field(5, ge=2, le=20, description="Number of progressive temporal frames")


@router.post("/generate")
def generate_dataset_endpoint(config: SyntheticConfigModel):
    """
    Generate a new synthetic cardiac deformation dataset with analytical ground truth.
    Persists dataset to disk and returns metadata and frame URLs.
    """
    cfg_dict = config.dict()
    if cfg_dict.get("center_x") is None:
        cfg_dict["center_x"] = cfg_dict["width"] / 2.0
    if cfg_dict.get("center_y") is None:
        cfg_dict["center_y"] = cfg_dict["height"] / 2.0

    ds_data = generate_synthetic_dataset(cfg_dict)
    saved = save_synthetic_dataset(ds_data)

    return {
        "dataset_id": saved["dataset_id"],
        "frame_count": saved["frame_count"],
        "frames": saved["frames"],
        "metadata": saved["metadata"]
    }


@router.get("/validation/history")
def get_validation_history_endpoint():
    """Retrieve historical benchmark validation records."""
    return get_all_validation_history()


@router.get("/{dataset_id}")
def get_dataset_endpoint(dataset_id: str):
    """Retrieve metadata for a specific synthetic dataset."""
    meta = get_synthetic_dataset_metadata(dataset_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Synthetic dataset with ID '{dataset_id}' not found."
        )
    return meta


@router.get("/{dataset_id}/frames")
def get_dataset_frames_endpoint(dataset_id: str):
    """Retrieve available frame URLs and indices for a synthetic dataset."""
    meta = get_synthetic_dataset_metadata(dataset_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Synthetic dataset with ID '{dataset_id}' not found."
        )
    return {
        "dataset_id": dataset_id,
        "frame_count": meta.get("frame_count", 0),
        "frames": meta.get("frame_urls", []),
        "filenames": meta.get("frame_filenames", [])
    }


@router.get("/{dataset_id}/ground-truth")
def get_dataset_ground_truth_endpoint(dataset_id: str):
    """
    Retrieve descriptive summary and available fields for ground-truth data.
    Does not transmit large raw numpy arrays over HTTP.
    """
    meta = get_synthetic_dataset_metadata(dataset_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Synthetic dataset with ID '{dataset_id}' not found."
        )

    gt_summary = meta.get("ground_truth_summary", {})
    return {
        "dataset_id": dataset_id,
        "available_fields": [
            "displacement_u",
            "displacement_v",
            "displacement_magnitude",
            "strain_exx",
            "strain_eyy",
            "strain_exy",
            "principal_strain_1",
            "principal_strain_2",
            "radial",
            "circumferential",
            "myocardial_mask"
        ],
        "summary": gt_summary,
        "description": "Ground truth generated analytically from mathematical transformation."
    }


@router.post("/{dataset_id}/validate")
def validate_synthetic_dataset_endpoint(dataset_id: str):
    """
    Run algorithmic motion estimation and strain calculation on the synthetic dataset,
    and quantitatively benchmark against exact mathematical ground truth.
    """
    loaded = load_synthetic_dataset(dataset_id)
    if not loaded:
        raise HTTPException(
            status_code=404,
            detail=f"Synthetic dataset with ID '{dataset_id}' not found."
        )

    frames = loaded.get("frames", [])
    if len(frames) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Synthetic dataset '{dataset_id}' contains fewer than 2 frames."
        )

    gt = loaded.get("ground_truth")
    if not gt:
        raise HTTPException(
            status_code=500,
            detail=f"Ground truth data missing for dataset '{dataset_id}'."
        )

    # Reference frame (t=0) and terminal deformed frame
    ref_frame = frames[0]
    def_frame = frames[-1]

    # 1. Run project's existing optical flow motion estimation
    flow = calculate_optical_flow(ref_frame, def_frame)
    est_u = flow[..., 0]
    est_v = flow[..., 1]
    est_mag = calculate_displacement_magnitude(flow)

    # 2. Run project's existing strain tensor calculation
    exx, eyy, exy = calculate_strain_tensor(flow)
    p1, p2 = calculate_principal_strains(exx, eyy, exy)

    # 3. Compute estimated radial and circumferential deformation
    meta = loaded.get("metadata", {})
    cfg = meta.get("config", {})
    cx = cfg.get("center_x", ref_frame.shape[1] / 2.0)
    cy = cfg.get("center_y", ref_frame.shape[0] / 2.0)

    h, w = ref_frame.shape[:2]
    grid_y, grid_x = np.indices((h, w), dtype=np.float32)
    theta = np.arctan2(grid_y - cy, grid_x - cx)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    est_radial = (exx * (cos_t**2) + eyy * (sin_t**2) + 2.0 * exy * sin_t * cos_t).astype(np.float32)
    est_circ = (exx * (sin_t**2) + eyy * (cos_t**2) - 2.0 * exy * sin_t * cos_t).astype(np.float32)

    estimated_bundle = {
        "displacement_u": est_u,
        "displacement_v": est_v,
        "displacement_magnitude": est_mag,
        "strain": {
            "exx": exx,
            "eyy": eyy,
            "exy": exy,
            "principal_1": p1,
            "principal_2": p2
        },
        "radial": est_radial,
        "circumferential": est_circ
    }

    ground_truth_bundle = {
        "displacement_u": gt["displacement_u"],
        "displacement_v": gt["displacement_v"],
        "displacement_magnitude": gt["displacement_magnitude"],
        "strain": {
            "exx": gt["strain_exx"],
            "eyy": gt["strain_eyy"],
            "exy": gt["strain_exy"],
            "principal_1": gt["principal_strain_1"],
            "principal_2": gt["principal_strain_2"]
        },
        "radial": gt["radial"],
        "circumferential": gt["circumferential"]
    }

    myo_mask = gt.get("myocardial_mask")

    # 4. Quantitative comparison against ground truth
    val_comparison = compare_estimated_vs_ground_truth(
        estimated_bundle,
        ground_truth_bundle,
        myocardial_mask=myo_mask
    )

    # 5. Generate validation visual heatmaps
    visualizations = generate_validation_visualizations(
        dataset_id=dataset_id,
        estimated=estimated_bundle,
        ground_truth=ground_truth_bundle,
        mask=myo_mask
    )

    # Summaries for response
    estimated_summary = {
        "mean_displacement": round(float(np.mean(est_mag)), 4),
        "max_displacement": round(float(np.max(est_mag)), 4),
        "myo_mean_displacement": round(float(np.mean(est_mag[myo_mask == 1])), 4) if myo_mask is not None and np.any(myo_mask == 1) else None,
        "mean_principal_strain_1": round(float(np.mean(p1)), 4),
        "mean_principal_strain_2": round(float(np.mean(p2)), 4)
    }

    warnings = []
    info = [
        "Optical flow evaluated using OpenCV Farneback algorithm.",
        "Error heatmaps computed as absolute difference |Estimated - GroundTruth|."
    ]

    epe_summary = val_comparison.get("summary", {}).get("mean_endpoint_error")
    if epe_summary is not None and epe_summary > 2.0:
        warnings.append(f"Mean endpoint error is elevated ({epe_summary:.2f} px); strong deformation or noise may affect optical flow.")

    response_payload = {
        "dataset_id": dataset_id,
        "deformation_mode": cfg.get("deformation_mode"),
        "estimated": estimated_summary,
        "ground_truth": meta.get("ground_truth_summary", {}),
        "validation": val_comparison,
        "visualizations": visualizations,
        "warnings": warnings,
        "info": info,
        "metadata": meta,
        "disclaimer": (
            "This benchmark compares image-based motion estimation with synthetic mathematical ground truth. "
            "It is a computational research benchmark and does not establish clinical validity."
        )
    }

    # Save validation run record to lightweight history
    save_validation_record({
        "dataset_id": dataset_id,
        "deformation_mode": cfg.get("deformation_mode"),
        "dimensions": f"{cfg.get('width')}x{cfg.get('height')}",
        "deformation_strength": cfg.get("deformation_strength"),
        "noise_level": cfg.get("noise_level"),
        "blur_sigma": cfg.get("blur_sigma"),
        "metrics_summary": val_comparison.get("summary", {}),
        "has_visualizations": bool(visualizations)
    })

    return response_payload


@router.post("/{dataset_id}/robustness")
def run_robustness_sweep_endpoint(dataset_id: str):
    """
    Run a multi-condition robustness sweep over varying noise levels (0.0, 0.01, 0.03, 0.05)
    and blur levels (0.0, 1.0, 2.0) for the dataset's deformation mode and geometry.
    """
    meta = get_synthetic_dataset_metadata(dataset_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=f"Synthetic dataset with ID '{dataset_id}' not found."
        )

    cfg = meta.get("config", {}).copy()
    w, h = cfg.get("width", 256), cfg.get("height", 256)
    cx, cy = cfg.get("center_x", w / 2.0), cfg.get("center_y", h / 2.0)
    r_in, r_out = cfg.get("inner_radius", 45.0), cfg.get("outer_radius", 75.0)

    # Clean ground truth (unaffected by noise or blur)
    u_gt, v_gt, mag_gt = generate_ground_truth_displacement(cfg, scale_factor=1.0)
    strain_gt = generate_ground_truth_strain(cfg, scale_factor=1.0)
    p1_gt = strain_gt["principal_1"]

    # Ring mask
    grid_y, grid_x = np.indices((h, w), dtype=np.float64)
    r = np.sqrt((grid_x - cx)**2 + (grid_y - cy)**2)
    myo_mask = ((r >= r_in) & (r <= r_out)).astype(np.uint8)

    noise_levels = [0.0, 0.01, 0.03, 0.05]
    blur_levels = [0.0, 1.0, 2.0]

    sweep_results = []

    for blur in blur_levels:
        for noise in noise_levels:
            test_cfg = cfg.copy()
            test_cfg["noise_level"] = noise
            test_cfg["blur_sigma"] = blur

            # Generate pair
            ref_img = generate_reference_image(test_cfg)
            def_img = generate_deformed_image(test_cfg, scale_factor=1.0)

            # Optical flow & strain
            flow = calculate_optical_flow(ref_img, def_img)
            est_u = flow[..., 0]
            est_v = flow[..., 1]
            est_mag = calculate_displacement_magnitude(flow)

            exx, eyy, exy = calculate_strain_tensor(flow)
            p1_est, _ = calculate_principal_strains(exx, eyy, exy)

            # Metrics on myocardial ring
            disp_rmse = calculate_field_rmse(est_mag, mag_gt, mask=myo_mask)
            disp_mae = calculate_field_mae(est_mag, mag_gt, mask=myo_mask)
            disp_corr = calculate_field_correlation(est_mag, mag_gt, mask=myo_mask)
            epe = calculate_endpoint_error(est_u, est_v, u_gt, v_gt, mask=myo_mask)

            strain_rmse = calculate_field_rmse(p1_est, p1_gt, mask=myo_mask)
            strain_mae = calculate_field_mae(p1_est, p1_gt, mask=myo_mask)
            strain_corr = calculate_field_correlation(p1_est, p1_gt, mask=myo_mask)

            sweep_results.append({
                "noise_level": noise,
                "blur_sigma": blur,
                "displacement_rmse": disp_rmse,
                "displacement_mae": disp_mae,
                "displacement_correlation": disp_corr,
                "mean_endpoint_error": epe.get("mean_endpoint_error"),
                "strain_rmse": strain_rmse,
                "strain_mae": strain_mae,
                "strain_correlation": strain_corr
            })

    return {
        "dataset_id": dataset_id,
        "deformation_mode": cfg.get("deformation_mode"),
        "sweep_count": len(sweep_results),
        "results": sweep_results,
        "explanation": (
            "Robustness benchmark measures optical flow and strain degradation "
            "as additive Gaussian noise and Gaussian blur are systematically varied."
        )
    }

