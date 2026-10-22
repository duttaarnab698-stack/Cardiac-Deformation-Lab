from fastapi import APIRouter, Depends, HTTPException, Query
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.temporal import analyze_temporal_strain
from app.services.fingerprint import create_cardiac_deformation_fingerprint
from app.services.history import save_analysis_result
from app.services.studies import get_study_by_id, add_analysis_to_study
from app.core.auth import get_current_user_optional
from app.services.calibration import (
    validate_calibration,
    calculate_calibrated_motion_statistics,
    calculate_physical_displacement_magnitude,
)
from app.services.roi import (
    validate_and_create_roi_mask,
    calculate_masked_displacement_statistics,
    calculate_masked_strain_statistics,
    calculate_masked_advanced_metrics,
    calculate_masked_cardiac_deformation,
)
from app.services.roi_visualization import create_roi_overlay
from app.services.roi_tracking import track_roi_across_frames
from app.services.roi_tracking_visualization import generate_tracking_visualizations
from app.services.quality_control import evaluate_analysis_quality
import json
import numpy as np

from app.services.image_processing import (
    load_image,
    preprocess_image,
    save_processed_image
)

from app.services.motion import (
    calculate_optical_flow,
    calculate_displacement_magnitude,
    calculate_motion_statistics
)

from app.services.displacement import (
    create_displacement_heatmap,
    create_motion_vector_map
)

from app.services.strain import (
    calculate_strain_tensor,
    calculate_principal_strains,
    calculate_strain_statistics,
    create_strain_heatmap,
    create_principal_strain_heatmap,
    calculate_principal_strain_direction,
    create_principal_direction_map
)

from app.services.metrics import (
    calculate_motion_coherence,
    calculate_strain_gradient,
    calculate_strain_anisotropy,
    calculate_strain_entropy,
    calculate_deformation_energy,
    create_metric_heatmap,
    calculate_radial_circumferential_deformation,
    create_signed_metric_heatmap
)

router = APIRouter(
    prefix="/api/analysis",
    tags=["Analysis"]
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")


@router.post("/preprocess")
async def preprocess(image_filename: str):
    """
    Preprocess a single cardiac image with path traversal protection.
    """
    from app.core.security import resolve_safe_path
    image_path = resolve_safe_path(UPLOAD_DIR, image_filename)

    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Image not found: {image_filename}"
        )

    try:
        image = load_image(str(image_path))
        processed = preprocess_image(image)

        output_filename = f"preprocessed_{image_filename}"
        output_path = OUTPUT_DIR / output_filename

        save_processed_image(processed, str(output_path))

        return {
            "message": "Image preprocessed successfully",
            "input_image": image_filename,
            "output_image": output_filename,
            "output_path": str(output_path)
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/displacement")
async def displacement_analysis(
    image1_filename: str,
    image2_filename: str
):
    """
    Calculate apparent displacement between two cardiac images
    using dense Farneback optical flow.
    """

    from app.core.security import resolve_safe_path
    image1_path = resolve_safe_path(UPLOAD_DIR, image1_filename)
    image2_path = resolve_safe_path(UPLOAD_DIR, image2_filename)

    if not image1_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"First image not found: {image1_filename}"
        )

    if not image2_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Second image not found: {image2_filename}"
        )

    try:
        # Load images
        image1 = load_image(str(image1_path))
        image2 = load_image(str(image2_path))

        # Calculate dense optical flow
        flow = calculate_optical_flow(image1, image2)

        # Calculate displacement magnitude: D(x,y) = sqrt(u² + v²)
        magnitude = calculate_displacement_magnitude(flow)

        # Calculate statistics
        statistics = calculate_motion_statistics(flow)

        # Build output filenames
        stem = Path(image1_filename).stem
        heatmap_filename = f"displacement_heatmap_{stem}.jpg"
        vector_filename = f"motion_vectors_{stem}.jpg"

        heatmap_path = OUTPUT_DIR / heatmap_filename
        vector_path = OUTPUT_DIR / vector_filename

        # Ensure outputs directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate visualizations
        create_displacement_heatmap(magnitude, str(heatmap_path))
        create_motion_vector_map(image1, flow, str(vector_path))

        return {
            "message": "Displacement analysis completed",
            "image1": image1_filename,
            "image2": image2_filename,
            "mean_displacement": statistics["mean_displacement"],
            "max_displacement": statistics["max_displacement"],
            "min_displacement": statistics["min_displacement"],
            "std_displacement": statistics["std_displacement"],
            "heatmap": str(heatmap_path),
            "motion_vector_map": str(vector_path)
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/strain")
async def strain_analysis(
    image1_filename: str,
    image2_filename: str,
    pixel_spacing_x: float = None,
    pixel_spacing_y: float = None,
    unit: str = "mm",
    roi: str = None,
    study_id: Optional[str] = Query(None, description="Optional study ID to link and inherit ownership"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Calculate apparent strain fields between two cardiac images
    using dense Farneback optical flow and small-deformation
    strain tensor decomposition.

    Optional spatial calibration (pixel_spacing_x, pixel_spacing_y, unit)
    converts pixel-space displacement into physical distance.
    Strain metrics remain dimensionless continuum quantities.

    Optional Region of Interest (ROI) parameter (JSON string) restricts
    statistical calculations to user-defined rectangle, ellipse, or polygon.
    Full-image metrics are preserved for direct comparison.
    """
    # Validate optional calibration parameters
    is_valid_cal, cal_error = validate_calibration(pixel_spacing_x, pixel_spacing_y, unit)
    if not is_valid_cal:
        raise HTTPException(
            status_code=400,
            detail=cal_error
        )

    # Parse and validate optional ROI configuration
    roi_config = None
    if roi:
        try:
            roi_config = json.loads(roi) if isinstance(roi, str) else roi
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ROI JSON parameter: {str(e)}"
            )

    from app.core.security import resolve_safe_path
    image1_path = resolve_safe_path(UPLOAD_DIR, image1_filename)
    image2_path = resolve_safe_path(UPLOAD_DIR, image2_filename)

    if not image1_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"First image not found: {image1_filename}"
        )

    if not image2_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Second image not found: {image2_filename}"
        )

    try:
        # Load images
        image1 = load_image(str(image1_path))
        image2 = load_image(str(image2_path))

        h, w = image1.shape[:2]

        # Validate ROI mask if specified
        roi_mask = None
        if roi_config and roi_config.get("enabled"):
            is_valid_roi, roi_err, roi_mask = validate_and_create_roi_mask(roi_config, h, w)
            if not is_valid_roi:
                raise HTTPException(
                    status_code=400,
                    detail=roi_err
                )

        # Calculate dense optical flow
        flow = calculate_optical_flow(image1, image2)

        # Calculate full-image displacement statistics (dual pixel-space and optional physical-space)
        displacement_statistics = calculate_calibrated_motion_statistics(
            flow,
            pixel_spacing_x=pixel_spacing_x,
            pixel_spacing_y=pixel_spacing_y,
            unit=unit
        )

        # Calculate strain tensor components (dimensionless)
        exx, eyy, exy = calculate_strain_tensor(flow)

        # Calculate principal strains
        principal_strain_1, principal_strain_2 = (
            calculate_principal_strains(exx, eyy, exy)
        )

        # Calculate principal strain direction angles (radians)
        theta = calculate_principal_strain_direction(exx, eyy, exy)

        # Calculate strain statistics
        statistics = calculate_strain_statistics(
            exx,
            eyy,
            exy,
            principal_strain_1,
            principal_strain_2
        )

        # Build output filenames using the image stem
        stem = Path(image1_filename).stem

        disp_heatmap_path = OUTPUT_DIR / f"displacement_heatmap_{stem}.jpg"
        vector_path    = OUTPUT_DIR / f"motion_vectors_{stem}.jpg"
        exx_path       = OUTPUT_DIR / f"strain_exx_{stem}.jpg"
        eyy_path       = OUTPUT_DIR / f"strain_eyy_{stem}.jpg"
        exy_path       = OUTPUT_DIR / f"strain_exy_{stem}.jpg"
        p1_path        = OUTPUT_DIR / f"principal_strain_{stem}.jpg"
        dir_map_path   = OUTPUT_DIR / f"principal_direction_{stem}.jpg"

        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate displacement visualizations
        magnitude = calculate_displacement_magnitude(flow)
        create_displacement_heatmap(magnitude, str(disp_heatmap_path))
        create_motion_vector_map(image1, flow, str(vector_path))

        # Generate heatmaps
        create_strain_heatmap(exx, str(exx_path))
        create_strain_heatmap(eyy, str(eyy_path))
        create_strain_heatmap(exy, str(exy_path))
        create_principal_strain_heatmap(
            principal_strain_1,
            str(p1_path)
        )

        # Generate principal direction map
        create_principal_direction_map(
            image1,
            principal_strain_1,
            theta,
            str(dir_map_path)
        )

        # ── Advanced metrics ─────────────────────────────────────────────
        coherence_result = calculate_motion_coherence(flow)

        gradient_result = calculate_strain_gradient(
            principal_strain_1
        )

        anisotropy_result = calculate_strain_anisotropy(
            principal_strain_1,
            principal_strain_2
        )

        entropy_result = calculate_strain_entropy(
            principal_strain_1
        )

        energy_result = calculate_deformation_energy(
            exx, eyy, exy
        )

        # ── Advanced metric heatmaps ──────────────────────────────────────
        coherence_path = OUTPUT_DIR / f"motion_coherence_{stem}.jpg"
        gradient_path  = OUTPUT_DIR / f"strain_gradient_{stem}.jpg"
        anisotropy_path = OUTPUT_DIR / f"anisotropy_{stem}.jpg"
        energy_path    = OUTPUT_DIR / f"deformation_energy_{stem}.jpg"

        create_metric_heatmap(
            coherence_result["map"], str(coherence_path)
        )
        create_metric_heatmap(
            gradient_result["map"], str(gradient_path)
        )
        create_metric_heatmap(
            anisotropy_result["map"], str(anisotropy_path)
        )
        create_metric_heatmap(
            energy_result["map"], str(energy_path)
        )

        # ── Radial & circumferential deformation ──────────────────────────
        radial_result = calculate_radial_circumferential_deformation(flow)

        radial_path = (
            OUTPUT_DIR / f"radial_deformation_{stem}.jpg"
        )
        circumferential_path = (
            OUTPUT_DIR / f"circumferential_deformation_{stem}.jpg"
        )

        create_signed_metric_heatmap(
            radial_result["radial_map"],
            str(radial_path)
        )
        create_signed_metric_heatmap(
            radial_result["circumferential_map"],
            str(circumferential_path)
        )

        advanced_metrics_data = {
            "motion_coherence": {
                "mean": coherence_result["mean"],
                "min":  float(coherence_result["map"].min()),
                "max":  float(coherence_result["map"].max())
            },
            "strain_gradient": {
                "mean": gradient_result["mean"],
                "max":  gradient_result["max"]
            },
            "anisotropy": {
                "mean": anisotropy_result["mean"],
                "max":  anisotropy_result["max"]
            },
            "entropy": entropy_result["entropy"],
            "deformation_energy": {
                "mean": energy_result["mean"],
                "max":  energy_result["max"]
            }
        }

        # ── Cardiac Deformation Fingerprint ─────────────────────────────
        fingerprint = create_cardiac_deformation_fingerprint(
            displacement_statistics=displacement_statistics,
            strain_statistics=statistics,
            advanced_metrics=advanced_metrics_data,
            temporal_metrics=None
        )

        # ── Region of Interest (ROI) Analysis (Optional) ──────────────────
        roi_metrics = None
        roi_outputs = {}
        roi_fingerprint = None
        analysis_scope = {
            "mode": "full_image" if roi_mask is None else "roi",
            "roi_type": roi_config.get("type") if (roi_config and roi_mask is not None) else None,
            "pixel_count": int(np.count_nonzero(roi_mask)) if roi_mask is not None else int(h * w),
        }

        if roi_mask is not None:
            # 1. Overlay image
            roi_overlay_path = OUTPUT_DIR / f"roi_overlay_{stem}.jpg"
            create_roi_overlay(
                image=image1,
                mask=roi_mask,
                output_path=str(roi_overlay_path),
                roi_type=roi_config.get("type", "roi")
            )
            roi_outputs["roi_overlay"] = str(roi_overlay_path)

            # 2. Masked metrics calculations
            roi_disp_stats = calculate_masked_displacement_statistics(
                flow=flow,
                mask=roi_mask,
                pixel_spacing_x=pixel_spacing_x,
                pixel_spacing_y=pixel_spacing_y,
                unit=unit
            )

            roi_strain_stats = calculate_masked_strain_statistics(
                exx=exx,
                eyy=eyy,
                exy=exy,
                principal_1=principal_strain_1,
                principal_2=principal_strain_2,
                mask=roi_mask
            )

            roi_adv_metrics = calculate_masked_advanced_metrics(
                coherence_map=coherence_result["map"],
                gradient_map=gradient_result["map"],
                anisotropy_map=anisotropy_result["map"],
                energy_map=energy_result["map"],
                principal_strain_1=principal_strain_1,
                mask=roi_mask
            )

            roi_cardiac_def = calculate_masked_cardiac_deformation(
                radial_map=radial_result["radial_map"],
                circumferential_map=radial_result["circumferential_map"],
                mask=roi_mask
            )

            # 3. Dedicated ROI Fingerprint
            roi_fingerprint = create_cardiac_deformation_fingerprint(
                displacement_statistics=roi_disp_stats,
                strain_statistics=roi_strain_stats,
                advanced_metrics=roi_adv_metrics,
                temporal_metrics=None
            )

            roi_metrics = {
                "displacement": roi_disp_stats,
                "strain_statistics": roi_strain_stats,
                "advanced_metrics": roi_adv_metrics,
                "cardiac_deformation": roi_cardiac_def,
                "fingerprint": roi_fingerprint,
                "pixel_count": int(np.count_nonzero(roi_mask)),
            }

        full_image_metrics = {
            "displacement": displacement_statistics,
            "strain_statistics": statistics,
            "advanced_metrics": advanced_metrics_data,
            "cardiac_deformation": {
                "radial": {
                    "mean": radial_result["radial_mean"],
                    "max":  radial_result["radial_max"],
                    "min":  radial_result["radial_min"]
                },
                "circumferential": {
                    "mean": radial_result["circumferential_mean"],
                    "max":  radial_result["circumferential_max"],
                    "min":  radial_result["circumferential_min"]
                }
            },
            "fingerprint": fingerprint,
            "pixel_count": int(h * w),
        }

        analysis_result = {
            "message": "Strain analysis completed",
            "image1": image1_filename,
            "image2": image2_filename,

            # Analysis Scope
            "analysis_scope": analysis_scope,

            # Direct top-level access (for backward compatibility)
            "displacement": displacement_statistics,
            "strain_statistics": statistics,
            "mean_principal_direction_radians": float(
                theta.mean()
            ),
            "advanced_metrics": advanced_metrics_data,
            "cardiac_deformation": full_image_metrics["cardiac_deformation"],
            "cardiac_deformation_fingerprint": fingerprint,

            # Categorized dual-scope metrics
            "full_image_metrics": full_image_metrics,
            "roi_metrics": roi_metrics,

            # Outputs
            "outputs": {
                "displacement_heatmap":     str(disp_heatmap_path),
                "motion_vector_map":        str(vector_path),
                "exx_heatmap":              str(exx_path),
                "eyy_heatmap":              str(eyy_path),
                "exy_heatmap":              str(exy_path),
                "principal_strain_heatmap": str(p1_path),
                "principal_direction_map":  str(dir_map_path),
                **roi_outputs,
            },

            "advanced_outputs": {
                "motion_coherence_map":   str(coherence_path),
                "strain_gradient_map":    str(gradient_path),
                "anisotropy_map":         str(anisotropy_path),
                "deformation_energy_map": str(energy_path)
            },

            "cardiac_deformation_outputs": {
                "radial_map":          str(radial_path),
                "circumferential_map": str(circumferential_path)
            },

            "roi_fingerprint": roi_fingerprint,

            "calibration": {
                "enabled": bool(pixel_spacing_x is not None and pixel_spacing_y is not None),
                "pixel_spacing_x": float(pixel_spacing_x) if pixel_spacing_x is not None else None,
                "pixel_spacing_y": float(pixel_spacing_y) if pixel_spacing_y is not None else None,
                "unit": unit.strip().lower() if pixel_spacing_x is not None else None,
            },

            "roi": {
                "enabled": bool(roi_mask is not None),
                "type": roi_config.get("type") if (roi_config and roi_mask is not None) else None,
                "coordinates": roi_config.get("coordinates") if (roi_config and roi_mask is not None) else None,
                "pixel_count": int(np.count_nonzero(roi_mask)) if roi_mask is not None else None,
            }
        }

        # Compute computational quality control
        try:
            analysis_result["quality_control"] = evaluate_analysis_quality(analysis_result, record_type="single_pair")
        except Exception:
            analysis_result["quality_control"] = None

        # Automatically save single-pair analysis to history with owner inheritance
        try:
            analysis_owner_id = None
            if study_id:
                try:
                    st_rec = get_study_by_id(study_id)
                    if st_rec:
                        analysis_owner_id = st_rec.get("owner_id")
                except Exception:
                    pass
            if not analysis_owner_id and current_user:
                analysis_owner_id = current_user.get("id")

            saved_rec = save_analysis_result(analysis_result, record_type="single_pair", owner_id=analysis_owner_id)
            analysis_result["analysis_id"] = saved_rec["id"]
            analysis_result["id"] = saved_rec["id"]
            analysis_result["owner_id"] = analysis_owner_id

            if study_id:
                try:
                    add_analysis_to_study(study_id, saved_rec["id"])
                except Exception:
                    pass
        except Exception:
            pass

        return analysis_result

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/roi/track-preview")
async def roi_track_preview(
    filenames: List[str] = Query(
        ...,
        description="List of uploaded image filenames representing consecutive cardiac frames. At least 2 frames required."
    ),
    roi: str = Query(
        ...,
        description="JSON string representing ROI configuration with enabled, type, coordinates, and mode."
    )
):
    """
    Generate an instantaneous preview of ROI tracking across frames.
    Renders keyframe overlays (first, middle, last) and computes tracking path,
    per-frame coordinates, and confidence metrics without computing full strain fields.
    """
    if len(filenames) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 frames are required for ROI tracking preview."
        )

    try:
        roi_config = json.loads(roi) if isinstance(roi, str) else roi
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ROI JSON parameter: {str(e)}"
        )

    if not roi_config or not roi_config.get("enabled"):
        raise HTTPException(
            status_code=400,
            detail="ROI must be enabled to generate tracking preview."
        )

    from app.core.security import resolve_safe_path
    frame_paths = []
    for fname in filenames:
        path = resolve_safe_path(UPLOAD_DIR, fname)
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Image not found: {fname}"
            )
        frame_paths.append(path)

    try:
        frames = [
            load_image(str(p))
            for p in frame_paths
        ]

        first_shape = frames[0].shape[:2]
        h, w = first_shape
        for idx, f in enumerate(frames[1:], start=2):
            if f.shape[:2] != first_shape:
                raise HTTPException(
                    status_code=400,
                    detail=f"Frame dimension mismatch: Frame 1 is {first_shape[1]}x{first_shape[0]}, but Frame {idx} is {f.shape[1]}x{f.shape[0]}."
                )

        # Validate initial ROI mask
        is_valid_roi, roi_err, roi_mask = validate_and_create_roi_mask(roi_config, h, w)
        if not is_valid_roi:
            raise HTTPException(
                status_code=400,
                detail=roi_err
            )

        # Run tracking across frames
        track_res = track_roi_across_frames(frames, roi_config)

        # Generate keyframe preview overlays
        previews = generate_tracking_visualizations(
            frames=frames,
            tracking_path=track_res["tracking_path"],
            masks=track_res["masks"],
            output_dir=OUTPUT_DIR,
            stem_prefix="roi_preview_"
        )

        return {
            "message": "ROI tracking preview generated successfully",
            "frame_count": len(frames),
            "tracking_summary": track_res["tracking_summary"],
            "tracking_path": track_res["tracking_path"],
            "previews": previews,
            "warning": track_res.get("warning")
        }

    except HTTPException:
        raise
    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/temporal-strain")
async def temporal_strain_analysis(
    filenames: List[str] = Query(
        ...,
        description="List of uploaded image filenames representing consecutive cardiac frames. At least 2 frames required."
    ),
    pixel_spacing_x: float = None,
    pixel_spacing_y: float = None,
    unit: str = "mm",
    roi: str = None,
    study_id: Optional[str] = Query(None, description="Optional study ID to link and inherit ownership"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    Perform temporal strain analysis across a sequence of consecutive
    cardiac image frames.

    Requires at least 2 frames from backend/uploads/.
    Processes consecutive frame pairs and computes temporal stability
    descriptors for principal strains.

    Optional calibration converts displacement metrics into physical units.
    Strain metrics remain dimensionless.

    Optional ROI parameter restricts temporal metric calculations to a user-defined
    region across frames, validating that all frame dimensions match. Supports both
    fixed ROI mode and tracked ROI mode across cine frames.
    """
    # Validate optional calibration parameters
    is_valid_cal, cal_error = validate_calibration(pixel_spacing_x, pixel_spacing_y, unit)
    if not is_valid_cal:
        raise HTTPException(
            status_code=400,
            detail=cal_error
        )

    # Parse and validate optional ROI configuration
    roi_config = None
    if roi:
        try:
            roi_config = json.loads(roi) if isinstance(roi, str) else roi
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ROI JSON parameter: {str(e)}"
            )

    from app.core.config import MAX_TEMPORAL_FRAMES
    from app.core.security import resolve_safe_path

    # Validate frame count
    if len(filenames) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 images are required for temporal strain analysis."
        )

    if len(filenames) > MAX_TEMPORAL_FRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Temporal sequence exceeds maximum allowed frames ({MAX_TEMPORAL_FRAMES})."
        )

    # Verify all files exist safely before loading
    frame_paths = []
    for fname in filenames:
        path = resolve_safe_path(UPLOAD_DIR, fname)
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Image not found: {fname}"
            )
        frame_paths.append(path)

    try:
        # Load all frames
        frames = [
            load_image(str(p))
            for p in frame_paths
        ]

        # Check frame dimensions across all sequence frames
        first_shape = frames[0].shape[:2]
        h, w = first_shape
        for idx, f in enumerate(frames[1:], start=2):
            if f.shape[:2] != first_shape:
                raise HTTPException(
                    status_code=400,
                    detail=f"Frame dimension mismatch: Frame 1 is {first_shape[1]}x{first_shape[0]}, but Frame {idx} is {f.shape[1]}x{f.shape[0]}. All sequence frames must have identical dimensions."
                )

        # Validate initial ROI mask if specified
        roi_mask = None
        if roi_config and roi_config.get("enabled"):
            is_valid_roi, roi_err, roi_mask = validate_and_create_roi_mask(roi_config, h, w)
            if not is_valid_roi:
                raise HTTPException(
                    status_code=400,
                    detail=roi_err
                )

        # Run temporal strain analysis with optional calibration and ROI configuration
        result = analyze_temporal_strain(
            frames,
            pixel_spacing_x=pixel_spacing_x,
            pixel_spacing_y=pixel_spacing_y,
            unit=unit,
            roi_mask=roi_mask,
            roi_config=roi_config,
            output_dir=OUTPUT_DIR
        )

        # Generate cardiac deformation fingerprint for temporal sequence
        temporal_strain_stats = {
            "mean_principal_strain": (
                result.get("principal_strain_1", {})
                .get("summary", {})
                .get("mean")
            )
        }
        temporal_fingerprint = create_cardiac_deformation_fingerprint(
            displacement_statistics=result.get("displacement") or {},
            strain_statistics=temporal_strain_stats,
            advanced_metrics={},
            temporal_metrics=result
        )

        # Dedicated ROI temporal fingerprint if ROI active
        roi_temporal_fingerprint = None
        if (roi_mask is not None or (roi_config and roi_config.get("enabled"))) and result.get("roi_metrics"):
            roi_m = result["roi_metrics"]
            roi_strain_stats = {
                "mean_principal_strain": (
                    roi_m.get("principal_strain_1", {})
                    .get("summary", {})
                    .get("mean")
                )
            }
            roi_temporal_fingerprint = create_cardiac_deformation_fingerprint(
                displacement_statistics=roi_m.get("displacement") or {},
                strain_statistics=roi_strain_stats,
                advanced_metrics={},
                temporal_metrics=roi_m
            )

        is_tracked_roi = bool(roi_config and roi_config.get("enabled") and roi_config.get("mode") == "tracked")
        analysis_scope = {
            "mode": (
                "tracked_roi" if is_tracked_roi
                else ("roi" if (roi_mask is not None or (roi_config and roi_config.get("enabled"))) else "full_image")
            ),
            "roi_type": roi_config.get("type") if (roi_config and (roi_mask is not None or roi_config.get("enabled"))) else None,
            "pixel_count": int(np.count_nonzero(roi_mask)) if roi_mask is not None else int(h * w),
        }

        temporal_result = {
            "message": "Temporal strain analysis completed",
            "frame_count": result["frame_count"],
            "pair_count":  result["pair_count"],

            "analysis_scope": analysis_scope,

            # Direct top-level access
            "principal_strain_1": result["principal_strain_1"],
            "principal_strain_2": result["principal_strain_2"],
            "displacement": result.get("displacement"),
            "cardiac_deformation_fingerprint": temporal_fingerprint,

            # Tracking specific fields
            "tracking_path": result.get("tracking_path"),
            "tracking_summary": result.get("tracking_summary"),
            "tracking_previews": result.get("tracking_previews"),
            "tracking_warning": result.get("tracking_warning"),

            # Categorized comparison metrics
            "full_image_metrics": result.get("full_image_metrics"),
            "roi_metrics": result.get("roi_metrics"),
            "roi_fingerprint": roi_temporal_fingerprint,

            "calibration": {
                "enabled": bool(pixel_spacing_x is not None and pixel_spacing_y is not None),
                "pixel_spacing_x": float(pixel_spacing_x) if pixel_spacing_x is not None else None,
                "pixel_spacing_y": float(pixel_spacing_y) if pixel_spacing_y is not None else None,
                "unit": unit.strip().lower() if pixel_spacing_x is not None else None,
            },

            "roi": {
                "enabled": bool(roi_mask is not None or (roi_config and roi_config.get("enabled"))),
                "mode": roi_config.get("mode", "fixed") if roi_config else "fixed",
                "type": roi_config.get("type") if (roi_config and (roi_mask is not None or roi_config.get("enabled"))) else None,
                "coordinates": roi_config.get("coordinates") if (roi_config and (roi_mask is not None or roi_config.get("enabled"))) else None,
                "pixel_count": int(np.count_nonzero(roi_mask)) if roi_mask is not None else None,
            }
        }

        # Compute computational quality control
        try:
            temporal_result["quality_control"] = evaluate_analysis_quality(temporal_result, record_type="temporal")
        except Exception:
            temporal_result["quality_control"] = None

        # Automatically save temporal analysis to history with owner inheritance
        try:
            analysis_owner_id = None
            if study_id:
                try:
                    st_rec = get_study_by_id(study_id)
                    if st_rec:
                        analysis_owner_id = st_rec.get("owner_id")
                except Exception:
                    pass
            if not analysis_owner_id and current_user:
                analysis_owner_id = current_user.get("id")

            saved_rec = save_analysis_result(temporal_result, record_type="temporal", owner_id=analysis_owner_id)
            temporal_result["analysis_id"] = saved_rec["id"]
            temporal_result["id"] = saved_rec["id"]
            temporal_result["owner_id"] = analysis_owner_id

            if study_id:
                try:
                    add_analysis_to_study(study_id, saved_rec["id"])
                except Exception:
                    pass
        except Exception:
            pass

        return temporal_result

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )