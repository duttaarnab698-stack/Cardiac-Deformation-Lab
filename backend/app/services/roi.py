"""
backend/app/services/roi.py

Region of Interest (ROI) Service for Cardiac Deformation Lab.

Provides:
- Representation of rectangular, elliptical, and polygonal user-defined ROIs as boolean masks.
- Strict validation ensuring coordinates lie within valid image dimensions and contain non-zero pixels.
- Calculation of masked deformation metrics (displacement, strain tensors, principal strains,
  advanced descriptors, and radial/circumferential deformation) without altering the underlying mathematics.
- Explicit non-diagnostic research prototype constraints: ROIs represent user-selected geometric regions,
  NOT validated anatomical segmentation.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import cv2


SUPPORTED_ROI_TYPES = ("rectangle", "ellipse", "polygon")


def create_rectangular_mask(
    height: int,
    width: int,
    x: float,
    y: float,
    w: float,
    h: float
) -> np.ndarray:
    """
    Create a boolean 2D mask for a rectangular ROI.

    Parameters
    ----------
    height, width : int
        Dimensions of the reference image.
    x, y : float
        Top-left coordinate of the rectangle.
    w, h : float
        Width and height of the rectangle.

    Returns
    -------
    np.ndarray (dtype=bool) of shape (height, width)
    """
    mask = np.zeros((height, width), dtype=np.uint8)

    # Normalize coordinates to handle potential negative width/height from dragging
    x0 = int(round(min(x, x + w)))
    y0 = int(round(min(y, y + h)))
    x1 = int(round(max(x, x + w)))
    y1 = int(round(max(y, y + h)))

    # Clip to image boundaries
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(0, min(width, x1))
    y1 = max(0, min(height, y1))

    if x1 > x0 and y1 > y0:
        mask[y0:y1, x0:x1] = 1

    return mask.astype(bool)


def create_elliptical_mask(
    height: int,
    width: int,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    angle_degrees: float = 0.0
) -> np.ndarray:
    """
    Create a boolean 2D mask for an elliptical ROI.

    Parameters
    ----------
    height, width : int
        Image dimensions.
    center_x, center_y : float
        Center coordinates of the ellipse.
    radius_x, radius_y : float
        Half-axes lengths (semi-major / semi-minor).
    angle_degrees : float, optional
        Rotation angle in degrees. Default is 0.0.

    Returns
    -------
    np.ndarray (dtype=bool) of shape (height, width)
    """
    mask = np.zeros((height, width), dtype=np.uint8)

    cx = int(round(center_x))
    cy = int(round(center_y))
    rx = max(1, int(round(abs(radius_x))))
    ry = max(1, int(round(abs(radius_y))))

    cv2.ellipse(
        mask,
        (cx, cy),
        (rx, ry),
        float(angle_degrees),
        0.0,
        360.0,
        1,
        -1 # filled
    )

    return mask.astype(bool)


def create_polygon_mask(
    height: int,
    width: int,
    points: List[Union[List[float], Tuple[float, float], Dict[str, float]]]
) -> np.ndarray:
    """
    Create a boolean 2D mask for an arbitrary polygon ROI.

    Parameters
    ----------
    height, width : int
        Image dimensions.
    points : list of (x, y) coordinates. Must contain at least 3 points.

    Returns
    -------
    np.ndarray (dtype=bool) of shape (height, width)
    """
    mask = np.zeros((height, width), dtype=np.uint8)

    parsed_points = []
    for pt in points:
        if isinstance(pt, dict):
            px = float(pt.get("x", 0.0))
            py = float(pt.get("y", 0.0))
        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
            px = float(pt[0])
            py = float(pt[1])
        else:
            continue
        parsed_points.append([int(round(px)), int(round(py))])

    if len(parsed_points) < 3:
        return mask.astype(bool)

    pts_arr = np.array([parsed_points], dtype=np.int32)
    cv2.fillPoly(mask, pts_arr, 1)

    return mask.astype(bool)


def validate_and_create_roi_mask(
    roi_config: Optional[Dict[str, Any]],
    height: int,
    width: int
) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
    """
    Validate ROI configuration and generate matching binary boolean mask.

    Parameters
    ----------
    roi_config : dict, optional
        {
            "enabled": bool,
            "type": "rectangle" | "ellipse" | "polygon",
            "coordinates": dict | list
        }
    height, width : int
        Reference image height and width.

    Returns
    -------
    (is_valid: bool, error_message: Optional[str], mask: Optional[np.ndarray])
    """
    if not roi_config or not roi_config.get("enabled"):
        return True, None, None

    roi_type = roi_config.get("type", "").strip().lower()
    if roi_type not in SUPPORTED_ROI_TYPES:
        return False, f"Unsupported ROI type '{roi_type}'. Supported: {', '.join(SUPPORTED_ROI_TYPES)}.", None

    coords = roi_config.get("coordinates")
    if coords is None:
        return False, "ROI coordinates must be provided when ROI is enabled.", None

    mask = None

    if roi_type == "rectangle":
        # Expecting { x, y, width, height } or [x, y, w, h]
        if isinstance(coords, dict):
            x = float(coords.get("x", 0))
            y = float(coords.get("y", 0))
            w = float(coords.get("width", 0))
            h = float(coords.get("height", 0))
        elif isinstance(coords, (list, tuple)) and len(coords) >= 4:
            x, y, w, h = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
        else:
            return False, "Rectangle ROI requires coordinates: x, y, width, height.", None

        if w <= 0 or h <= 0:
            return False, "Rectangle ROI width and height must be strictly positive.", None

        # Check bounds
        if x >= width or y >= height or (x + w) <= 0 or (y + h) <= 0:
            return False, "Rectangle ROI is completely outside image boundaries.", None

        mask = create_rectangular_mask(height, width, x, y, w, h)

    elif roi_type == "ellipse":
        # Expecting { center_x, center_y, radius_x, radius_y, (angle) } or [cx, cy, rx, ry, (angle)]
        if isinstance(coords, dict):
            cx = float(coords.get("center_x", coords.get("cx", 0)))
            cy = float(coords.get("center_y", coords.get("cy", 0)))
            rx = float(coords.get("radius_x", coords.get("rx", 0)))
            ry = float(coords.get("radius_y", coords.get("ry", 0)))
            angle = float(coords.get("angle", coords.get("angle_degrees", 0.0)))
        elif isinstance(coords, (list, tuple)) and len(coords) >= 4:
            cx, cy, rx, ry = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
            angle = float(coords[4]) if len(coords) > 4 else 0.0
        else:
            return False, "Ellipse ROI requires center_x, center_y, radius_x, radius_y.", None

        if rx <= 0 or ry <= 0:
            return False, "Ellipse ROI radius_x and radius_y must be strictly positive.", None

        if cx + rx <= 0 or cx - rx >= width or cy + ry <= 0 or cy - ry >= height:
            return False, "Ellipse ROI is completely outside image boundaries.", None

        mask = create_elliptical_mask(height, width, cx, cy, rx, ry, angle)

    elif roi_type == "polygon":
        points = coords.get("points") if isinstance(coords, dict) else coords
        if not isinstance(points, (list, tuple)) or len(points) < 3:
            return False, "Polygon ROI requires at least 3 coordinate points.", None

        # Check if at least one point is inside the image bounds
        any_inside = False
        for pt in points:
            px = float(pt.get("x", 0)) if isinstance(pt, dict) else float(pt[0])
            py = float(pt.get("y", 0)) if isinstance(pt, dict) else float(pt[1])
            if 0 <= px < width and 0 <= py < height:
                any_inside = True
                break

        if not any_inside:
            return False, "Polygon ROI does not contain points inside the image bounds.", None

        mask = create_polygon_mask(height, width, points)

    pixel_count = int(np.count_nonzero(mask))
    if pixel_count == 0:
        return False, "ROI mask contains 0 active pixels after clipping to image bounds.", None

    return True, None, mask


def calculate_masked_displacement_statistics(
    flow: np.ndarray,
    mask: np.ndarray,
    pixel_spacing_x: Optional[float] = None,
    pixel_spacing_y: Optional[float] = None,
    unit: str = "mm"
) -> Dict[str, Any]:
    """
    Calculate displacement statistics restricted to the ROI mask.
    """
    u = flow[..., 0]
    v = flow[..., 1]
    pixel_mag = np.sqrt(u ** 2 + v ** 2)

    masked_px = pixel_mag[mask]
    if len(masked_px) == 0:
        return {
            "mean_displacement": 0.0,
            "max_displacement": 0.0,
            "min_displacement": 0.0,
            "std_displacement": 0.0,
            "pixel_space": {
                "mean_displacement": 0.0,
                "max_displacement": 0.0,
                "min_displacement": 0.0,
                "std_displacement": 0.0,
                "unit": "px"
            },
            "physical_space": None,
            "pixel_count": 0
        }

    pixel_stats = {
        "mean_displacement": float(np.mean(masked_px)),
        "max_displacement": float(np.max(masked_px)),
        "min_displacement": float(np.min(masked_px)),
        "std_displacement": float(np.std(masked_px)),
        "unit": "px"
    }

    physical_stats = None
    if pixel_spacing_x is not None and pixel_spacing_y is not None:
        sx = float(pixel_spacing_x)
        sy = float(pixel_spacing_y)
        u_phys = u * sx
        v_phys = v * sy
        phys_mag = np.sqrt(u_phys ** 2 + v_phys ** 2)
        masked_phys = phys_mag[mask]
        clean_unit = unit.strip().lower() if isinstance(unit, str) else "mm"
        physical_stats = {
            "mean_displacement": float(np.mean(masked_phys)),
            "max_displacement": float(np.max(masked_phys)),
            "min_displacement": float(np.min(masked_phys)),
            "std_displacement": float(np.std(masked_phys)),
            "unit": clean_unit
        }

    return {
        "mean_displacement": pixel_stats["mean_displacement"],
        "max_displacement": pixel_stats["max_displacement"],
        "min_displacement": pixel_stats["min_displacement"],
        "std_displacement": pixel_stats["std_displacement"],
        "pixel_space": pixel_stats,
        "physical_space": physical_stats,
        "pixel_count": int(len(masked_px))
    }


def calculate_masked_strain_statistics(
    exx: np.ndarray,
    eyy: np.ndarray,
    exy: np.ndarray,
    principal_1: np.ndarray,
    principal_2: np.ndarray,
    mask: np.ndarray
) -> Dict[str, Any]:
    """
    Calculate strain statistics restricted to the ROI mask.
    """
    m_exx = exx[mask]
    m_eyy = eyy[mask]
    m_exy = exy[mask]
    m_p1  = principal_1[mask]
    m_p2  = principal_2[mask]

    if len(m_p1) == 0:
        return {
            "mean_exx": 0.0, "max_exx": 0.0, "min_exx": 0.0, "std_exx": 0.0,
            "mean_eyy": 0.0, "max_eyy": 0.0, "min_eyy": 0.0, "std_eyy": 0.0,
            "mean_exy": 0.0, "max_exy": 0.0, "min_exy": 0.0, "std_exy": 0.0,
            "principal_strain_1": {"mean": 0.0, "max": 0.0, "min": 0.0, "std": 0.0},
            "principal_strain_2": {"mean": 0.0, "max": 0.0, "min": 0.0, "std": 0.0},
            "mean_principal_strain_1": 0.0, "max_principal_strain_1": 0.0,
            "mean_principal_strain_2": 0.0, "max_principal_strain_2": 0.0
        }

    p1_stats = {
        "mean": float(np.mean(m_p1)),
        "max":  float(np.max(m_p1)),
        "min":  float(np.min(m_p1)),
        "std":  float(np.std(m_p1)),
    }

    p2_stats = {
        "mean": float(np.mean(m_p2)),
        "max":  float(np.max(m_p2)),
        "min":  float(np.min(m_p2)),
        "std":  float(np.std(m_p2)),
    }

    return {
        "mean_exx": float(np.mean(m_exx)),
        "max_exx":  float(np.max(m_exx)),
        "min_exx":  float(np.min(m_exx)),
        "std_exx":  float(np.std(m_exx)),

        "mean_eyy": float(np.mean(m_eyy)),
        "max_eyy":  float(np.max(m_eyy)),
        "min_eyy":  float(np.min(m_eyy)),
        "std_eyy":  float(np.std(m_eyy)),

        "mean_exy": float(np.mean(m_exy)),
        "max_exy":  float(np.max(m_exy)),
        "min_exy":  float(np.min(m_exy)),
        "std_exy":  float(np.std(m_exy)),

        "principal_strain_1": p1_stats,
        "principal_strain_2": p2_stats,

        "mean_principal_strain_1": p1_stats["mean"],
        "max_principal_strain_1":  p1_stats["max"],
        "min_principal_strain_1":  p1_stats["min"],

        "mean_principal_strain_2": p2_stats["mean"],
        "max_principal_strain_2":  p2_stats["max"],
        "min_principal_strain_2":  p2_stats["min"],
    }


def calculate_masked_advanced_metrics(
    coherence_map: np.ndarray,
    gradient_map: np.ndarray,
    anisotropy_map: np.ndarray,
    energy_map: np.ndarray,
    principal_strain_1: np.ndarray,
    mask: np.ndarray
) -> Dict[str, Any]:
    """
    Calculate advanced biomechanical descriptors restricted to the ROI mask.
    """
    m_coh = coherence_map[mask]
    m_grad = gradient_map[mask]
    m_ani = anisotropy_map[mask]
    m_en = energy_map[mask]
    m_p1 = principal_strain_1[mask]

    if len(m_p1) == 0:
        return {
            "motion_coherence": {"mean": 0.0, "min": 0.0, "max": 0.0},
            "strain_gradient": {"mean": 0.0, "max": 0.0},
            "anisotropy": {"mean": 0.0, "max": 0.0},
            "entropy": 0.0,
            "deformation_energy": {"mean": 0.0, "max": 0.0}
        }

    # Shannon entropy over the masked values
    abs_p1 = np.abs(m_p1)
    p_sum = np.sum(abs_p1)
    if p_sum > 0:
        prob = abs_p1 / p_sum
        prob = prob[prob > 0]
        entropy_val = float(-np.sum(prob * np.log(prob)))
    else:
        entropy_val = 0.0

    return {
        "motion_coherence": {
            "mean": float(np.mean(m_coh)),
            "min":  float(np.min(m_coh)),
            "max":  float(np.max(m_coh))
        },
        "strain_gradient": {
            "mean": float(np.mean(m_grad)),
            "max":  float(np.max(m_grad))
        },
        "anisotropy": {
            "mean": float(np.mean(m_ani)),
            "max":  float(np.max(m_ani))
        },
        "entropy": entropy_val,
        "deformation_energy": {
            "mean": float(np.mean(m_en)),
            "max":  float(np.max(m_en))
        }
    }


def calculate_masked_cardiac_deformation(
    radial_map: np.ndarray,
    circumferential_map: np.ndarray,
    mask: np.ndarray
) -> Dict[str, Any]:
    """
    Calculate radial and circumferential deformation restricted to the ROI mask.
    """
    m_rad = radial_map[mask]
    m_circ = circumferential_map[mask]

    if len(m_rad) == 0:
        return {
            "radial": {"mean": 0.0, "max": 0.0, "min": 0.0},
            "circumferential": {"mean": 0.0, "max": 0.0, "min": 0.0}
        }

    return {
        "radial": {
            "mean": float(np.mean(m_rad)),
            "max":  float(np.max(m_rad)),
            "min":  float(np.min(m_rad))
        },
        "circumferential": {
            "mean": float(np.mean(m_circ)),
            "max":  float(np.max(m_circ)),
            "min":  float(np.min(m_circ))
        }
    }

