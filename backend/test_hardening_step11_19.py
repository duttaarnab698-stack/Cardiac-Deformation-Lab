"""
backend/test_hardening_step11_19.py

Comprehensive test suite for Step 11.19: Production Hardening, Performance & Security.
Validates:
1. Versioning & Health Check endpoint
2. Path Traversal rejection & filename sanitization
3. Magic Bytes file content verification
4. File upload size limit enforcement (413)
5. Comparison endpoint authorization & IDOR prevention
6. Atomic JSON writes and corrupted-file recovery
7. Sensitive credential redaction in logging
8. Global exception handler structure (no traceback leaks)
"""

import io
import json
import logging
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.version import APP_VERSION, API_TITLE, SCIENTIFIC_DISCLAIMER
from app.core.config import ENVIRONMENT, MAX_IMAGE_UPLOAD_BYTES
from app.core.security import (
    sanitize_filename,
    resolve_safe_path,
    verify_image_file_content,
    atomic_write_json,
    safe_load_json,
)
from app.core.logging import SanitizingFormatter, setup_logger
from app.services.auth import create_access_token, hash_password, _save_all_users
from app.services.history import save_analysis_result, clear_all_history
from app.services.comparison_history import save_comparison, delete_comparison_by_id

client = TestClient(app)


def test_01_versioning_and_health_endpoint():
    """Verify single source of truth versioning and health endpoint."""
    assert APP_VERSION == "1.0.4"
    assert API_TITLE == "Cardiac Deformation Lab API"

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "cardiac-deformation-lab"
    assert data["version"] == APP_VERSION
    assert "environment" in data

    disc_resp = client.get("/disclaimer")
    assert disc_resp.status_code == 200
    disc_data = disc_resp.json()
    assert "disclaimer" in disc_data
    assert disc_data["version"] == APP_VERSION


def test_02_path_traversal_prevention():
    """Verify strict path traversal rejection and filename sanitization."""
    # Filename sanitization
    safe_name = sanitize_filename("../../etc/passwd.png")
    assert ".." not in safe_name
    assert "/" not in safe_name
    assert "\\" not in safe_name

    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        safe_file = base_dir / "valid_image.png"
        safe_file.write_text("dummy")

        # Resolving safe relative path should succeed
        resolved = resolve_safe_path(base_dir, "valid_image.png")
        assert resolved.exists()

        # Path traversal should be rejected with 400
        try:
            resolve_safe_path(base_dir, "../outside_file.txt")
            assert False, "Should have raised HTTPException for traversal attempt"
        except Exception as e:
            assert getattr(e, "status_code", None) == 400

    # API endpoint path traversal test
    resp = client.post(
        "/api/analysis/preprocess",
        params={"image_filename": "../../../../../windows/system32/cmd.exe"}
    )
    assert resp.status_code == 400
    assert "path traversal" in resp.json()["detail"].lower()


def test_03_magic_bytes_image_content_validation():
    """Verify magic bytes validation detects and rejects spoofed file extensions."""
    # Valid PNG header
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    assert verify_image_file_content(png_bytes, "valid.png") is True

    # Valid JPEG header
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    assert verify_image_file_content(jpeg_bytes, "valid.jpg") is True

    # Spoofed executable renamed to .png
    fake_png_bytes = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 20
    assert verify_image_file_content(fake_png_bytes, "fake.png") is False


def test_04_file_upload_size_limit():
    """Verify rejection with 413 when uploaded file exceeds MAX_IMAGE_UPLOAD_BYTES."""
    oversized_data = io.BytesIO(b"A" * (MAX_IMAGE_UPLOAD_BYTES + 1024))
    resp = client.post(
        "/api/upload/image",
        files={"file": ("huge_image.png", oversized_data, "image/png")}
    )
    assert resp.status_code == 413
    assert "exceeds maximum allowed size" in resp.json()["detail"].lower()


def test_05_atomic_json_storage_and_recovery():
    """Verify atomic write prevents corruption and safe_load_json recovers gracefully."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_file = Path(tmp_dir) / "test_data.json"

        # Atomic write
        payload = [{"id": "item1", "value": 42}]
        atomic_write_json(json_file, payload)
        loaded = safe_load_json(json_file, list)
        assert loaded == payload

        # Corrupted JSON simulation
        json_file.write_text("{ this is malformed invalid json ::::")
        fallback = safe_load_json(json_file, list)
        assert fallback == []


def test_06_sensitive_data_logging_redaction():
    """Verify SanitizingFormatter redacts passwords, JWT tokens, and secrets."""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Login failed for user with password=SuperSecretPassword123 and token=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy and secret_key=mysecret",
        args=(),
        exc_info=None
    )
    formatter = SanitizingFormatter("%(message)s")
    sanitized = formatter.format(record)

    assert "SuperSecretPassword123" not in sanitized
    assert "eyJhbGci" not in sanitized
    assert "REDACTED" in sanitized


def test_07_comparison_authorization_and_idor_prevention():
    """Verify researcher role cannot access or compare analyses belonging to another researcher."""
    from app.services.auth import create_user, get_user_by_email

    clear_all_history()

    # Create or get Researcher 1
    u1 = get_user_by_email("u1_res@test.org")
    if not u1:
        u1 = create_user("Researcher One", "u1_res@test.org", "Password123!", role="researcher")
    user1_id = u1["id"]
    user1_token = create_access_token(user1_id, "researcher")
    headers_u1 = {"Authorization": f"Bearer {user1_token}"}

    # Create or get Researcher 2
    u2 = get_user_by_email("u2_res@test.org")
    if not u2:
        u2 = create_user("Researcher Two", "u2_res@test.org", "Password123!", role="researcher")
    user2_id = u2["id"]
    user2_token = create_access_token(user2_id, "researcher")
    headers_u2 = {"Authorization": f"Bearer {user2_token}"}

    # Add analysis owned by User 1
    res1 = {
        "displacement": {"mean_displacement": 2.5, "max_displacement": 5.0, "min_displacement": 0.0, "std_displacement": 0.5},
        "strain_statistics": {"mean_principal_strain": 0.12},
        "advanced_metrics": {},
        "cardiac_deformation_fingerprint": {"fingerprint": {"D_mean": 2.5}},
        "outputs": {"displacement_heatmap": "outputs/disp1.png"},
    }
    rec1 = save_analysis_result(res1, record_type="single_pair", owner_id=user1_id)
    aid1 = rec1["id"]

    # Add second analysis owned by User 1
    res2 = {
        "displacement": {"mean_displacement": 2.8, "max_displacement": 5.2, "min_displacement": 0.0, "std_displacement": 0.6},
        "strain_statistics": {"mean_principal_strain": 0.14},
        "advanced_metrics": {},
        "cardiac_deformation_fingerprint": {"fingerprint": {"D_mean": 2.8}},
        "outputs": {"displacement_heatmap": "outputs/disp2.png"},
    }
    rec2 = save_analysis_result(res2, record_type="single_pair", owner_id=user1_id)
    aid2 = rec2["id"]

    # User 1 can compare their own analyses
    resp_u1 = client.post(
        "/api/comparison",
        headers=headers_u1,
        json={"analysis_ids": [aid1, aid2]}
    )
    assert resp_u1.status_code == 200

    # User 2 cannot compare User 1's analyses (IDOR prevention)
    resp_u2 = client.post(
        "/api/comparison",
        headers=headers_u2,
        json={"analysis_ids": [aid1, aid2]}
    )
    assert resp_u2.status_code == 403
    assert "Forbidden" in resp_u2.json()["detail"]


def test_08_global_exception_handler_sanitization():
    """Verify unhandled exceptions return structured JSON without leaking tracebacks."""
    # Call an endpoint that raises unhandled error by intentionally passing trigger if needed
    # Or test by inspecting main exception handler directly
    from fastapi import Request
    from app.main import global_unhandled_exception_handler
    import asyncio

    class DummyRequest:
        method = "GET"
        url = type("URL", (), {"path": "/api/test/fail"})()

    dummy_req = DummyRequest()
    exc = RuntimeError("Database connection string postgresql://user:secretpass@db.local/lab exploded")

    response = asyncio.run(global_unhandled_exception_handler(dummy_req, exc))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "secretpass" not in str(body)
    assert "exploded" not in str(body)
    assert body["detail"] == "An internal server error occurred."


if __name__ == "__main__":
    test_01_versioning_and_health_endpoint()
    print("[PASS] Test 01: Versioning and Health Endpoint")
    test_02_path_traversal_prevention()
    print("[PASS] Test 02: Path Traversal Prevention")
    test_03_magic_bytes_image_content_validation()
    print("[PASS] Test 03: Magic Bytes Image Validation")
    test_04_file_upload_size_limit()
    print("[PASS] Test 04: File Upload Size Limit (413)")
    test_05_atomic_json_storage_and_recovery()
    print("[PASS] Test 05: Atomic JSON Storage and Recovery")
    test_06_sensitive_data_logging_redaction()
    print("[PASS] Test 06: Sensitive Data Logging Redaction")
    test_07_comparison_authorization_and_idor_prevention()
    print("[PASS] Test 07: Comparison Authorization and IDOR Prevention")
    test_08_global_exception_handler_sanitization()
    print("[PASS] Test 08: Global Exception Handler Sanitization")
    print("\nALL STEP 11.19 HARDENING TESTS PASSED!")
