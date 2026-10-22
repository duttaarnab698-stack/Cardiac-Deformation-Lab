"""
backend/app/services/roi_tracking_visualization.py

ROI Tracking Visualization Service for Cardiac Deformation Lab.

Generates:
- High-contrast visual overlays displaying tracked ROI boundaries and semi-transparent tint
  on key sequence frames (first, middle, last).
- Watermark badge detailing frame number, tracking confidence, and status.
- Saves keyframe images to outputs/tracked_roi_frame_{idx:06d}.jpg.
"""

from pathlib import Path
from typing import Any, Dict, List
import cv2
import numpy as np


def render_tracked_roi_frame(
    image: np.ndarray,
    mask: np.ndarray,
    frame_index: int,
    total_frames: int,
    confidence: float,
    status: str,
    roi_type: str,
    output_path: str
) -> str:
    """
    Render and save a single frame overlay with the tracked ROI contour,
    confidence score, and technical metadata.
    """
    if len(image.shape) == 2:
        vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        vis = image.copy()

    h, w = vis.shape[:2]
    uint8_mask = (mask.astype(np.uint8)) * 255

    # Color coding based on status and confidence:
    # High confidence (green/teal), Medium/unreliable (yellow/amber), Failed (red)
    if status == "failed":
        color = (0, 0, 230) # Red in BGR
    elif confidence >= 0.60:
        color = (80, 215, 60) # Green in BGR
    else:
        color = (0, 190, 255) # Amber/Yellow in BGR

    # 1. Semi-transparent tint inside ROI
    alpha = 0.25
    tinted = vis.copy()
    tinted[mask] = (
        (1.0 - alpha) * vis[mask] + alpha * np.array(color, dtype=np.float32)
    ).astype(np.uint8)

    # 2. Draw crisp boundary contour
    contours, _ = cv2.findContours(
        uint8_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(tinted, contours, -1, color, 2, cv2.LINE_AA)

    # 3. Text Overlay Badge
    badge_text = f"Frame {frame_index + 1}/{total_frames} | Conf: {confidence:.2f} ({status.upper()})"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.40, min(0.65, w / 700.0))
    thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(badge_text, font, font_scale, thickness)

    pad = 6
    bx = 10
    by = 10
    cv2.rectangle(
        tinted,
        (bx, by),
        (bx + text_w + 2 * pad, by + text_h + 2 * pad + baseline),
        (15, 23, 42), # Dark Slate background
        -1
    )
    cv2.rectangle(
        tinted,
        (bx, by),
        (bx + text_w + 2 * pad, by + text_h + 2 * pad + baseline),
        color,
        1
    )
    cv2.putText(
        tinted,
        badge_text,
        (bx + pad, by + text_h + pad),
        font,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA
    )

    # Secondary subtitle badge
    sub_text = f"Tracked ROI ({roi_type.capitalize()})"
    cv2.putText(
        tinted,
        sub_text,
        (bx + pad, by + text_h + 2 * pad + baseline + 14),
        font,
        max(0.35, font_scale * 0.8),
        color,
        1,
        cv2.LINE_AA
    )

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_p), tinted)

    return str(out_p)


def generate_tracking_visualizations(
    frames: List[np.ndarray],
    tracking_path: List[Dict[str, Any]],
    masks: List[np.ndarray],
    output_dir: Path,
    stem_prefix: str = "tracked_roi"
) -> Dict[str, Dict[str, Any]]:
    """
    Generate visualizations for first, middle, and last sequence frames.

    Returns:
    --------
    dict mapping "first", "middle", "last" (or frame keys) to details:
    {
        "first": { "frame_index": 0, "path": "...", "confidence": 1.0, "status": "valid" },
        ...
    }
    """
    n = len(frames)
    if n == 0 or len(tracking_path) == 0:
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine keyframe indices: first, middle, last
    indices = [0]
    if n >= 3:
        mid = n // 2
        indices.append(mid)
    if n >= 2:
        indices.append(n - 1)

    # Deduplicate while preserving order
    unique_indices = []
    for idx in indices:
        if idx not in unique_indices and idx < n:
            unique_indices.append(idx)

    key_names = ["first", "middle", "last"] if len(unique_indices) == 3 else [f"frame_{i}" for i in range(len(unique_indices))]

    previews: Dict[str, Dict[str, Any]] = {}

    for pos, idx in enumerate(unique_indices):
        key = key_names[pos] if pos < len(key_names) else f"frame_{idx}"
        rec = tracking_path[idx]
        mask = masks[idx]
        conf = rec["tracking_confidence"]
        status = rec["status"]
        roi_type = rec["roi"]["type"]

        filename = f"{stem_prefix}_frame_{idx + 1:06d}.jpg"
        out_path = output_dir / filename

        render_tracked_roi_frame(
            image=frames[idx],
            mask=mask,
            frame_index=idx,
            total_frames=n,
            confidence=conf,
            status=status,
            roi_type=roi_type,
            output_path=str(out_path)
        )

        previews[key] = {
            "frame_index": idx,
            "filename": filename,
            "path": str(out_path),
            "confidence": conf,
            "status": status,
            "center": rec["roi"]["center"],
            "pixel_count": rec["roi"]["pixel_count"],
        }

    return previews
