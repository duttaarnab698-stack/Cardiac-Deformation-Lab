"""
backend/app/services/roi_tracking.py

Automatic Region of Interest (ROI) Tracking Service for Cardiac Deformation Lab.

Provides:
- Rigid translation of user-defined ROIs (rectangle, ellipse, polygon) across cine frames.
- Robust optical flow motion estimation using median ROI displacement and outlier filtering.
- Tracking confidence scoring (0.0 to 1.0) evaluating image-motion vector consistency.
- Boundary validation and safe clamping ensuring ROIs remain within image dimensions.
- Graceful failure handling without crashing temporal analysis.
- Clear non-diagnostic research prototype constraints: Tracking reflects image-space optical flow,
  NOT validated anatomical tissue tracking. Shape deformation is not modeled.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import cv2

from app.services.motion import calculate_optical_flow
from app.services.roi import (
    create_rectangular_mask,
    create_elliptical_mask,
    create_polygon_mask,
    validate_and_create_roi_mask,
)


def extract_roi_center(roi_type: str, coords: Any) -> Tuple[float, float]:
    """Calculate the geometric center (cx, cy) of the ROI coordinates."""
    if roi_type == "rectangle":
        if isinstance(coords, dict):
            x = float(coords.get("x", 0))
            y = float(coords.get("y", 0))
            w = float(coords.get("width", 0))
            h = float(coords.get("height", 0))
        elif isinstance(coords, (list, tuple)) and len(coords) >= 4:
            x, y, w, h = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
        else:
            return 0.0, 0.0
        return x + w / 2.0, y + h / 2.0

    elif roi_type == "ellipse":
        if isinstance(coords, dict):
            cx = float(coords.get("center_x", coords.get("cx", 0)))
            cy = float(coords.get("center_y", coords.get("cy", 0)))
        elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
            cx, cy = float(coords[0]), float(coords[1])
        else:
            return 0.0, 0.0
        return cx, cy

    elif roi_type == "polygon":
        points = coords.get("points") if isinstance(coords, dict) else coords
        if not isinstance(points, (list, tuple)) or len(points) == 0:
            return 0.0, 0.0
        xs = [float(p.get("x", 0)) if isinstance(p, dict) else float(p[0]) for p in points]
        ys = [float(p.get("y", 0)) if isinstance(p, dict) else float(p[1]) for p in points]
        return float(np.mean(xs)), float(np.mean(ys))

    return 0.0, 0.0


def translate_roi_coordinates(
    roi_type: str,
    coords: Any,
    dx: float,
    dy: float,
    height: int,
    width: int
) -> Tuple[Any, Tuple[float, float], bool]:
    """
    Apply rigid 2D translation (dx, dy) to ROI coordinates and safely clamp/clip to image boundaries.

    Returns:
    --------
    (new_coords, (center_x, center_y), is_valid)
    """
    if roi_type == "rectangle":
        if isinstance(coords, dict):
            x = float(coords.get("x", 0)) + dx
            y = float(coords.get("y", 0)) + dy
            w = float(coords.get("width", 0))
            h = float(coords.get("height", 0))
        else:
            x = float(coords[0]) + dx
            y = float(coords[1]) + dy
            w = float(coords[2])
            h = float(coords[3])

        # Clamp safely within image bounds
        x = max(0.0, min(float(width - w), x))
        y = max(0.0, min(float(height - h), y))

        new_coords = {
            "x": round(x, 2),
            "y": round(y, 2),
            "width": round(w, 2),
            "height": round(h, 2),
        }
        cx = x + w / 2.0
        cy = y + h / 2.0
        is_valid = (w > 2 and h > 2 and x < width and y < height)
        return new_coords, (cx, cy), is_valid

    elif roi_type == "ellipse":
        if isinstance(coords, dict):
            cx = float(coords.get("center_x", coords.get("cx", 0))) + dx
            cy = float(coords.get("center_y", coords.get("cy", 0))) + dy
            rx = float(coords.get("radius_x", coords.get("rx", 0)))
            ry = float(coords.get("radius_y", coords.get("ry", 0)))
            angle = float(coords.get("angle", coords.get("angle_degrees", 0.0)))
        else:
            cx = float(coords[0]) + dx
            cy = float(coords[1]) + dy
            rx = float(coords[2])
            ry = float(coords[3])
            angle = float(coords[4]) if len(coords) > 4 else 0.0

        # Clamp center so ellipse remains within image frame
        cx = max(rx, min(float(width - rx), cx))
        cy = max(ry, min(float(height - ry), cy))

        new_coords = {
            "center_x": round(cx, 2),
            "center_y": round(cy, 2),
            "radius_x": round(rx, 2),
            "radius_y": round(ry, 2),
            "angle": round(angle, 2),
        }
        is_valid = (rx > 2 and ry > 2 and 0 <= cx < width and 0 <= cy < height)
        return new_coords, (cx, cy), is_valid

    elif roi_type == "polygon":
        points = coords.get("points") if isinstance(coords, dict) else coords
        new_points = []
        for p in points:
            px = (float(p.get("x", 0)) if isinstance(p, dict) else float(p[0])) + dx
            py = (float(p.get("y", 0)) if isinstance(p, dict) else float(p[1])) + dy
            # Clamp vertex to valid image pixel coordinates
            px = max(0.0, min(float(width - 1), px))
            py = max(0.0, min(float(height - 1), py))
            new_points.append({"x": round(px, 2), "y": round(py, 2)})

        xs = [p["x"] for p in new_points]
        ys = [p["y"] for p in new_points]
        cx = float(np.mean(xs)) if xs else 0.0
        cy = float(np.mean(ys)) if ys else 0.0

        new_coords = {"points": new_points}
        is_valid = len(new_points) >= 3 and (max(xs) - min(xs) > 2) and (max(ys) - min(ys) > 2)
        return new_coords, (cx, cy), is_valid

    return coords, (0.0, 0.0), False


def estimate_roi_motion(
    flow: np.ndarray,
    mask: np.ndarray,
    initial_pixel_count: int
) -> Tuple[float, float, float, str, Dict[str, Any]]:
    """
    Robustly estimate ROI displacement between consecutive frames using median flow and outlier rejection.

    Returns:
    --------
    (median_dx, median_dy, tracking_confidence, status, stats_dict)
    """
    if mask is None or np.count_nonzero(mask) == 0:
        return 0.0, 0.0, 0.0, "failed", {
            "mean_dx": 0.0, "mean_dy": 0.0, "median_dx": 0.0, "median_dy": 0.0,
            "std_dx": 0.0, "std_dy": 0.0, "valid_pixels": 0
        }

    # Extract flow vectors inside the active ROI mask
    u_roi = flow[..., 0][mask]
    v_roi = flow[..., 1][mask]
    n_pts = len(u_roi)

    if n_pts < 10:
        return 0.0, 0.0, 0.0, "failed", {
            "mean_dx": 0.0, "mean_dy": 0.0, "median_dx": 0.0, "median_dy": 0.0,
            "std_dx": 0.0, "std_dy": 0.0, "valid_pixels": int(n_pts)
        }

    # Outlier rejection using IQR filtering on flow magnitude
    mags = np.sqrt(u_roi**2 + v_roi**2)
    q25, q75 = np.percentile(mags, [25, 75])
    iqr = q75 - q25
    cutoff = q75 + 2.5 * max(iqr, 0.5)

    valid_mask = mags <= cutoff
    if np.count_nonzero(valid_mask) >= 5:
        u_valid = u_roi[valid_mask]
        v_valid = v_roi[valid_mask]
    else:
        u_valid = u_roi
        v_valid = v_roi

    # Robust statistics
    med_dx = float(np.median(u_valid))
    med_dy = float(np.median(v_valid))
    mean_dx = float(np.mean(u_valid))
    mean_dy = float(np.mean(v_valid))
    std_dx = float(np.std(u_valid))
    std_dy = float(np.std(v_valid))
    disp_std = float(np.sqrt(std_dx**2 + std_dy**2))
    disp_med = float(np.sqrt(med_dx**2 + med_dy**2))

    # Calculate Tracking Confidence Score (0.0 to 1.0)
    # Factor 1: Outlier retention ratio
    f_outlier = float(len(u_valid) / max(1, n_pts))
    # Factor 2: Vector directional coherence (ratio of standard deviation to displacement magnitude)
    f_coherence = float(1.0 / (1.0 + disp_std / max(0.5, disp_med)))
    # Factor 3: Relative mask coverage vs initial frame
    f_area = float(min(1.0, n_pts / max(1, initial_pixel_count)))

    confidence = round(float(0.40 * f_coherence + 0.35 * f_outlier + 0.25 * f_area), 4)
    confidence = max(0.0, min(1.0, confidence))

    if confidence >= 0.55:
        status = "valid"
    elif confidence >= 0.30:
        status = "unreliable"
    else:
        status = "failed"

    stats_dict = {
        "mean_dx": round(mean_dx, 4),
        "mean_dy": round(mean_dy, 4),
        "median_dx": round(med_dx, 4),
        "median_dy": round(med_dy, 4),
        "std_dx": round(std_dx, 4),
        "std_dy": round(std_dy, 4),
        "valid_pixels": int(len(u_valid)),
    }

    return med_dx, med_dy, confidence, status, stats_dict


def track_roi_across_frames(
    frames: List[np.ndarray],
    initial_roi: Dict[str, Any],
    method: str = "optical_flow"
) -> Dict[str, Any]:
    """
    Track a user-defined ROI across consecutive image frames via dense optical flow translation.

    Parameters
    ----------
    frames : list of np.ndarray
        List of image arrays representing consecutive cardiac frames.
    initial_roi : dict
        {
            "enabled": True,
            "type": "rectangle" | "ellipse" | "polygon",
            "coordinates": {...}
        }
    method : str
        Tracking estimation method (default: "optical_flow").

    Returns
    -------
    dict with keys:
        "masks": List of 2D boolean masks for each frame.
        "tracking_path": List of frame tracking records with coordinates, center, dx, dy, confidence.
        "tracking_summary": Compact metrics (frame_count, successful_frames, mean_confidence, etc.).
        "warning": Optional warning message if tracking stopped or degraded.
    """
    if len(frames) == 0:
        raise ValueError("Cannot track ROI on empty frame sequence.")

    first_frame = frames[0]
    h, w = first_frame.shape[:2]

    # Validate initial ROI
    is_valid, err, init_mask = validate_and_create_roi_mask(initial_roi, h, w)
    if not is_valid or init_mask is None:
        raise ValueError(f"Invalid initial ROI configuration: {err}")

    roi_type = initial_roi.get("type", "rectangle").strip().lower()
    current_coords = initial_roi.get("coordinates")
    initial_pixel_count = int(np.count_nonzero(init_mask))
    init_cx, init_cy = extract_roi_center(roi_type, current_coords)

    masks: List[np.ndarray] = [init_mask]
    tracking_path: List[Dict[str, Any]] = [
        {
            "frame_index": 0,
            "roi": {
                "type": roi_type,
                "coordinates": current_coords,
                "center": {"x": round(init_cx, 2), "y": round(init_cy, 2)},
                "pixel_count": initial_pixel_count,
            },
            "tracking_confidence": 1.0,
            "status": "valid",
            "displacement": {"dx": 0.0, "dy": 0.0, "magnitude": 0.0},
            "motion_stats": {
                "mean_dx": 0.0, "mean_dy": 0.0, "median_dx": 0.0, "median_dy": 0.0,
                "std_dx": 0.0, "std_dy": 0.0, "valid_pixels": initial_pixel_count
            }
        }
    ]

    current_mask = init_mask
    consecutive_failures = 0
    warning_msg = None

    for i in range(len(frames) - 1):
        frame_a = frames[i]
        frame_b = frames[i + 1]

        if consecutive_failures >= 3:
            # Halted tracking: preserve last known mask
            masks.append(current_mask)
            cx, cy = extract_roi_center(roi_type, current_coords)
            tracking_path.append({
                "frame_index": i + 1,
                "roi": {
                    "type": roi_type,
                    "coordinates": current_coords,
                    "center": {"x": round(cx, 2), "y": round(cy, 2)},
                    "pixel_count": int(np.count_nonzero(current_mask)),
                },
                "tracking_confidence": 0.0,
                "status": "failed",
                "displacement": {"dx": 0.0, "dy": 0.0, "magnitude": 0.0},
                "motion_stats": {
                    "mean_dx": 0.0, "mean_dy": 0.0, "median_dx": 0.0, "median_dy": 0.0,
                    "std_dx": 0.0, "std_dy": 0.0, "valid_pixels": 0
                }
            })
            continue

        # 1. Optical flow between current pair
        flow = calculate_optical_flow(frame_a, frame_b)

        # 2. Robust motion estimation inside current ROI
        dx, dy, conf, status, stats = estimate_roi_motion(flow, current_mask, initial_pixel_count)

        if status == "failed":
            consecutive_failures += 1
            if consecutive_failures >= 3 and warning_msg is None:
                warning_msg = (
                    f"ROI tracking halted at frame {i + 1} after 3 consecutive low-confidence steps. "
                    "Retaining last known position for remaining frames."
                )
            masks.append(current_mask)
            cx, cy = extract_roi_center(roi_type, current_coords)
            tracking_path.append({
                "frame_index": i + 1,
                "roi": {
                    "type": roi_type,
                    "coordinates": current_coords,
                    "center": {"x": round(cx, 2), "y": round(cy, 2)},
                    "pixel_count": int(np.count_nonzero(current_mask)),
                },
                "tracking_confidence": conf,
                "status": "failed",
                "displacement": {"dx": 0.0, "dy": 0.0, "magnitude": 0.0},
                "motion_stats": stats,
            })
            continue

        consecutive_failures = 0

        # 3. Translate ROI coordinates
        new_coords, (cx, cy), is_valid = translate_roi_coordinates(
            roi_type=roi_type,
            coords=current_coords,
            dx=dx,
            dy=dy,
            height=h,
            width=w
        )

        # 4. Generate new mask
        is_mask_valid, _, new_mask = validate_and_create_roi_mask(
            {"enabled": True, "type": roi_type, "coordinates": new_coords},
            h, w
        )

        if not is_valid or not is_mask_valid or new_mask is None or np.count_nonzero(new_mask) == 0:
            status = "failed"
            conf = 0.0
            new_mask = current_mask

        current_coords = new_coords
        current_mask = new_mask
        masks.append(current_mask)

        mag = float(np.sqrt(dx**2 + dy**2))
        tracking_path.append({
            "frame_index": i + 1,
            "roi": {
                "type": roi_type,
                "coordinates": current_coords,
                "center": {"x": round(cx, 2), "y": round(cy, 2)},
                "pixel_count": int(np.count_nonzero(current_mask)),
            },
            "tracking_confidence": conf,
            "status": status,
            "displacement": {"dx": round(dx, 4), "dy": round(dy, 4), "magnitude": round(mag, 4)},
            "motion_stats": stats,
        })

    # Summary metrics
    confidences = [item["tracking_confidence"] for item in tracking_path]
    valid_frames = sum(1 for item in tracking_path if item["status"] in ("valid", "unreliable"))
    failed_frames = sum(1 for item in tracking_path if item["status"] == "failed")

    tracking_summary = {
        "frame_count": len(frames),
        "successful_tracking_frames": valid_frames,
        "failed_tracking_frames": failed_frames,
        "mean_confidence": round(float(np.mean(confidences)), 4),
        "min_confidence": round(float(np.min(confidences)), 4),
        "max_confidence": round(float(np.max(confidences)), 4),
        "tracking_mode": "tracked",
    }

    return {
        "masks": masks,
        "tracking_path": tracking_path,
        "tracking_summary": tracking_summary,
        "warning": warning_msg,
    }
