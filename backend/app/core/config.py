"""
backend/app/core/config.py

Centralized configuration and environment settings for Cardiac Deformation Lab.
Loads from environment variables with safe development defaults.
Ensures production safety, configurable CORS, upload limits, and JWT parameters.
"""

import os
from pathlib import Path
from typing import List

# Environment: "development", "staging", "production", "testing"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION: bool = ENVIRONMENT == "production"
IS_DEVELOPMENT: bool = ENVIRONMENT in ("development", "dev", "testing")

# Security & Cryptography
# In production, SECRET_KEY must be provided via environment variable
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "cardiac-lab-dev-secret-key-32bytes-secure!")
if IS_PRODUCTION and JWT_SECRET_KEY == "cardiac-lab-dev-secret-key-32bytes-secure!":
    import warnings
    warnings.warn(
        "CRITICAL SECURITY WARNING: Running in production with default development JWT_SECRET_KEY! "
        "Set JWT_SECRET_KEY in your production environment.",
        RuntimeWarning
    )

JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
JWT_ALGORITHM: str = "HS256"

# CORS Configuration
_DEFAULT_CORS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

_env_cors = os.getenv("CORS_ORIGINS", "")
if _env_cors:
    CORS_ORIGINS: List[str] = [origin.strip() for origin in _env_cors.split(",") if origin.strip()]
else:
    CORS_ORIGINS: List[str] = _DEFAULT_CORS

# File & Storage Limits
# 50 MB maximum image file size
MAX_IMAGE_UPLOAD_BYTES: int = int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(50 * 1024 * 1024)))
# 200 MB maximum video file size
MAX_VIDEO_UPLOAD_BYTES: int = int(os.getenv("MAX_VIDEO_UPLOAD_BYTES", str(200 * 1024 * 1024)))

# Input Validation Bounds for Analysis
MAX_IMAGE_DIMENSION: int = int(os.getenv("MAX_IMAGE_DIMENSION", "4096"))
MIN_IMAGE_DIMENSION: int = int(os.getenv("MIN_IMAGE_DIMENSION", "16"))
MAX_TEMPORAL_FRAMES: int = int(os.getenv("MAX_TEMPORAL_FRAMES", "300"))

# Logging Level
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# Storage Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"

for directory in [UPLOADS_DIR, OUTPUTS_DIR, REPORTS_DIR, DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

