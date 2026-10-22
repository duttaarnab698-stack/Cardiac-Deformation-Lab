from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.version import APP_VERSION, API_TITLE, API_DESCRIPTION, SCIENTIFIC_DISCLAIMER
from app.core.config import CORS_ORIGINS, ENVIRONMENT, UPLOADS_DIR, OUTPUTS_DIR, REPORTS_DIR, DATA_DIR
from app.core.logging import setup_logger

from app.api.upload import router as upload_router
from app.api.analysis import router as analysis_router
from app.api.history import router as history_router
from app.api.reports import router as reports_router
from app.api.video import router as video_router
from app.api.studies import router as studies_router
from app.api.comparison import router as comparison_router
from app.api.quality import router as quality_router
from app.api.longitudinal import router as longitudinal_router
from app.api.statistics import router as statistics_router
from app.api.synthetic import router as synthetic_router
from app.api.annotations import router as annotations_router
from app.api.real_validation import router as real_validation_router
from app.api.auth import router as auth_router

logger = setup_logger("cdl.main")

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=APP_VERSION
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error during {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )

outputs_dir = Path("outputs")
outputs_dir.mkdir(parents=True, exist_ok=True)

reports_dir = Path("reports")
reports_dir.mkdir(parents=True, exist_ok=True)

uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)

frames_dir = Path("data/video_frames")
frames_dir.mkdir(parents=True, exist_ok=True)

synthetic_dir = Path("data/synthetic")
synthetic_dir.mkdir(parents=True, exist_ok=True)

app.mount(
    "/outputs",
    StaticFiles(directory="outputs"),
    name="outputs"
)

app.mount(
    "/reports",
    StaticFiles(directory="reports"),
    name="reports"
)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

app.mount(
    "/video-frames",
    StaticFiles(directory="data/video_frames"),
    name="video-frames"
)

app.mount(
    "/synthetic-data",
    StaticFiles(directory="data/synthetic"),
    name="synthetic-data"
)


app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(history_router)
app.include_router(reports_router)
app.include_router(video_router)
app.include_router(studies_router)
app.include_router(comparison_router)
app.include_router(quality_router)
app.include_router(longitudinal_router)
app.include_router(statistics_router)
app.include_router(synthetic_router)
app.include_router(annotations_router)
app.include_router(real_validation_router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "Cardiac Deformation Lab API is running",
        "status": "success",
        "version": APP_VERSION
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "cardiac-deformation-lab",
        "version": APP_VERSION,
        "environment": ENVIRONMENT
    }


@app.get("/disclaimer")
def get_scientific_disclaimer():
    return {
        "disclaimer": SCIENTIFIC_DISCLAIMER,
        "version": APP_VERSION
    }