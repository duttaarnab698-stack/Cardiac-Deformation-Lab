"""
backend/app/services/roi_visualization.py

ROI Visualization and Overlay Service for Cardiac Deformation Lab.

Generates:
- Clear boundary line and tinted semi-transparent overlay of the user-defined ROI
  superimposed directly onto the reference image.
- Masked visualization versions where values outside the ROI are gently dimmed.
- Saves result to outputs/roi_overlay_<stem>.jpg.
"""

from pathlib import Path
import cv2
import numpy as np


def create_roi_overlay(
    image: np.ndarray,
    mask: np.ndarray,
    output_path: str,
    roi_type: str = "roi",
    color: tuple = (0, 255, 255), # Yellow in BGR
    alpha: float = 0.25
) -> str:
    """
    Generate an image displaying the reference frame with the ROI boundary
    and a subtle semi-transparent tinted overlay.

    Parameters
    ----------
    image : np.ndarray
        Original image (grayscale or BGR).
    mask : np.ndarray (bool)
        Binary 2D boolean mask where True indicates pixels inside the ROI.
    output_path : str
        Target destination file path.
    roi_type : str
        Geometric label ("rectangle", "ellipse", "polygon").
    color : tuple
        Overlay border and tint color (B, G, R). Default: Yellow (0, 255, 255).
    alpha : float
        Transparency of the filled region tint (0.0 to 1.0).

    Returns
    -------
    str : Path of saved ROI overlay image.
    """
    # Ensure 3-channel BGR visualization
    if len(image.shape) == 2:
        vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        vis = image.copy()

    h, w = vis.shape[:2]
    uint8_mask = (mask.astype(np.uint8)) * 255

    # 1. Semi-transparent tint inside ROI
    tinted = vis.copy()
    tinted[mask] = (
        (1.0 - alpha) * vis[mask] + alpha * np.array(color, dtype=np.float32)
    ).astype(np.uint8)

    # 2. Draw crisp boundary line using findContours
    contours, _ = cv2.findContours(
        uint8_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(tinted, contours, -1, color, 2, cv2.LINE_AA)

    # 3. Add small technical watermark tag
    label_text = f"USER ROI ({roi_type.upper()})"
    cv2.putText(
        tinted,
        label_text,
        (16, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 0),
        3,
        cv2.LINE_AA
    )
    cv2.putText(
        tinted,
        label_text,
        (16, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 255),
        1,
        cv2.LINE_AA
    )

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_file), tinted)

    return str(out_file)

