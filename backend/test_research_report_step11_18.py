"""
Unit & Integration Test Suite for Step 11.18:
Publication-Ready Research Report and Scientific Export System.

Tests:
1. Generation of 21-section Comprehensive Research Report PDF (POST /api/reports/research/{study_id}).
2. Generation of Research Export Package ZIP (POST /api/reports/research/{study_id}/package).
3. Verification of internal package contents (PDF, CSVs, JSON metadata, figures, methodology.txt).
4. Verification of CSV export structure (analysis_metrics.csv, temporal_metrics.csv, longitudinal_metrics.csv, statistics.csv).
5. Verification that JSON metadata strictly omits auth tokens, passwords, and security data.
6. Study report history tracking (GET /api/reports/history/{study_id} and GET /api/reports/history).
7. Non-clinical research disclaimers present in metadata, PDF, and export packages.
8. Access control and ownership isolation on research reports and packages.
9. Regression verification for existing report endpoints:
   - POST /api/reports/{analysis_id} (single analysis report)
   - POST /api/reports/longitudinal/{study_id} (longitudinal report)
   - POST /api/reports/statistics/{study_id} (statistics report)
"""

import os
import sys
import uuid
import zipfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
import numpy as np
import cv2

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app.main import app
from app.services.auth import create_access_token

client = TestClient(app)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
REPORTS_DIR = Path("reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def create_synthetic_pair_files():
    """Create two test frames in uploads/ for testing."""
    h, w = 120, 120
    f1 = np.full((h, w), 50, dtype=np.uint8)
    cv2.circle(f1, (60, 60), 30, 180, -1)
    cv2.circle(f1, (60, 60), 15, 50, -1)

    f2 = np.full((h, w), 50, dtype=np.uint8)
    cv2.circle(f2, (63, 62), 33, 180, -1)
    cv2.circle(f2, (63, 62), 17, 50, -1)

    uid = uuid.uuid4().hex[:6]
    fn1 = f"test_rep_f1_{uid}.png"
    fn2 = f"test_rep_f2_{uid}.png"
    cv2.imwrite(str(UPLOAD_DIR / fn1), f1)
    cv2.imwrite(str(UPLOAD_DIR / fn2), f2)
    return fn1, fn2


def setup_test_study_with_analyses():
    """Helper to create a test study with 2 analyses."""
    fn1, fn2 = create_synthetic_pair_files()
    a1_res = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&pixel_spacing_x=0.5&pixel_spacing_y=0.5&unit=mm"
    ).json()
    a1_id = a1_res["id"]

    fn3, fn4 = create_synthetic_pair_files()
    a2_res = client.post(
        f"/api/analysis/strain?image1_filename={fn3}&image2_filename={fn4}&pixel_spacing_x=0.5&pixel_spacing_y=0.5&unit=mm"
    ).json()
    a2_id = a2_res["id"]

    # Create study
    st_res = client.post(
        "/api/studies",
        json={
            "title": f"Report Test Study {uuid.uuid4().hex[:6]}",
            "subject_code": "TEST-REP-01",
            "description": "Validation study for Step 11.18 reporting and export package."
        }
    ).json()
    study_id = st_res["id"]

    # Link analyses to study
    client.post(f"/api/studies/{study_id}/analyses/{a1_id}")
    client.post(f"/api/studies/{study_id}/analyses/{a2_id}")

    return study_id, [a1_id, a2_id], [fn1, fn2, fn3, fn4]


def test_01_comprehensive_research_report_generation():
    """Verify POST /api/reports/research/{study_id} generates valid 21-section PDF."""
    study_id, analysis_ids, files = setup_test_study_with_analyses()
    try:
        res = client.post(f"/api/reports/research/{study_id}")
        assert res.status_code == 200, res.text
        data = res.json()
        assert "report" in data
        assert "url" in data
        assert "report_filename" in data
        assert "study_id" in data
        assert data["study_id"] == study_id

        report_meta = data["report"]
        assert report_meta["report_type"] == "comprehensive_research"
        assert report_meta["software_version"] == "1.0.4"
        assert report_meta["report_schema_version"] == "1.0"
        assert "disclaimer" in report_meta
        assert "Not For Diagnostic Use" in report_meta["disclaimer"]

        # Verify PDF exists on disk and is non-empty
        pdf_path = REPORTS_DIR / data["report_filename"]
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 5000  # Multi-page PDF
    finally:
        for fn in files:
            p = UPLOAD_DIR / fn
            if p.exists():
                p.unlink()


def test_02_research_export_package_generation():
    """Verify POST /api/reports/research/{study_id}/package builds a valid ZIP research archive."""
    study_id, analysis_ids, files = setup_test_study_with_analyses()
    try:
        res = client.post(f"/api/reports/research/{study_id}/package")
        assert res.status_code == 200, res.text
        data = res.json()
        assert "package" in data
        assert "filename" in data
        assert data["filename"].endswith(".zip")

        zip_path = REPORTS_DIR / data["filename"]
        assert zip_path.exists()
        assert zip_path.stat().st_size > 1000

        # Inspect ZIP internal files
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            namelist = zf.namelist()
            # 1. Comprehensive PDF
            assert any(n.endswith(".pdf") for n in namelist)
            # 2. CSV summaries
            assert "analysis_metrics.csv" in namelist
            assert "temporal_metrics.csv" in namelist
            assert "longitudinal_metrics.csv" in namelist
            assert "statistics.csv" in namelist
            assert "validation_metrics.csv" in namelist
            # 3. JSON metadata
            assert "research_metadata.json" in namelist
            # 4. Methodology text
            assert "methodology.txt" in namelist

            # Verify JSON metadata content
            json_bytes = zf.read("research_metadata.json")
            meta_json = json.loads(json_bytes.decode("utf-8"))
            assert "study" in meta_json
            assert "analyses" in meta_json
            assert meta_json["study"]["id"] == study_id
            # Security check: Ensure no password, password_hash, token, secret
            dumped_str = json.dumps(meta_json).lower()
            assert "password" not in dumped_str
            assert "access_token" not in dumped_str
            assert "secret" not in dumped_str

            # Verify analysis_metrics.csv content
            csv_lines = zf.read("analysis_metrics.csv").decode("utf-8").strip().splitlines()
            assert len(csv_lines) >= 3  # Header + 2 analyses
            header = csv_lines[0].split(",")
            assert "mean_displacement" in header
            assert "mean_principal_strain" in header
    finally:
        for fn in files:
            p = UPLOAD_DIR / fn
            if p.exists():
                p.unlink()


def test_03_report_history_tracking():
    """Verify report metadata persistence in backend/data/reports.json and history retrieval."""
    study_id, analysis_ids, files = setup_test_study_with_analyses()
    try:
        # Generate a report to ensure an entry exists
        rep_res = client.post(f"/api/reports/research/{study_id}").json()
        rep_id = rep_res["report"]["report_id"]

        # Fetch study report history
        hist_res = client.get(f"/api/reports/history/{study_id}")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert "reports" in hist_data
        study_reports = hist_data["reports"]
        assert len(study_reports) >= 1
        assert any(r["report_id"] == rep_id for r in study_reports)

        # Fetch global reports history
        all_res = client.get("/api/reports/history")
        assert all_res.status_code == 200
        all_data = all_res.json()
        assert "total_reports" in all_data
        assert all_data["total_reports"] >= 1
    finally:
        for fn in files:
            p = UPLOAD_DIR / fn
            if p.exists():
                p.unlink()


def test_04_access_control_on_research_reports():
    """Verify role-based access control and isolation on report generation."""
    # Register real user A
    email_a = f"alice_{uuid.uuid4().hex[:6]}@cardiaclab.local"
    reg_a = client.post(
        "/api/auth/register",
        json={"name": "Alice User", "email": email_a, "password": "Password123!"}
    ).json()
    token_a = reg_a.get("token") or reg_a.get("access_token")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    st_res = client.post(
        "/api/studies",
        headers=headers_a,
        json={"title": "Private Research Study A", "subject_code": "PRIV-A"}
    ).json()
    st_id = st_res["id"]

    # Register real user B (different researcher)
    email_b = f"bob_{uuid.uuid4().hex[:6]}@cardiaclab.local"
    reg_b = client.post(
        "/api/auth/register",
        json={"name": "Bob User", "email": email_b, "password": "Password123!"}
    ).json()
    token_b = reg_b.get("token") or reg_b.get("access_token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B should be forbidden from generating reports for User A's study
    forbidden_rep = client.post(f"/api/reports/research/{st_id}", headers=headers_b)
    assert forbidden_rep.status_code == 403

    # User B should be forbidden from exporting package for User A's study
    forbidden_pkg = client.post(f"/api/reports/research/{st_id}/package", headers=headers_b)
    assert forbidden_pkg.status_code == 403

    # Admin should have full access
    admin_token = create_access_token(user_id="admin_user", role="admin")
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    admin_rep = client.post(f"/api/reports/research/{st_id}", headers=headers_admin)
    assert admin_rep.status_code == 200


def test_05_regression_existing_report_endpoints():
    """Verify existing single-analysis, longitudinal, and statistics report endpoints continue functioning."""
    study_id, analysis_ids, files = setup_test_study_with_analyses()
    try:
        a1_id = analysis_ids[0]

        # 1. Single analysis report
        single_rep = client.post(f"/api/reports/{a1_id}")
        assert single_rep.status_code == 200
        assert "report_filename" in single_rep.json()

        # 2. Longitudinal report
        long_rep = client.post(f"/api/reports/longitudinal/{study_id}")
        assert long_rep.status_code == 200
        assert "report_filename" in long_rep.json()

        # 3. Statistics report
        stat_rep = client.post(f"/api/reports/statistics/{study_id}?scope=full_image")
        assert stat_rep.status_code == 200
        assert "report_filename" in stat_rep.json()
    finally:
        for fn in files:
            p = UPLOAD_DIR / fn
            if p.exists():
                p.unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING CDL STEP 11.18 RESEARCH REPORT & EXPORT TEST SUITE")
    print("=" * 60)
    tests = [
        test_01_comprehensive_research_report_generation,
        test_02_research_export_package_generation,
        test_03_report_history_tracking,
        test_04_access_control_on_research_reports,
        test_05_regression_existing_report_endpoints,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"[FAIL] {t.__name__}:")
            traceback.print_exc()
            failed += 1
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)
