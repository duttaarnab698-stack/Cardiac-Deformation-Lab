"""
backend/app/services/calibration.py

Spatial Calibration and Physical Units Service for Cardiac Deformation Lab.

Provides:
- Calibration model and validation (pixel_spacing_x, pixel_spacing_y, unit)
- Physical flow conversion: u_phys = u * sx, v_phys = v * sy
- Physical displacement magnitude: D_phys = sqrt(u_phys² + v_phys²)
- Physical displacement statistics calculation
- Dimensionless preservation guarantees for continuum strain metrics
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np


SUPPORTED_UNITS = ("mm", "cm")


def validate_calibration(
    pixel_spacing_x: Optional[float],
    pixel_spacing_y: Optional[float],
    unit: str = "mm"
) -> Tuple[bool, Optional[str]]:
    """
    Validate spatial calibration parameters.

    Rules:
    - If neither pixel_spacing_x nor pixel_spacing_y is provided, calibration is inactive (valid, disabled).
    - If either is provided, BOTH must be provided, positive numeric values (> 0).
    - Unit must be one of SUPPORTED_UNITS ('mm', 'cm').

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if pixel_spacing_x is None and pixel_spacing_y is None:
        return True, None

    if pixel_spacing_x is None or pixel_spacing_y is None:
        return False, "Both pixel_spacing_x and pixel_spacing_y must be provided for spatial calibration."

    try:
        sx = float(pixel_spacing_x)
        sy = float(pixel_spacing_y)
    except (ValueError, TypeError):
        return False, "pixel_spacing_x and pixel_spacing_y must be numeric values."

    if sx <= 0 or sy <= 0:
        return False, f"Pixel spacing values must be strictly positive (> 0). Got x={sx}, y={sy}."

    if not isinstance(unit, str) or unit.strip().lower() not in SUPPORTED_UNITS:
        return False, f"Unsupported spatial unit '{unit}'. Supported units are: {', '.join(SUPPORTED_UNITS)}."

    return True, None


def convert_flow_to_physical_units(
    flow: np.ndarray,
    pixel_spacing_x: float,
    pixel_spacing_y: float
) -> np.ndarray:
    """
    Convert image-space optical flow (pixels) to physical displacement components.

    u_physical = u * pixel_spacing_x
    v_physical = v * pixel_spacing_y

    Parameters
    ----------
    flow : np.ndarray
        Dense optical flow array with shape (H, W, 2).
        flow[..., 0] is horizontal displacement u in pixels.
        flow[..., 1] is vertical displacement v in pixels.
    pixel_spacing_x : float
        Physical width per pixel (e.g. mm/pixel). Must be > 0.
    pixel_spacing_y : float
        Physical height per pixel (e.g. mm/pixel). Must be > 0.

    Returns
    -------
    np.ndarray
        Physical displacement array with shape (H, W, 2).
    """
    physical_flow = np.empty_like(flow, dtype=np.float32)
    physical_flow[..., 0] = flow[..., 0] * float(pixel_spacing_x)
    physical_flow[..., 1] = flow[..., 1] * float(pixel_spacing_y)
    return physical_flow


def calculate_physical_displacement_magnitude(
    flow: np.ndarray,
    pixel_spacing_x: float,
    pixel_spacing_y: float
) -> np.ndarray:
    """
    Calculate physical displacement magnitude field:
        D_physical(x,y) = sqrt( (u * sx)² + (v * sy)² )

    Parameters
    ----------
    flow : np.ndarray
        Dense optical flow (H, W, 2) in pixels.
    pixel_spacing_x : float
        Physical distance per pixel along x.
    pixel_spacing_y : float
        Physical distance per pixel along y.

    Returns
    -------
    np.ndarray
        2D array (H, W) of physical displacement magnitudes.
    """
    u_phys = flow[..., 0] * float(pixel_spacing_x)
    v_phys = flow[..., 1] * float(pixel_spacing_y)
    return np.sqrt(u_phys ** 2 + v_phys ** 2)


def calculate_calibrated_motion_statistics(
    flow: np.ndarray,
    pixel_spacing_x: Optional[float] = None,
    pixel_spacing_y: Optional[float] = None,
    unit: str = "mm"
) -> Dict[str, Any]:
    """
    Calculate displacement statistics in both pixel-space and physical-space
    (when valid calibration parameters are supplied).

    Returns
    -------
    dict
        {
            "pixel_space": {
                "mean_displacement": float,
                "max_displacement": float,
                "min_displacement": float,
                "std_displacement": float,
                "unit": "px"
            },
            "physical_space": { ... } or None,
            "mean_displacement": float, # backward-compatible pixel value
            "max_displacement": float,  # backward-compatible pixel value
            "min_displacement": float,  # backward-compatible pixel value
            "std_displacement": float   # backward-compatible pixel value
        }
    """
    u = flow[..., 0]
    v = flow[..., 1]
    pixel_mag = np.sqrt(u ** 2 + v ** 2)

    pixel_stats = {
        "mean_displacement": float(np.mean(pixel_mag)),
        "max_displacement": float(np.max(pixel_mag)),
        "min_displacement": float(np.min(pixel_mag)),
        "std_displacement": float(np.std(pixel_mag)),
        "unit": "px",
    }

    physical_stats = None
    if pixel_spacing_x is not None and pixel_spacing_y is not None:
        sx = float(pixel_spacing_x)
        sy = float(pixel_spacing_y)
        u_phys = u * sx
        v_phys = v * sy
        phys_mag = np.sqrt(u_phys ** 2 + v_phys ** 2)
        clean_unit = unit.strip().lower() if isinstance(unit, str) else "mm"

        physical_stats = {
            "mean_displacement": float(np.mean(phys_mag)),
            "max_displacement": float(np.max(phys_mag)),
            "min_displacement": float(np.min(phys_mag)),
            "std_displacement": float(np.std(phys_mag)),
            "unit": clean_unit,
        }

    res: Dict[str, Any] = {
        # Backward-compatible direct keys
        "mean_displacement": pixel_stats["mean_displacement"],
        "max_displacement": pixel_stats["max_displacement"],
        "min_displacement": pixel_stats["min_displacement"],
        "std_displacement": pixel_stats["std_displacement"],
        # Categorized spaces
        "pixel_space": pixel_stats,
        "physical_space": physical_stats,
    }

    return res

