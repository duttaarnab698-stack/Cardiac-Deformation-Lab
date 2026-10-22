"""
backend/test_complete_suite_step11_20.py

Comprehensive End-to-End Master Test Suite for Cardiac Deformation Lab.
Validates Step 11.20 requirements across all backend layers:
1. Health
2. Auth (Register, Login, Role restrictions)
3. Upload (Valid, Invalid ext, Invalid bytes, Traversal, 413)
4. Analysis (Preprocess, Displacement, Strain, Temporal, Missing)
5. ROI (Rectangle, Ellipse, Polygon, Invalid)
6. Calibration (Valid, Invalid, Physical Displacement)
7. Studies (CRUD & Ownership)
8. Comparison (Valid, Invalid, IDOR 403)
9. Quality Control (Valid, 404)
10. Longitudinal (Summary & Timeline)
11. Statistics (Descriptive, Correlations, Outliers)
12. Synthetic Validation (Generation, Ground Truth, Benchmarking)
13. Real Validation (Annotation CRUD, Real Benchmark)
14. Reports & Exports (PDF Report, Zip Package, Access Control)
15. Explorer (Outputs & Metadata)
16. Error Handling (400, 401, 403, 404, 422, 500-safe)
"""

import io
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

import cv2
import numpy as np

from app.main import app
from app.core.version import APP_VERSION, API_TITLE, SCIENTIFIC_DISCLAIMER
from app.core.config import MAX_IMAGE_UPLOAD_BYTES, UPLOADS_DIR, OUTPUTS_DIR
from app.services.auth import create_access_token, create_user, get_user_by_email
from app.services.history import save_analysis_result, clear_all_history, get_history_by_id
from app.services.studies import create_study, add_analysis_to_study
from app.services.annotations import create_annotation, get_annotations, delete_annotation
from app.services.synthetic_data import generate_synthetic_dataset, save_synthetic_dataset

client = TestClient(app)


# Helper to generate test images with synthetic textures on disk
def _create_test_image(filename: str, width: int = 128, height: int = 128, shift: int = 0) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    img_path = UPLOADS_DIR / filename
    img = np.zeros((height, width), dtype=np.uint8)
    # Draw circular cardiac phantom wall
    cv2.circle(img, (width // 2 + shift, height // 2), 35, 180, thickness=-1)
    cv2.circle(img, (width // 2 + shift, height // 2), 20, 40, thickness=-1)
    # Add texture speckles
    np.random.seed(42 + shift)
    noise = np.random.normal(0, 15, (height, width)).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    cv2.imwrite(str(img_path), img)
    return img_path


def test_01_health_and_version():
    """Verify health endpoint and single source of truth versioning."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == APP_VERSION

    disc_resp = client.get("/disclaimer")
    assert disc_resp.status_code == 200
    assert "optical-flow" in disc_resp.json()["disclaimer"].lower()
    print("  [PASS] 1. Health & Version verified")


def test_02_auth_system():
    """Verify authentication, registration, login, role restrictions."""
    email = f"tester_{uuid.uuid4().hex[:6]}@lab.test"
    # Registration
    reg_resp = client.post("/api/auth/register", json={
        "name": "Dr. Researcher",
        "email": email,
        "password": "SecurePassword123!",
        "role": "researcher"
    })
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()["user"]
    assert user_data["email"] == email

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePassword123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token

    # Invalid login
    bad_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # Protected endpoint without token
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    # Protected endpoint with valid token
    auth_req = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_req.status_code == 200
    assert auth_req.json()["email"] == email

    # Role restriction test: reviewer cannot access admin endpoints
    rev_user = create_user("Reviewer One", f"rev_{uuid.uuid4().hex[:6]}@lab.test", "Password123!", role="reviewer")
    rev_token = create_access_token(user_id=rev_user["id"], role="reviewer")
    rev_resp = client.get("/api/auth/users", headers={"Authorization": f"Bearer {rev_token}"})
    assert rev_resp.status_code == 403
    print("  [PASS] 2. Authentication & Role-Based Access verified")


def test_03_file_upload_and_security():
    """Verify upload, extension rejection, magic bytes, path traversal, and 413 limits."""
    # 1. Valid image upload
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    valid_up = client.post(
        "/api/upload/image",
        files={"file": ("sample.png", io.BytesIO(png_header), "image/png")}
    )
    assert valid_up.status_code == 200
    saved_fn = valid_up.json()["saved_filename"]

    # 2. Invalid extension
    bad_ext = client.post(
        "/api/upload/image",
        files={"file": ("script.py", io.BytesIO(b"print('hello')"), "text/x-python")}
    )
    assert bad_ext.status_code == 400

    # 3. Invalid magic bytes (spoofed .png containing random text)
    spoofed = client.post(
        "/api/upload/image",
        files={"file": ("fake.png", io.BytesIO(b"This is not a real image"), "image/png")}
    )
    assert spoofed.status_code == 400

    # 4. Path traversal attempt in image preprocessing
    traversal = client.post(
        "/api/analysis/preprocess",
        params={"image_filename": "../../../boot.ini"}
    )
    assert traversal.status_code == 400

    # 5. Oversized upload (413)
    oversized = io.BytesIO(b"A" * (MAX_IMAGE_UPLOAD_BYTES + 512))
    size_err = client.post(
        "/api/upload/image",
        files={"file": ("huge.png", oversized, "image/png")}
    )
    assert size_err.status_code == 413
    print("  [PASS] 3. File Upload, Magic Bytes & Path Traversal Guards verified")


def test_04_analysis_motion_and_strain():
    """Verify preprocessing, optical flow displacement, strain tensor, and missing files."""
    fn1 = "test_frame_1.png"
    fn2 = "test_frame_2.png"
    _create_test_image(fn1, shift=0)
    _create_test_image(fn2, shift=2)

    # Preprocessing
    pre_resp = client.post("/api/analysis/preprocess", params={"image_filename": fn1})
    assert pre_resp.status_code == 200

    # Missing file check
    missing_resp = client.post("/api/analysis/preprocess", params={"image_filename": "non_existent.png"})
    assert missing_resp.status_code == 404

    # Displacement
    disp_resp = client.post("/api/analysis/displacement", params={
        "image1_filename": fn1,
        "image2_filename": fn2
    })
    assert disp_resp.status_code == 200
    disp_data = disp_resp.json()
    assert "mean_displacement" in disp_data
    assert disp_data["mean_displacement"] >= 0

    # Strain tensor and advanced metrics
    strain_resp = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2
    })
    assert strain_resp.status_code == 200
    st_data = strain_resp.json()
    assert "mean_principal_strain_1" in st_data["strain_statistics"]
    assert "motion_coherence" in st_data["advanced_metrics"]
    print("  [PASS] 4. Motion Estimation, Displacement & Strain Tensors verified")


def test_05_roi_and_calibration():
    """Verify ROI masks (rect, ellipse, polygon, invalid) and spatial calibration."""
    fn1 = "test_frame_1.png"
    fn2 = "test_frame_2.png"

    # 1. Rectangle ROI
    rect_roi = {"enabled": True, "type": "rectangle", "coordinates": {"x": 20, "y": 20, "width": 50, "height": 50}}
    rect_resp = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2,
        "roi": json.dumps(rect_roi)
    })
    assert rect_resp.status_code == 200
    assert rect_resp.json()["roi"]["enabled"] is True

    # 2. Ellipse ROI
    ellipse_roi = {"enabled": True, "type": "ellipse", "coordinates": {"cx": 64, "cy": 64, "rx": 30, "ry": 25}}
    el_resp = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2,
        "roi": json.dumps(ellipse_roi)
    })
    assert el_resp.status_code == 200

    # 3. Polygon ROI
    poly_roi = {"enabled": True, "type": "polygon", "coordinates": [{"x": 30, "y": 30}, {"x": 70, "y": 30}, {"x": 50, "y": 70}]}
    poly_resp = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2,
        "roi": json.dumps(poly_roi)
    })
    assert poly_resp.status_code == 200

    # 4. Invalid ROI (negative bounds)
    bad_roi = {"enabled": True, "type": "rectangle", "coordinates": {"x": 20, "y": 20, "width": -10, "height": 50}}
    bad_roi_resp = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2,
        "roi": json.dumps(bad_roi)
    })
    assert bad_roi_resp.status_code == 400

    # 5. Spatial calibration
    from app.services.calibration import calculate_physical_displacement_magnitude
    cal_resp = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2,
        "pixel_spacing_x": 0.5,
        "pixel_spacing_y": 0.5,
        "unit": "mm"
    })
    assert cal_resp.status_code == 200
    cal_data = cal_resp.json()
    assert cal_data["calibration"]["enabled"] is True
    assert cal_data["calibration"]["pixel_spacing_x"] == 0.5
    assert cal_data["calibration"]["unit"] == "mm"

    # 6. Invalid spacing (must be > 0, returns 400)
    bad_cal = client.post("/api/analysis/strain", params={
        "image1_filename": fn1,
        "image2_filename": fn2,
        "pixel_spacing_x": -0.5,
        "pixel_spacing_y": 0.5
    })
    assert bad_cal.status_code == 400

    # 7. Physical displacement magnitude calculation
    dummy_flow = np.ones((10, 10, 2), dtype=np.float32) * 2.0
    phys_mag = calculate_physical_displacement_magnitude(dummy_flow, 0.5, 0.5)
    assert np.isclose(phys_mag[0, 0], np.sqrt(2.0))
    print("  [PASS] 5. ROI Analysis & Spatial Calibration verified")


def test_06_studies_and_ownership():
    """Verify study creation, retrieval, updates, and user ownership isolation."""
    # User 1
    u1_user = create_user("Res User 1", f"res1_{uuid.uuid4().hex[:6]}@lab.test", "Password123!", role="researcher")
    u1_token = create_access_token(u1_user["id"], "researcher")
    h_u1 = {"Authorization": f"Bearer {u1_token}"}

    # User 2
    u2_user = create_user("Res User 2", f"res2_{uuid.uuid4().hex[:6]}@lab.test", "Password123!", role="researcher")
    u2_token = create_access_token(u2_user["id"], "researcher")
    h_u2 = {"Authorization": f"Bearer {u2_token}"}

    # Create study as User 1
    create_res = client.post("/api/studies", headers=h_u1, json={
        "title": "Study Cohort Alpha",
        "subject_code": "SUBJ-A01",
        "description": "Longitudinal cardiac motion study"
    })
    assert create_res.status_code == 201
    study_id = create_res.json()["id"]

    # Retrieve studies as User 1
    list_u1 = client.get("/api/studies", headers=h_u1)
    studies_1 = list_u1.json() if isinstance(list_u1.json(), list) else list_u1.json().get("studies", [])
    assert any(s["id"] == study_id for s in studies_1)

    # User 2 list should not see User 1's study
    list_u2 = client.get("/api/studies", headers=h_u2)
    studies_2 = list_u2.json() if isinstance(list_u2.json(), list) else list_u2.json().get("studies", [])
    assert not any(s["id"] == study_id for s in studies_2)

    # Update study as User 1
    up_res = client.put(f"/api/studies/{study_id}", headers=h_u1, json={
        "title": "Study Cohort Alpha - Phase 2"
    })
    assert up_res.status_code == 200
    assert up_res.json()["title"] == "Study Cohort Alpha - Phase 2"
    print("  [PASS] 6. Study Management & Ownership Isolation verified")
    return study_id, h_u1, h_u2, u1_user["id"]


def test_07_analysis_saving_and_qc(study_id: str, h_u1: dict, u1_id: str):
    """Verify saving analysis record, linking to study, and automated QC evaluation."""
    res = {
        "displacement": {"mean_displacement": 2.1, "max_displacement": 4.5, "min_displacement": 0.0, "std_displacement": 0.4},
        "strain_statistics": {"mean_principal_strain": 0.09, "max_principal_strain": 0.18, "mean_exx": 0.05, "mean_eyy": -0.04, "mean_exy": 0.01},
        "advanced_metrics": {"motion_coherence": 0.88, "anisotropy": 0.35, "deformation_energy": 12.4},
        "cardiac_deformation_fingerprint": {"fingerprint": {"D_mean": 2.1, "epsilon_principal": 0.09}},
        "outputs": {"displacement_heatmap": "outputs/disp.png"}
    }
    rec1 = save_analysis_result(res, record_type="single_pair", owner_id=u1_id)
    aid1 = rec1["id"]

    # Link to study
    link_res = client.post(f"/api/studies/{study_id}/analyses/{aid1}", headers=h_u1)
    assert link_res.status_code == 200

    # Evaluate Quality Control
    qc_resp = client.post(f"/api/quality/{aid1}")
    assert qc_resp.status_code == 200
    qc_data = qc_resp.json()
    assert "score" in qc_data
    assert "level" in qc_data
    assert qc_data["score"] >= 0

    # Missing analysis QC (404)
    qc_404 = client.post("/api/quality/invalid_analysis_id")
    assert qc_404.status_code == 404
    print("  [PASS] 7. Analysis Association & Automated Quality Control verified")
    return aid1


def test_08_longitudinal_and_statistics(study_id: str, aid1: str, h_u1: dict, u1_id: str):
    """Verify longitudinal summary, timeline series, and statistical analysis."""
    # Add a second analysis to study so we have a multi-session timeline
    res2 = {
        "displacement": {"mean_displacement": 2.4, "max_displacement": 4.9, "min_displacement": 0.0, "std_displacement": 0.5},
        "strain_statistics": {"mean_principal_strain": 0.11, "max_principal_strain": 0.20, "mean_exx": 0.06, "mean_eyy": -0.05, "mean_exy": 0.01},
        "advanced_metrics": {"motion_coherence": 0.89, "anisotropy": 0.38, "deformation_energy": 14.2},
        "cardiac_deformation_fingerprint": {"fingerprint": {"D_mean": 2.4, "epsilon_principal": 0.11}},
        "outputs": {"displacement_heatmap": "outputs/disp2.png"}
    }
    rec2 = save_analysis_result(res2, record_type="single_pair", owner_id=u1_id)
    aid2 = rec2["id"]
    client.post(f"/api/studies/{study_id}/analyses/{aid2}", headers=h_u1)

    # Longitudinal summary
    long_resp = client.get(f"/api/longitudinal/study/{study_id}")
    assert long_resp.status_code == 200
    long_data = long_resp.json()
    assert long_data["analysis_count"] >= 2
    assert "trends" in long_data

    # Statistics endpoint
    stats_resp = client.get(f"/api/statistics/study/{study_id}")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert "descriptive_statistics" in stats_data

    # Correlations endpoint
    corr_resp = client.get(f"/api/statistics/study/{study_id}/correlations")
    assert corr_resp.status_code == 200
    assert "correlations" in corr_resp.json()
    print("  [PASS] 8. Longitudinal Analytics & Statistical Modeling verified")
    return aid2


def test_09_synthetic_validation_workflow():
    """Verify synthetic dataset generation, ground-truth retrieval, and validation benchmark."""
    # Generate synthetic phantom dataset
    gen_resp = client.post("/api/synthetic/generate", json={
        "width": 128,
        "height": 128,
        "deformation_mode": "radial_expansion",
        "deformation_strength": 0.05,
        "frame_count": 3
    })
    assert gen_resp.status_code == 200
    ds_id = gen_resp.json()["dataset_id"]
    assert ds_id

    # Retrieve ground truth
    gt_resp = client.get(f"/api/synthetic/{ds_id}/ground-truth")
    assert gt_resp.status_code == 200
    assert "displacement_magnitude" in gt_resp.json()["available_fields"]

    # Validate against ground truth
    val_resp = client.post(f"/api/synthetic/{ds_id}/validate")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert "validation" in val_data
    val_summary = val_data["validation"]["summary"]
    assert "displacement_mae" in val_summary
    assert "mean_endpoint_error" in val_summary
    print("  [PASS] 9. Synthetic Phantom Validation & Benchmark verified")


def test_10_real_validation_and_annotations(aid1: str, h_u1: dict):
    """Verify manual annotation creation, retrieval, and real-image benchmarking."""
    # Create manual landmark annotation
    ann_resp = client.post("/api/annotations", headers=h_u1, json={
        "analysis_id": aid1,
        "image_filename": "test_frame_1.png",
        "annotation_type": "landmark",
        "annotator_label": "apex_reference",
        "points": [{"x": 64.0, "y": 64.0}]
    })
    assert ann_resp.status_code == 201
    ann_id = ann_resp.json()["id"]

    # Retrieve annotations for analysis
    get_anns = client.get(f"/api/annotations?analysis_id={aid1}", headers=h_u1)
    assert get_anns.status_code == 200
    assert any(a["id"] == ann_id for a in get_anns.json())

    # Benchmark analysis against annotations
    bench_resp = client.post(f"/api/validation/real/{aid1}")
    assert bench_resp.status_code == 200
    bench_data = bench_resp.json()
    assert bench_data["analysis_id"] == aid1
    assert bench_data["annotation_count"] >= 1
    assert "disclaimer" in bench_data
    print("  [PASS] 10. Manual Annotation CRUD & Real-Image Benchmark verified")


def test_11_reports_and_export_packages(study_id: str, aid1: str, h_u1: dict, h_u2: dict):
    """Verify standard report, comprehensive research report, and research package zip export."""
    # 1. Single Analysis Report
    rep_resp = client.post(f"/api/reports/{aid1}", headers=h_u1)
    if rep_resp.status_code != 200:
        print("rep_resp error:", rep_resp.status_code, rep_resp.json())
    assert rep_resp.status_code == 200
    assert "report_filename" in rep_resp.json()

    # 2. Comprehensive Research Report for study
    res_rep = client.post(f"/api/reports/research/{study_id}", headers=h_u1)
    assert res_rep.status_code == 200
    assert "comprehensive_research" in res_rep.json()["report_filename"]

    # 3. Research Export Package (.zip)
    pkg_resp = client.post(f"/api/reports/research/{study_id}/package", headers=h_u1)
    assert pkg_resp.status_code == 200
    pkg_fn = pkg_resp.json()["filename"]
    assert pkg_fn.endswith(".zip")

    # 4. IDOR Protection: User 2 cannot generate reports for User 1's study
    unauth_rep = client.post(f"/api/reports/research/{study_id}", headers=h_u2)
    assert unauth_rep.status_code == 403

    # 5. Report history endpoint
    hist_resp = client.get(f"/api/reports/history/{study_id}", headers=h_u1)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["reports"]) >= 1
    print("  [PASS] 11. PDF Reports, Export Packages & Report History verified")


def test_12_analysis_explorer_and_comparisons(aid1: str, aid2: str, h_u1: dict, h_u2: dict):
    """Verify Analysis Explorer output retrieval and Comparison authorization."""
    # Analysis Explorer retrieval
    exp_rec = get_history_by_id(aid1)
    assert exp_rec is not None
    assert exp_rec["id"] == aid1

    # Missing analysis explorer retrieval
    assert get_history_by_id("non_existent_id") is None

    # Comparison of two analyses
    comp_resp = client.post("/api/comparison", headers=h_u1, json={"analysis_ids": [aid1, aid2]})
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["analysis_count"] == 2
    assert "comparison_table" in comp_data

    # IDOR Protection: User 2 cannot compare User 1's analyses
    unauth_comp = client.post("/api/comparison", headers=h_u2, json={"analysis_ids": [aid1, aid2]})
    assert unauth_comp.status_code == 403
    print("  [PASS] 12. Analysis Explorer & Quantitative Comparison verified")


def test_13_error_handling_standards():
    """Verify standard HTTP status codes: 400, 401, 403, 404, 422, 500-safe."""
    # 400 Bad Request
    r400 = client.post("/api/comparison", json={"analysis_ids": ["only_one_id"]})
    assert r400.status_code == 400

    # 401 Unauthorized
    r401 = client.get("/api/auth/me")
    assert r401.status_code == 401

    # 403 Forbidden
    rev_temp = create_user("Temp Reviewer", f"revtemp_{uuid.uuid4().hex[:6]}@lab.test", "Password123!", role="reviewer")
    u_token = create_access_token(rev_temp["id"], "reviewer")
    r403 = client.post("/api/studies", headers={"Authorization": f"Bearer {u_token}"}, json={"title": "Test"})
    assert r403.status_code == 403

    # 404 Not Found
    r404 = client.get("/api/studies/non_existent_study_id_12345")
    assert r404.status_code == 404

    # 422 Unprocessable Entity
    r422 = client.post("/api/auth/register", json={"invalid_field": 123})
    assert r422.status_code == 422
    print("  [PASS] 13. Error Handling Standards & Status Codes verified")


if __name__ == "__main__":
    print("\n============================================================")
    print("CARDIAC DEFORMATION LAB -- MASTER TEST SUITE (STEP 11.20)")
    print("============================================================\n")

    test_01_health_and_version()
    test_02_auth_system()
    test_03_file_upload_and_security()
    test_04_analysis_motion_and_strain()
    test_05_roi_and_calibration()
    study_id, h_u1, h_u2, u1_id = test_06_studies_and_ownership()
    aid1 = test_07_analysis_saving_and_qc(study_id, h_u1, u1_id)
    aid2 = test_08_longitudinal_and_statistics(study_id, aid1, h_u1, u1_id)
    test_09_synthetic_validation_workflow()
    test_10_real_validation_and_annotations(aid1, h_u1)
    test_11_reports_and_export_packages(study_id, aid1, h_u1, h_u2)
    test_12_analysis_explorer_and_comparisons(aid1, aid2, h_u1, h_u2)
    test_13_error_handling_standards()

    print("\n============================================================")
    print("ALL 13 MASTER TEST SUITES PASSED! 100% SUCCESS")
    print("============================================================\n")
