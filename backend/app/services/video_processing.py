"""
backend/app/services/video_processing.py

Video processing and frame extraction service for Cardiac Deformation Lab.
Uses OpenCV to extract frames at deterministic intervals up to a specified
maximum limit, saving images in structured directories.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import cv2


def get_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Extract video dimensions, framerate, frame count, and duration using OpenCV.

    Parameters
    ----------
    video_path : str
        Filesystem path to the video file.

    Returns
    -------
    dict
        {
            "filename": str,
            "width": int,
            "height": int,
            "fps": float,
            "total_frames": int,
            "duration_seconds": float
        }

    Raises
    ------
    ValueError
        If the video cannot be opened or contains zero frames.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(v_path.resolve()))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {v_path.name}")

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0:
            fps = 25.0  # sensible fallback if header metadata is missing

        duration_seconds = round(total_frames / fps, 2) if total_frames > 0 else 0.0

        if width <= 0 or height <= 0 or total_frames <= 0:
            raise ValueError(f"Corrupt or empty video stream: {v_path.name}")

        return {
            "filename": v_path.name,
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "duration_seconds": duration_seconds,
        }
    finally:
        cap.release()


def extract_video_frames(
    video_path: str,
    output_directory: str,
    frame_interval: int = 1,
    max_frames: int = 100,
    format_ext: str = "jpg"
) -> List[str]:
    """
    Extract frames at requested intervals up to max_frames using OpenCV.
    Does NOT load the entire video into memory simultaneously.

    Parameters
    ----------
    video_path : str
        Path to input video file.
    output_directory : str
        Directory where extracted frame images will be written.
    frame_interval : int
        Step size between sampled frames (>= 1).
    max_frames : int
        Maximum number of extracted frame images (>= 2).
    format_ext : str
        File format extension ('jpg' or 'png').

    Returns
    -------
    list of str
        List of filenames (e.g. ['frame_000001.jpg', ...]) relative to output_directory.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if frame_interval < 1:
        raise ValueError("frame_interval must be >= 1")
    if max_frames < 2:
        raise ValueError("max_frames must be >= 2")

    out_dir = Path(output_directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(v_path.resolve()))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {v_path.name}")

    extracted_filenames: List[str] = []
    frame_idx = 0
    saved_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_idx % frame_interval == 0:
                saved_count += 1
                frame_filename = f"frame_{saved_count:06d}.{format_ext}"
                target_path = out_dir / frame_filename

                # Save frame image
                success = cv2.imwrite(str(target_path), frame)
                if success:
                    extracted_filenames.append(frame_filename)

                if saved_count >= max_frames:
                    break

            frame_idx += 1
    finally:
        cap.release()

    if not extracted_filenames:
        raise ValueError("No frames could be extracted from video.")

    return extracted_filenames

