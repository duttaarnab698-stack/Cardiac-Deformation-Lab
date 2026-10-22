"""
backend/app/services/real_validation.py

Real-Image Annotation and Reference Benchmark Service for Cardiac Deformation Lab.
Performs quantitative comparisons between algorithmic optical-flow/strain outputs
and manual reference annotations (landmarks, contours, polygons, and ROIs).

Computes:
- Landmark Euclidean Endpoint Error (EPE)
- Displacement MAE, RMSE, and absolute differences
- Contour / ROI Intersection over Union (IoU) and Dice coefficient
- Centroid distance and geometric area/perimeter differences
- Manual reference engineering strain comparisons
- Composite Research Benchmark Score (clearly labeled and non-diagnostic)

Strict non-clinical rules:
- Does not fabricate metrics when annotations are missing.
- Clearly states that manual annotations are subjective reference labels for benchmarking,
  not medical ground truth.
"""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.services.history import get_history_by_id
from app.services.annotations import get_annotations, calculate_contour_geometry
from app.services.motion import calculate_optical_flow, calculate_displacement_magnitude
from app.services.strain import calculate_strain_tensor, calculate_principal_strains
from app.services.roi import create_polygon_mask


def _safe_float(val: Any, decimals: int = 4) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (ValueError, TypeError):
        return None


def benchmark_analysis_against_annotations(analysis_id: str) -> Dict[str, Any]:
    """
    Perform multi-modal quantitative benchmark comparing an analysis's estimated motion
    and strain against user manual reference annotations.
    """
    record = get_history_by_id(analysis_id)
    if not record:
        raise ValueError(f"Analysis with ID '{analysis_id}' not found in history.")

    annotations = get_annotations(analysis_id=analysis_id)
    if not annotations:
        return {
            "analysis_id": analysis_id,
            "status": "no_annotations",
            "annotation_count": 0,
            "landmark_metrics": None,
            "displacement_metrics": None,
            "contour_metrics": None,
            "roi_metrics": None,
            "strain_comparison": None,
            "benchmark_score": None,
            "warnings": ["No manual reference annotations found for this analysis."],
            "info": ["Add landmarks or contours in the Annotation Workbench to benchmark algorithmic results."],
            "disclaimer": "Manual annotations are reference labels for computational benchmarking and do not represent clinical ground truth."
        }

    # Load analysis images to re-evaluate flow at exact annotated points
    res = record.get("result") or record
    img1_val = (
        res.get("image1")
        or res.get("image1_filename")
        or res.get("image1_path")
        or record.get("image1_path")
    )
    img2_val = (
        res.get("image2")
        or res.get("image2_filename")
        or res.get("image2_path")
        or record.get("image2_path")
    )

    flow = None
    h, w = 256, 256

    if img1_val and img2_val:
        p1 = Path(img1_val)
        p2 = Path(img2_val)
        if not p1.exists():
            p1 = Path("uploads") / str(img1_val)
        if not p2.exists():
            p2 = Path("uploads") / str(img2_val)
        if not p1.exists():
            p1 = Path("backend/uploads") / str(img1_val)
        if not p2.exists():
            p2 = Path("backend/uploads") / str(img2_val)

        if p1.exists() and p2.exists():
            im1 = cv2.imread(str(p1), cv2.IMREAD_GRAYSCALE)
            im2 = cv2.imread(str(p2), cv2.IMREAD_GRAYSCALE)
            if im1 is not None and im2 is not None:
                h, w = im1.shape[:2]
                flow = calculate_optical_flow(im1, im2)

    warnings: List[str] = []
    info: List[str] = []

    # 1. Landmark & Displacement Comparison
    # Pair landmarks by landmark_name across frame_index 0 and frame_index 1
    landmarks_f0: Dict[str, Dict[str, Any]] = {}
    landmarks_f1: Dict[str, Dict[str, Any]] = {}

    for ann in annotations:
        if ann.get("annotation_type") in ("point", "landmark"):
            lbl = ann.get("annotator_label") or ann.get("metadata", {}).get("landmark_name") or ann["id"]
            frame_idx = ann.get("frame_index", 0)
            if frame_idx == 0:
                landmarks_f0[lbl] = ann
            else:
                landmarks_f1[lbl] = ann

    # Find matching pairs
    paired_labels = set(landmarks_f0.keys()).intersection(set(landmarks_f1.keys()))
    landmark_comparisons = []
    epes = []
    abs_disp_diffs = []

    for lbl in paired_labels:
        ann0 = landmarks_f0[lbl]
        ann1 = landmarks_f1[lbl]

        p0 = ann0.get("points", [{}])[0]
        p1 = ann1.get("points", [{}])[0]

        x0, y0 = float(p0.get("x", 0)), float(p0.get("y", 0))
        x1, y1 = float(p1.get("x", 0)), float(p1.get("y", 0))

        # Manual reference displacement
        u_ref = x1 - x0
        v_ref = y1 - y0
        d_ref = math.sqrt(u_ref**2 + v_ref**2)

        # Algorithm estimated flow at (x0, y0)
        u_est, v_est, d_est = None, None, None
        epe = None
        disp_diff = None

        if flow is not None:
            ix = int(round(max(0, min(w - 1, x0))))
            iy = int(round(max(0, min(h - 1, y0))))
            u_est = float(flow[iy, ix, 0])
            v_est = float(flow[iy, ix, 1])
            d_est = math.sqrt(u_est**2 + v_est**2)

            epe = math.sqrt((u_est - u_ref)**2 + (v_est - v_ref)**2)
            disp_diff = abs(d_est - d_ref)

            epes.append(epe)
            abs_disp_diffs.append(disp_diff)

        landmark_comparisons.append({
            "landmark_label": lbl,
            "coordinate_f0": {"x": round(x0, 2), "y": round(y0, 2)},
            "coordinate_f1": {"x": round(x1, 2), "y": round(y1, 2)},
            "reference_displacement": {
                "u": round(u_ref, 4),
                "v": round(v_ref, 4),
                "magnitude": round(d_ref, 4)
            },
            "estimated_displacement": {
                "u": _safe_float(u_est),
                "v": _safe_float(v_est),
                "magnitude": _safe_float(d_est)
            } if u_est is not None else None,
            "endpoint_error": _safe_float(epe),
            "displacement_error": _safe_float(disp_diff)
        })

    landmark_metrics = None
    displacement_metrics = None

    if landmark_comparisons:
        if epes:
            mean_epe = float(np.mean(epes))
            max_epe = float(np.max(epes))
            rmse_disp = float(np.sqrt(np.mean(np.array(abs_disp_diffs)**2)))
            mae_disp = float(np.mean(abs_disp_diffs))

            landmark_metrics = {
                "paired_count": len(landmark_comparisons),
                "paired_landmark_count": len(landmark_comparisons),
                "mean_endpoint_error": _safe_float(mean_epe),
                "max_endpoint_error": _safe_float(max_epe),
                "pairs": landmark_comparisons
            }

            displacement_metrics = {
                "mae": _safe_float(mae_disp),
                "rmse": _safe_float(rmse_disp),
                "mean_reference_magnitude": _safe_float(float(np.mean([c["reference_displacement"]["magnitude"] for c in landmark_comparisons]))),
                "mean_estimated_magnitude": _safe_float(float(np.mean([c["estimated_displacement"]["magnitude"] for c in landmark_comparisons if c["estimated_displacement"]])))
            }
        else:
            landmark_metrics = {
                "paired_count": len(landmark_comparisons),
                "paired_landmark_count": len(landmark_comparisons),
                "pairs": landmark_comparisons
            }
    else:
        info.append("No paired landmarks found across frames for reference motion benchmarking.")

    # 2. Geometric Reference Strain from paired landmarks
    strain_comparison = None
    if len(paired_labels) >= 2:
        labels_list = sorted(list(paired_labels))
        segments = []
        for i in range(len(labels_list) - 1):
            lbl_a = labels_list[i]
            lbl_b = labels_list[i + 1]

            pa_0 = landmarks_f0[lbl_a]["points"][0]
            pb_0 = landmarks_f0[lbl_b]["points"][0]
            pa_1 = landmarks_f1[lbl_a]["points"][0]
            pb_1 = landmarks_f1[lbl_b]["points"][0]

            l0 = math.sqrt((pb_0["x"] - pa_0["x"])**2 + (pb_0["y"] - pa_0["y"])**2)
            l1 = math.sqrt((pb_1["x"] - pa_1["x"])**2 + (pb_1["y"] - pa_1["y"])**2)

            if l0 > 1e-4:
                ref_strain = (l1 - l0) / l0
                segments.append({
                    "segment": f"{lbl_a} — {lbl_b}",
                    "initial_length": round(l0, 2),
                    "final_length": round(l1, 2),
                    "reference_engineering_strain": round(ref_strain, 4)
                })

        if segments:
            strains_val = [s["reference_engineering_strain"] for s in segments]
            mean_ref_s = float(np.mean(strains_val))
            std_ref_s = float(np.std(strains_val)) if len(strains_val) > 1 else 0.0

            # Compare with analysis mean principal strain if available
            algo_mean_strain = (
                res.get("strain_statistics", {}).get("mean_principal_strain_1")
                or res.get("summary", {}).get("mean_principal_strain")
                or record.get("summary", {}).get("mean_principal_strain")
                or res.get("metrics", {}).get("mean_principal_strain")
                or record.get("metrics", {}).get("mean_principal_strain")
            )
            strain_diff = abs(algo_mean_strain - mean_ref_s) if algo_mean_strain is not None else None

            strain_comparison = {
                "segment_count": len(segments),
                "segments": segments,
                "mean_reference_strain": _safe_float(mean_ref_s),
                "std_reference_strain": _safe_float(std_ref_s),
                "algorithm_mean_strain": _safe_float(algo_mean_strain),
                "strain_difference": _safe_float(strain_diff),
                "interpretation": "Manual reference strain computed from paired landmark chord elongation."
            }

    # 3. Contour & ROI Comparison (IoU, Dice, Centroid)
    contour_annotations = [
        a for a in annotations if a.get("annotation_type") in ("polygon", "contour", "region") and len(a.get("points", [])) >= 3
    ]

    contour_metrics = None
    roi_metrics = None

    if contour_annotations:
        contour_evaluations = []
        for ann in contour_annotations:
            pts = ann.get("points", [])
            geom = calculate_contour_geometry(pts)
            contour_evaluations.append({
                "annotation_id": ann.get("id"),
                "label": ann.get("annotator_label"),
                "point_count": len(pts),
                "area": geom.get("area"),
                "perimeter": geom.get("perimeter"),
                "centroid": geom.get("centroid"),
                "bounding_box": geom.get("bounding_box")
            })

        contour_metrics = {
            "contour_count": len(contour_evaluations),
            "contours": contour_evaluations
        }

        # Check if analysis has an active ROI polygon to compute IoU
        analysis_roi = (
            res.get("roi")
            or record.get("roi")
            or res.get("analysis_scope", {}).get("roi")
            or record.get("analysis_scope", {}).get("roi")
        )
        if analysis_roi and analysis_roi.get("enabled"):
            roi_type = analysis_roi.get("type", "polygon")
            roi_coords = analysis_roi.get("coordinates")

            # Rasterize manual contour (use first matching contour)
            first_c = contour_annotations[0]
            mask_ann = create_polygon_mask(h, w, first_c["points"])

            # Rasterize analysis ROI
            mask_roi = None
            if roi_type == "polygon" and isinstance(roi_coords, list):
                mask_roi = create_polygon_mask(h, w, roi_coords)
            elif roi_type == "rectangle" and isinstance(roi_coords, dict):
                rx = roi_coords.get("x", 0)
                ry = roi_coords.get("y", 0)
                rw = roi_coords.get("width", 0)
                rh = roi_coords.get("height", 0)
                from app.services.roi import create_rectangular_mask
                mask_roi = create_rectangular_mask(h, w, rx, ry, rw, rh)

            if mask_roi is not None:
                intersection = np.logical_and(mask_ann, mask_roi)
                union = np.logical_or(mask_ann, mask_roi)

                int_count = int(np.sum(intersection))
                union_count = int(np.sum(union))
                ann_count = int(np.sum(mask_ann))
                roi_count = int(np.sum(mask_roi))

                iou = (int_count / union_count) if union_count > 0 else 0.0
                dice = (2.0 * int_count / (ann_count + roi_count)) if (ann_count + roi_count) > 0 else 0.0

                # Centroid distance
                c_ann = first_c.get("metadata", {}).get("centroid") or {}
                # Calculate ROI mask centroid
                roi_ys, roi_xs = np.where(mask_roi)
                c_roi_x = float(np.mean(roi_xs)) if len(roi_xs) > 0 else 0.0
                c_roi_y = float(np.mean(roi_ys)) if len(roi_ys) > 0 else 0.0
                centroid_dist = None
                if "x" in c_ann and "y" in c_ann and len(roi_xs) > 0:
                    centroid_dist = math.sqrt((c_ann["x"] - c_roi_x)**2 + (c_ann["y"] - c_roi_y)**2)

                roi_metrics = {
                    "reference_contour_label": first_c.get("annotator_label"),
                    "manual_mask_pixels": ann_count,
                    "analysis_roi_pixels": roi_count,
                    "overlap_pixels": int_count,
                    "intersection_over_union": _safe_float(iou),
                    "dice_coefficient": _safe_float(dice),
                    "iou": _safe_float(iou),
                    "dice": _safe_float(dice),
                    "centroid_distance": _safe_float(centroid_dist),
                    "area_difference": abs(ann_count - roi_count)
                }

    # 4. Composite Research Benchmark Score (clearly labeled and non-clinical)
    benchmark_score = None
    score_components = {}

    if landmark_metrics and landmark_metrics.get("mean_endpoint_error") is not None:
        # Scale EPE: 0 px -> 100, >= 5 px -> 0
        epe_v = landmark_metrics["mean_endpoint_error"]
        score_epe = max(0.0, min(100.0, (1.0 - (epe_v / 5.0)) * 100.0))
        score_components["landmark_accuracy"] = round(score_epe, 1)

    if roi_metrics and roi_metrics.get("intersection_over_union") is not None:
        iou_v = roi_metrics["intersection_over_union"]
        score_components["roi_concordance"] = round(iou_v * 100.0, 1)

    if score_components:
        comp_vals = list(score_components.values())
        benchmark_score = {
            "score": round(sum(comp_vals) / len(comp_vals), 1),
            "scale": "/100",
            "components": score_components,
            "formula": "Unweighted mean of Landmark Motion Concordance (1 - EPE/5.0px) and ROI Boundary IoU (IoU*100).",
            "label": "Research Benchmark Score (Computational Agreement Only)"
        }

    return {
        "analysis_id": analysis_id,
        "status": "computed",
        "annotation_count": len(annotations),
        "landmark_metrics": landmark_metrics,
        "displacement_metrics": displacement_metrics,
        "contour_metrics": contour_metrics,
        "roi_metrics": roi_metrics,
        "strain_comparison": strain_comparison,
        "benchmark_score": benchmark_score,
        "warnings": warnings,
        "info": info,
        "disclaimer": "Manual annotations are reference labels for computational benchmarking and do not represent clinical ground truth."
    }
