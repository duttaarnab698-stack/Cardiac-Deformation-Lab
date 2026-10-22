from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid

from app.core.config import MAX_IMAGE_UPLOAD_BYTES, UPLOADS_DIR
from app.core.security import (
    ALLOWED_IMAGE_EXTENSIONS,
    sanitize_filename,
    verify_image_file_content,
)
from app.core.logging import logger

router = APIRouter(
    prefix="/api/upload",
    tags=["Upload"]
)


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Securely upload a cardiac image (.png, .jpg, .jpeg, .bmp, .tif, .tiff).
    Validates file extension, upload size, and image magic bytes.
    """
    safe_orig_name = sanitize_filename(file.filename)
    extension = Path(safe_orig_name).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{extension}'. Allowed formats: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )

    # Read content with size check
    content = await file.read()
    if len(content) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size ({MAX_IMAGE_UPLOAD_BYTES // (1024 * 1024)} MB)."
        )

    if len(content) < 4:
        raise HTTPException(
            status_code=400,
            detail="File is empty or corrupted."
        )

    # Verify magic bytes
    if not verify_image_file_content(content[:32], safe_orig_name):
        raise HTTPException(
            status_code=400,
            detail="File content does not match standard image format signatures."
        )

    unique_name = f"{uuid.uuid4()}{extension}"
    file_path = UPLOADS_DIR / unique_name

    with file_path.open("wb") as buffer:
        buffer.write(content)

    logger.info(f"Image uploaded successfully: {safe_orig_name} -> {unique_name} ({len(content)} bytes)")

    return {
        "message": "Image uploaded successfully",
        "filename": safe_orig_name,
        "saved_filename": unique_name,
        "path": str(file_path)
    }