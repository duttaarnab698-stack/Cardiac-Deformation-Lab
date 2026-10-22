"""
backend/app/api/video.py

FastAPI router for cardiac video upload, information probing, and frame extraction.
Extracts frames into backend/data/video_frames/<video_stem>/ and creates accessible
symlinks/copies for the temporal analysis pipeline.
"""

from pathlib import Path
from typing import List, Optional
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.video_processing import get_video_metadata, extract_video_frames

router = APIRouter(
    prefix="/api/video",
    tags=["Video"]
)

VIDEO_UPLOAD_DIR = Path("uploads/videos")
VIDEO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FRAMES_BASE_DIR = Path("data/video_frames")
FRAMES_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Also ensure regular uploads dir exists for temporal analysis access
GENERAL_UPLOADS_DIR = Path("uploads")
GENERAL_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm"
}


class ExtractFramesRequest(BaseModel):
    filename: str = Field(..., description="Saved filename of the uploaded video")
    frame_interval: int = Field(1, ge=1, description="Interval step between sampled frames")
    max_frames: int = Field(50, ge=2, description="Maximum number of frames to extract")


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a cardiac video in .mp4, .avi, .mov, .mkv, or .webm format.
    Saves into backend/uploads/videos/ with a unique UUID after size and format validation.
    """
    from app.core.config import MAX_VIDEO_UPLOAD_BYTES
    from app.core.security import sanitize_filename
    from app.core.logging import logger

    safe_name = sanitize_filename(file.filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
        )

    content = await file.read()
    if len(content) > MAX_VIDEO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Video exceeds maximum allowed size ({MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024)} MB)."
        )

    if len(content) < 64:
        raise HTTPException(
            status_code=400,
            detail="Video file is empty or corrupted."
        )

    unique_filename = f"{uuid.uuid4()}{ext}"
    target_path = VIDEO_UPLOAD_DIR / unique_filename

    with target_path.open("wb") as buffer:
        buffer.write(content)

    logger.info(f"Video uploaded successfully: {safe_name} -> {unique_filename} ({len(content)} bytes)")

    return {
        "message": "Video uploaded successfully",
        "filename": safe_name,
        "saved_filename": unique_filename,
        "path": str(target_path)
    }


@router.get("/info/{filename}")
def video_info(filename: str):
    """
    Retrieve video metadata (width, height, fps, total_frames, duration_seconds) using OpenCV.
    """
    safe_name = Path(filename).name  # Prevent path traversal
    video_path = VIDEO_UPLOAD_DIR / safe_name

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file '{safe_name}' not found."
        )

    try:
        info = get_video_metadata(str(video_path))
        return info
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read video stream: {str(error)}"
        )


@router.post("/extract-frames")
def extract_frames_endpoint(req: ExtractFramesRequest):
    """
    Extract frames from an uploaded video file.
    Frames are stored in a dedicated folder in data/video_frames/<video_stem>/
    and also registered in uploads/ so they can be processed directly by the
    existing POST /api/analysis/temporal-strain endpoint.
    """
    safe_name = Path(req.filename).name
    video_path = VIDEO_UPLOAD_DIR / safe_name

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file '{safe_name}' not found."
        )

    if req.frame_interval < 1:
        raise HTTPException(
            status_code=400,
            detail="frame_interval must be >= 1"
        )

    if req.max_frames < 2:
        raise HTTPException(
            status_code=400,
            detail="max_frames must be >= 2"
        )

    video_stem = video_path.stem
    output_dir = FRAMES_BASE_DIR / video_stem

    try:
        extracted = extract_video_frames(
            video_path=str(video_path),
            output_directory=str(output_dir),
            frame_interval=req.frame_interval,
            max_frames=req.max_frames,
            format_ext="jpg"
        )

        # For seamless interoperability with the existing POST /api/analysis/temporal-strain,
        # copy or link extracted frames into GENERAL_UPLOADS_DIR prefixed with the video stem
        registered_frame_names: List[str] = []
        for f_name in extracted:
            src = output_dir / f_name
            # Unique registered name in uploads/
            reg_name = f"{video_stem}_{f_name}"
            dst = GENERAL_UPLOADS_DIR / reg_name
            if not dst.exists():
                shutil.copyfile(src, dst)
            registered_frame_names.append(reg_name)

        return {
            "message": "Frames extracted successfully",
            "video": safe_name,
            "frame_count": len(registered_frame_names),
            "frames": registered_frame_names,
            "relative_dir": f"/video-frames/{video_stem}"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Frame extraction failed: {str(error)}"
        )

