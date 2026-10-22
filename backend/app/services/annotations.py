"""
backend/app/services/annotations.py

Lightweight JSON-based Annotation and Reference Benchmark Service
for the Cardiac Deformation Lab.

Provides:
- Storage and CRUD management for user annotations on cardiac images.
- Support for: point, polyline, polygon, contour, landmark, region.
- Geometric property derivations (area, perimeter, centroid, bounding box).
- Annotation Quality Control (point count, coordinate bounds, zero-area detection).
- Conversion from polygon/contour/region annotation to ROI data model.
- Paired landmark reference motion and geometric engineering strain calculation.
- JSON-compatible annotation import/export.
- Non-diagnostic disclaimer enforcement.
"""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.config import DATA_DIR
from app.core.security import atomic_write_json, safe_load_json

ANNOTATIONS_FILE = DATA_DIR / "annotations.json"
SUPPORTED_ANNOTATION_TYPES = ("point", "polyline", "polygon", "contour", "landmark", "region")


def _ensure_file():
    ANNOTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ANNOTATIONS_FILE.exists():
        atomic_write_json(ANNOTATIONS_FILE, [])


def _load_all_records() -> List[Dict[str, Any]]:
    _ensure_file()
    data = safe_load_json(ANNOTATIONS_FILE, list)
    if isinstance(data, list):
        for r in data:
            r.setdefault("owner_id", None)
        return data
    return []


def _save_all_records(records: List[Dict[str, Any]]) -> None:
    _ensure_file()
    atomic_write_json(ANNOTATIONS_FILE, records)


def calculate_contour_geometry(points: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Calculate image-space geometric properties for a series of polygon/contour points.
    Computes:
    - Area via the Shoelace formula
    - Perimeter via Euclidean segment summation
    - Centroid via polygon moments (or centroid mean)
    - Bounding box: {x, y, width, height}
    """
    if not points or len(points) < 3:
        if points and len(points) == 1:
            return {
                "area": 0.0,
                "perimeter": 0.0,
                "centroid": {"x": round(float(points[0]["x"]), 2), "y": round(float(points[0]["y"]), 2)},
                "bounding_box": {"x": round(float(points[0]["x"]), 2), "y": round(float(points[0]["y"]), 2), "width": 0.0, "height": 0.0}
            }
        return {
            "area": 0.0,
            "perimeter": 0.0,
            "centroid": None,
            "bounding_box": None
        }

    pts = [(float(p["x"]), float(p["y"])) for p in points]
    n = len(pts)

    # Bounding Box
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bbox = {
        "x": round(min_x, 2),
        "y": round(min_y, 2),
        "width": round(max_x - min_x, 2),
        "height": round(max_y - min_y, 2)
    }

    # Perimeter
    perimeter = 0.0
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        perimeter += math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    # Shoelace Formula for Area
    area_sum = 0.0
    cx_sum = 0.0
    cy_sum = 0.0

    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cross = (x0 * y1 - x1 * y0)
        area_sum += cross
        cx_sum += (x0 + x1) * cross
        cy_sum += (y0 + y1) * cross

    area = abs(area_sum) / 2.0

    if area > 1e-6:
        cx = abs(cx_sum / (6.0 * (area_sum / 2.0)))
        cy = abs(cy_sum / (6.0 * (area_sum / 2.0)))
        centroid = {"x": round(cx, 2), "y": round(cy, 2)}
    else:
        # Fallback to mean coordinate
        centroid = {"x": round(sum(xs) / n, 2), "y": round(sum(ys) / n, 2)}

    return {
        "area": round(area, 2),
        "perimeter": round(perimeter, 2),
        "centroid": centroid,
        "bounding_box": bbox
    }


def validate_annotation_quality(
    record: Dict[str, Any],
    image_width: Optional[int] = None,
    image_height: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform computational quality control checks on an annotation record:
    - Minimum point requirements per type
    - Coordinate finite and non-negative
    - Bounds checking against image dimensions
    - Zero-area polygon detection
    """
    errors: List[str] = []
    warnings: List[str] = []

    ann_type = str(record.get("annotation_type", "")).lower().strip()
    if ann_type not in SUPPORTED_ANNOTATION_TYPES:
        errors.append(f"Invalid annotation_type '{ann_type}'. Supported: {', '.join(SUPPORTED_ANNOTATION_TYPES)}")

    raw_points = record.get("points")
    if not raw_points or not isinstance(raw_points, list):
        errors.append("Annotation must contain a non-empty 'points' list.")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Validate coordinate data types
    valid_points = []
    for idx, p in enumerate(raw_points):
        if not isinstance(p, dict) or "x" not in p or "y" not in p:
            errors.append(f"Point at index {idx} is malformed (must have 'x' and 'y').")
            continue
        try:
            x = float(p["x"])
            y = float(p["y"])
            if math.isnan(x) or math.isinf(x) or math.isnan(y) or math.isinf(y):
                errors.append(f"Point at index {idx} contains non-finite coordinates.")
            else:
                valid_points.append({"x": x, "y": y})
        except (ValueError, TypeError):
            errors.append(f"Point at index {idx} has non-numeric coordinates.")

    n_pts = len(valid_points)

    if ann_type in ("point", "landmark") and n_pts < 1:
        errors.append(f"'{ann_type}' requires at least 1 point.")
    elif ann_type == "polyline" and n_pts < 2:
        errors.append("'polyline' requires at least 2 points.")
    elif ann_type in ("polygon", "contour", "region") and n_pts < 3:
        errors.append(f"'{ann_type}' requires at least 3 points to form an enclosed 2D shape.")

    # Image boundary check
    if image_width is not None and image_height is not None:
        out_of_bounds = 0
        for p in valid_points:
            if p["x"] < 0 or p["x"] > image_width or p["y"] < 0 or p["y"] > image_height:
                out_of_bounds += 1
        if out_of_bounds > 0:
            warnings.append(f"{out_of_bounds} point(s) lie outside nominal image boundaries ({image_width}x{image_height} px).")

    # Zero area check for polygons
    if ann_type in ("polygon", "contour", "region") and n_pts >= 3:
        geom = calculate_contour_geometry(valid_points)
        if geom.get("area", 0.0) <= 0.01:
            warnings.append("Polygon has zero or near-zero enclosed area (collinear or degenerate vertices).")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def create_annotation(record_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create and persist a new annotation record.
    Calculates derived geometry automatically for polygons/contours.
    """
    qc = validate_annotation_quality(record_data)
    if not qc["valid"]:
        raise ValueError(f"Annotation validation failed: {'; '.join(qc['errors'])}")

    ann_id = str(record_data.get("id") or uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    ann_type = record_data.get("annotation_type", "point").lower().strip()
    points = record_data.get("points", [])

    meta = record_data.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}

    geom = None
    # Calculate geometry if enclosed 2D shape
    if ann_type in ("polygon", "contour", "region") and len(points) >= 3:
        geom = calculate_contour_geometry(points)
        meta["area"] = geom["area"]
        meta["perimeter"] = geom["perimeter"]
        meta["centroid"] = geom["centroid"]
        meta["bounding_box"] = geom["bounding_box"]

    record: Dict[str, Any] = {
        "id": ann_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "owner_id": record_data.get("owner_id"),
        "analysis_id": record_data.get("analysis_id"),
        "study_id": record_data.get("study_id"),
        "image_filename": record_data.get("image_filename", ""),
        "image_type": record_data.get("image_type", "analysis_image"),
        "annotation_type": ann_type,
        "annotator_label": record_data.get("annotator_label", "manual_reference"),
        "points": points,
        "frame_index": record_data.get("frame_index", 0),
        "geometry": geom,
        "metadata": meta,
        "qc_warnings": qc["warnings"],
        "disclaimer": "Manual annotations are reference labels for computational benchmarking and do not represent clinical ground truth."
    }

    records = _load_all_records()
    records.append(record)
    _save_all_records(records)

    return record


def get_annotation(annotation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single annotation record by ID."""
    records = _load_all_records()
    for rec in records:
        if rec.get("id") == annotation_id:
            rec.setdefault("owner_id", None)
            return rec
    return None


def get_annotations(
    analysis_id: Optional[str] = None,
    image_filename: Optional[str] = None,
    study_id: Optional[str] = None,
    annotation_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve filtered annotations list based on filters and user ownership."""
    records = _load_all_records()
    filtered = []

    for r in records:
        if analysis_id and r.get("analysis_id") != analysis_id:
            continue
        if image_filename and r.get("image_filename") != image_filename:
            continue
        if study_id and r.get("study_id") != study_id:
            continue
        if annotation_type and r.get("annotation_type") != annotation_type:
            continue
        # Researcher ownership filtering
        if role == "researcher" and owner_id:
            r_owner = r.get("owner_id")
            if r_owner is not None and r_owner != owner_id:
                continue
        filtered.append(r)

    # Sort newest first
    return sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)


def update_annotation(annotation_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing annotation record."""
    records = _load_all_records()
    target_idx = None

    for idx, r in enumerate(records):
        if r.get("id") == annotation_id:
            target_idx = idx
            break

    if target_idx is None:
        return None

    existing = records[target_idx]

    # Merge fields
    for field in ("annotator_label", "annotation_type", "points", "frame_index", "analysis_id", "study_id", "image_filename", "image_type"):
        if field in update_data:
            existing[field] = update_data[field]

    if "metadata" in update_data and isinstance(update_data["metadata"], dict):
        existing["metadata"].update(update_data["metadata"])

    # Re-calculate geometry if points were updated
    ann_type = existing.get("annotation_type", "")
    pts = existing.get("points", [])
    if ann_type in ("polygon", "contour", "region") and len(pts) >= 3:
        geom = calculate_contour_geometry(pts)
        existing["geometry"] = geom
        existing["metadata"]["area"] = geom["area"]
        existing["metadata"]["perimeter"] = geom["perimeter"]
        existing["metadata"]["centroid"] = geom["centroid"]
        existing["metadata"]["bounding_box"] = geom["bounding_box"]
    else:
        existing["geometry"] = None

    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    records[target_idx] = existing
    _save_all_records(records)
    return existing


def delete_annotation(annotation_id: str) -> bool:
    """Delete a single annotation record by ID."""
    records = _load_all_records()
    initial_len = len(records)
    records = [r for r in records if r.get("id") != annotation_id]
    if len(records) < initial_len:
        _save_all_records(records)
        return True
    return False


def delete_annotations_by_analysis(analysis_id: str) -> int:
    """Delete all annotations associated with a specific analysis ID."""
    records = _load_all_records()
    initial_len = len(records)
    records = [r for r in records if r.get("analysis_id") != analysis_id]
    deleted_count = initial_len - len(records)
    if deleted_count > 0:
        _save_all_records(records)
    return deleted_count


def convert_annotation_to_roi(annotation_or_id: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert a saved polygon, contour, or region annotation (by ID or dictionary)
    into an ROI object compatible with the existing ROI services (app.services.roi).
    """
    if isinstance(annotation_or_id, dict):
        ann = annotation_or_id
        annotation_id = ann.get("id", "ad-hoc")
    else:
        annotation_id = str(annotation_or_id)
        ann = get_annotation(annotation_id)
        if not ann:
            raise ValueError(f"Annotation with ID '{annotation_id}' not found.")

    ann_type = ann.get("annotation_type", "")
    points = ann.get("points", [])

    if ann_type not in ("polygon", "contour", "region"):
        raise ValueError(f"Cannot convert '{ann_type}' to ROI. Only polygon, contour, and region can be converted.")

    if len(points) < 3:
        raise ValueError("Annotation requires at least 3 points to define an ROI mask.")

    roi_dict = {
        "enabled": True,
        "type": "polygon",
        "coordinates": points,
        "label": ann.get("annotator_label", "manual_roi"),
        "source_annotation_id": annotation_id
    }

    return roi_dict


def compute_paired_landmark_displacement(
    landmark_1: Dict[str, Any],
    landmark_2: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate manual reference displacement between paired landmarks in two frames:
        u = x2 - x1
        v = y2 - y1
        D = sqrt(u^2 + v^2)
    """
    p1 = landmark_1.get("points", [{}])[0]
    p2 = landmark_2.get("points", [{}])[0]

    x1, y1 = float(p1.get("x", 0.0)), float(p1.get("y", 0.0))
    x2, y2 = float(p2.get("x", 0.0)), float(p2.get("y", 0.0))

    u = round(x2 - x1, 4)
    v = round(y2 - y1, 4)
    magnitude = round(math.sqrt(u**2 + v**2), 4)

    return {
        "initial_point": {"x": x1, "y": y1},
        "final_point": {"x": x2, "y": y2},
        "displacement_vector": {"u": u, "v": v},
        "reference_displacement": magnitude,
        "dx": u,
        "dy": v,
        "displacement": magnitude,
        "label": "manual reference image displacement"
    }


def compute_reference_geometric_strain(
    paired_segments: Union[List[Dict[str, Any]], Dict[str, Any]],
    p2_f1: Optional[Dict[str, Any]] = None,
    p1_f2: Optional[Dict[str, Any]] = None,
    p2_f2: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate manual reference engineering strain across paired landmark segments:
    For segment between points A and B:
        L0 = initial distance in Frame 1
        L1 = final distance in Frame 2
        epsilon = (L1 - L0) / L0
    """
    if p2_f1 is not None and p1_f2 is not None and p2_f2 is not None:
        def _get_pt(obj):
            if isinstance(obj, dict):
                pts = obj.get("points")
                if isinstance(pts, list) and len(pts) > 0:
                    return pts[0]
                return obj
            return {"x": 0.0, "y": 0.0}

        segments_to_process = [{
            "p1_f1": _get_pt(paired_segments),
            "p2_f1": _get_pt(p2_f1),
            "p1_f2": _get_pt(p1_f2),
            "p2_f2": _get_pt(p2_f2)
        }]
    elif isinstance(paired_segments, list):
        segments_to_process = paired_segments
    else:
        segments_to_process = [paired_segments]

    strains = []
    segment_details = []

    for seg in segments_to_process:
        p1_f1 = seg["p1_f1"]
        p2_f1 = seg["p2_f1"]
        p1_f2 = seg["p1_f2"]
        p2_f2 = seg["p2_f2"]

        l0 = math.sqrt((p2_f1["x"] - p1_f1["x"])**2 + (p2_f1["y"] - p1_f1["y"])**2)
        l1 = math.sqrt((p2_f2["x"] - p1_f2["x"])**2 + (p2_f2["y"] - p1_f2["y"])**2)

        if l0 > 1e-5:
            eps = (l1 - l0) / l0
            strains.append(eps)
            segment_details.append({
                "l0": round(l0, 4),
                "l1": round(l1, 4),
                "initial_length": round(l0, 4),
                "final_length": round(l1, 4),
                "engineering_strain": round(eps, 4),
                "percent_strain": round(eps * 100.0, 2)
            })

    if not strains:
        return {
            "mean_reference_strain": None,
            "min_reference_strain": None,
            "max_reference_strain": None,
            "std_reference_strain": None,
            "segment_count": 0,
            "segments": []
        }

    mean_s = sum(strains) / len(strains)
    std_s = math.sqrt(sum((s - mean_s)**2 for s in strains) / len(strains)) if len(strains) > 1 else 0.0

    res_out = {
        "mean_reference_strain": round(mean_s, 4),
        "min_reference_strain": round(min(strains), 4),
        "max_reference_strain": round(max(strains), 4),
        "std_reference_strain": round(std_s, 4),
        "segment_count": len(strains),
        "segments": segment_details,
        "disclaimer": "Manual geometric reference strain represents chord elongation between landmarks and does not establish clinical strain ground truth."
    }

    if len(segment_details) == 1:
        res_out["initial_length"] = segment_details[0]["initial_length"]
        res_out["final_length"] = segment_details[0]["final_length"]
        res_out["engineering_strain"] = segment_details[0]["engineering_strain"]
        res_out["percent_strain"] = segment_details[0]["percent_strain"]

    return res_out


def export_annotations(analysis_id: str) -> Dict[str, Any]:
    """Export all annotations for an analysis as a portable JSON package."""
    ann_list = get_annotations(analysis_id=analysis_id)
    return {
        "format": "cardiac_deformation_lab_annotations_v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "analysis_id": analysis_id,
        "annotation_count": len(ann_list),
        "annotations": ann_list,
        "disclaimer": "Manual annotations exported for research benchmarking only."
    }


def import_annotations(package: Dict[str, Any]) -> Dict[str, Any]:
    """Import an exported annotation JSON package."""
    if not isinstance(package, dict) or "annotations" not in package:
        raise ValueError("Invalid annotation package: missing 'annotations' array.")

    imported = []
    skipped = []

    for ann in package.get("annotations", []):
        qc = validate_annotation_quality(ann)
        if qc["valid"]:
            try:
                # Assign fresh ID to avoid collisions
                ann_copy = ann.copy()
                ann_copy["id"] = str(uuid.uuid4())
                created = create_annotation(ann_copy)
                imported.append(created["id"])
            except Exception as e:
                skipped.append({"id": ann.get("id"), "reason": str(e)})
        else:
            skipped.append({"id": ann.get("id"), "reason": "; ".join(qc["errors"])})

    return {
        "imported_count": len(imported),
        "imported_ids": imported,
        "skipped_count": len(skipped),
        "skipped": skipped
    }
