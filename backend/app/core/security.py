"""
backend/app/core/security.py

Security and validation utilities for Cardiac Deformation Lab.
Provides:
- Path traversal prevention and path sanitization
- Uploaded file header/magic bytes verification
- Safe filename generation
- JSON storage atomic writes with automatic recovery
"""

import os
import re
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

# Allowed extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Magic bytes for reliable file content verification
IMAGE_MAGIC_SIGNATURES = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\xff\xd8\xff", ".jpeg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"BM", ".bmp"),
    (b"II*\x00", ".tif"),
    (b"MM\x00*", ".tif"),
    (b"II*\x00", ".tiff"),
    (b"MM\x00*", ".tiff"),
]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a user-provided filename by extracting only the base name,
    stripping directory path separators, and replacing unsafe characters.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    # Strip any directory separators (/ and \)
    base = os.path.basename(filename.replace("\\", "/"))
    # Remove null bytes and non-printable characters
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()

    if not cleaned or cleaned in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename provided.")

    return cleaned


def resolve_safe_path(base_dir: Path, filename: str) -> Path:
    """
    Safely resolve a filename within an intended target base directory,
    strictly verifying that the resolved path does not escape base_dir.
    Raises HTTPException(400) on path traversal attempts.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise HTTPException(
            status_code=400,
            detail="Security error: Path traversal detected. Access outside target directory is prohibited."
        )

    cleaned_name = sanitize_filename(filename)
    resolved_base = base_dir.resolve()
    target_path = (resolved_base / cleaned_name).resolve()

    try:
        target_path.relative_to(resolved_base)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Security error: Path traversal detected. Access outside target directory is prohibited."
        )

    return target_path


def verify_image_file_content(file_bytes: bytes, filename: str) -> bool:
    """
    Validate that file bytes match expected image magic headers.
    Returns True if valid, False if mismatched.
    """
    if not file_bytes or len(file_bytes) < 4:
        return False

    ext = Path(filename).suffix.lower()
    for signature, sig_ext in IMAGE_MAGIC_SIGNATURES:
        if file_bytes.startswith(signature):
            if ext in (sig_ext, ".jpg", ".jpeg", ".tif", ".tiff") and sig_ext in (".jpg", ".jpeg", ".tif", ".tiff"):
                return True
            if ext == sig_ext:
                return True
    return False


def atomic_write_json(file_path: Path, data: Any, indent: int = 2) -> None:
    """
    Thread/crash-safe JSON writer using temporary file creation and atomic rename.
    Ensures that existing data files are never truncated or corrupted if a write fails.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp_{uuid.uuid4().hex[:8]}")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # Atomic replace
        temp_path.replace(file_path)
    except Exception as exc:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise IOError(f"Failed to atomically persist JSON data to '{file_path}': {str(exc)}")


def safe_load_json(file_path: Path, default_factory: Any = list) -> Any:
    """
    Load JSON from a file, returning a default value if missing or corrupt,
    without raising unhandled exceptions.
    """
    if not file_path.exists():
        return default_factory() if callable(default_factory) else default_factory

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default_factory() if callable(default_factory) else default_factory
            return json.loads(content)
    except Exception:
        # Graceful fallback on corrupt JSON
        return default_factory() if callable(default_factory) else default_factory
