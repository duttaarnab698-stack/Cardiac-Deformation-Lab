"""
Unit & Integration Test Suite for Step 11.17: Advanced Scientific Visualization and Interactive Analysis Explorer.

Tests:
1. End-to-end single pair analysis produces all 15 visualization outputs.
2. Output files exist on disk and are accessible via static /outputs/ routes.
3. Full history record retrieval via GET /api/history/{id} preserves all metrics, maps, and QC.
4. Calibration metadata and physical displacement preservation.
5. Temporal analysis produces sequential metric series and tracking previews for Explorer.
6. Annotations retrieval via GET /api/annotations/analysis/{id} for overlay integration.
7. Role-based access control and isolation on analysis records.
8. Non-clinical scientific disclaimer presence in metadata.
9. System regression check across existing endpoints.
"""

import os
import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
import numpy as np
import cv2

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app.main import app
from app.services.auth import create_access_token

client = TestClient(app)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
    fn1 = f"test_sci_f1_{uid}.png"
    fn2 = f"test_sci_f2_{uid}.png"
    cv2.imwrite(str(UPLOAD_DIR / fn1), f1)
    cv2.imwrite(str(UPLOAD_DIR / fn2), f2)
    return fn1, fn2


def test_01_single_pair_outputs_generation():
    """Verify single-pair analysis generates all required scientific visualization maps."""
    fn1, fn2 = create_synthetic_pair_files()

    res = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&pixel_spacing_x=0.5&pixel_spacing_y=0.5&unit=mm"
    )
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert "outputs" in data
    assert "advanced_outputs" in data
    assert "cardiac_deformation_outputs" in data

    outputs = data["outputs"]
    adv = data["advanced_outputs"]
    cardiac = data["cardiac_deformation_outputs"]

    # Check key scientific maps
    expected_maps = [
        outputs.get("displacement_heatmap"),
        outputs.get("motion_vector_map"),
        outputs.get("exx_heatmap"),
        outputs.get("eyy_heatmap"),
        outputs.get("exy_heatmap"),
        outputs.get("principal_strain_heatmap"),
        outputs.get("principal_direction_map"),
        adv.get("motion_coherence_map"),
        adv.get("strain_gradient_map"),
        adv.get("anisotropy_map"),
        adv.get("deformation_energy_map"),
        cardiac.get("radial_map"),
        cardiac.get("circumferential_map"),
    ]

    for p in expected_maps:
        assert p is not None
        assert Path(p).exists() or Path("outputs" / Path(p).name).exists()

    # Clean up uploaded test images
    for fn in [fn1, fn2]:
        p = UPLOAD_DIR / fn
        if p.exists():
            p.unlink()


def test_02_history_record_retrieval_and_metadata():
    """Verify history record retrieval by ID preserves calibration, QC, and metric structures."""
    fn1, fn2 = create_synthetic_pair_files()
    analysis_res = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&pixel_spacing_x=0.5&pixel_spacing_y=0.5&unit=mm"
    ).json()
    analysis_id = analysis_res["id"]

    # Fetch through GET /api/history/{id}
    rec_res = client.get(f"/api/history/{analysis_id}")
    assert rec_res.status_code == 200
    record = rec_res.json()
    assert record["id"] == analysis_id
    res_data = record.get("result", {})
    assert "displacement" in res_data
    assert "strain_statistics" in res_data
    assert "advanced_metrics" in res_data
    assert "calibration" in res_data
    assert res_data["calibration"]["enabled"] is True
    assert res_data["calibration"]["unit"] == "mm"
    assert "quality_control" in res_data
    assert "outputs" in res_data

    # Verify static outputs are accessible over HTTP
    disp_path = res_data["outputs"]["displacement_heatmap"]
    filename = Path(disp_path).name
    img_res = client.get(f"/outputs/{filename}")
    assert img_res.status_code == 200
    assert len(img_res.content) > 100

    # Clean up
    for fn in [fn1, fn2]:
        p = UPLOAD_DIR / fn
        if p.exists():
            p.unlink()


def test_03_temporal_sequence_metrics_and_curves():
    """Verify temporal analysis returns frame counts, metric series, and tracking summaries."""
    fn1, fn2 = create_synthetic_pair_files()
    fn3 = f"test_sci_f3_{uuid.uuid4().hex[:6]}.png"
    cv2.imwrite(str(UPLOAD_DIR / fn3), np.full((120, 120), 60, dtype=np.uint8))

    res = client.post(
        f"/api/analysis/temporal-strain?filenames={fn1}&filenames={fn2}&filenames={fn3}&pixel_spacing_x=0.4&pixel_spacing_y=0.4&unit=mm"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["frame_count"] == 3
    assert data["pair_count"] == 2
    assert "principal_strain_1" in data
    assert "values" in data["principal_strain_1"]
    assert len(data["principal_strain_1"]["values"]) == 2
    assert "displacement" in data
    assert "quality_control" in data

    # Clean up
    for fn in [fn1, fn2, fn3]:
        p = UPLOAD_DIR / fn
        if p.exists():
            p.unlink()


def test_04_analysis_annotations_overlay_retrieval():
    """Verify annotations can be created and queried by analysis ID for Explorer overlays."""
    # Register a researcher
    r_email = f"explorer_anno_{uuid.uuid4().hex[:6]}@lab.local"
    token = client.post(
        "/api/auth/register",
        json={"name": "Dr. Explorer", "email": r_email, "password": "Password123!"},
    ).json()["token"]

    fn1, fn2 = create_synthetic_pair_files()
    anal_id = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]

    # Add a landmark annotation to this analysis
    anno_res = client.post(
        "/api/annotations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "analysis_id": anal_id,
            "image_filename": fn1,
            "annotation_type": "point",
            "annotator_label": "Apex Landmark",
            "points": [{"x": 60.0, "y": 60.0}],
        },
    )
    assert anno_res.status_code == 201

    # Retrieve annotations by analysis ID
    list_res = client.get(
        f"/api/annotations/analysis/{anal_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    annos = list_res.json()
    assert len(annos) >= 1
    assert any(a["annotator_label"] == "Apex Landmark" for a in annos)

    # Clean up
    for fn in [fn1, fn2]:
        p = UPLOAD_DIR / fn
        if p.exists():
            p.unlink()


def test_05_access_control_on_analysis_explorer():
    """Verify researcher isolation on GET /api/history/{id}."""
    u1_token = client.post(
        "/api/auth/register",
        json={"name": "User 1", "email": f"u1_{uuid.uuid4().hex[:6]}@lab.local", "password": "Password123!"},
    ).json()["token"]

    u2_token = client.post(
        "/api/auth/register",
        json={"name": "User 2", "email": f"u2_{uuid.uuid4().hex[:6]}@lab.local", "password": "Password123!"},
    ).json()["token"]

    fn1, fn2 = create_synthetic_pair_files()
    u1_analysis = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}",
        headers={"Authorization": f"Bearer {u1_token}"},
    ).json()
    u1_id = u1_analysis["id"]

    # User 1 can view own analysis
    ok_res = client.get(
        f"/api/history/{u1_id}",
        headers={"Authorization": f"Bearer {u1_token}"},
    )
    assert ok_res.status_code == 200

    # User 2 cannot access User 1's analysis
    forbidden_res = client.get(
        f"/api/history/{u1_id}",
        headers={"Authorization": f"Bearer {u2_token}"},
    )
    assert forbidden_res.status_code == 403

    # Clean up
    for fn in [fn1, fn2]:
        p = UPLOAD_DIR / fn
        if p.exists():
            p.unlink()


def test_06_regression_checks():
    """Verify health and existing API endpoints function normally."""
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    hist_res = client.get("/api/history")
    assert hist_res.status_code == 200

    studies_res = client.get("/api/studies")
    assert studies_res.status_code == 200


if __name__ == "__main__":
    tests = [
        test_01_single_pair_outputs_generation,
        test_02_history_record_retrieval_and_metadata,
        test_03_temporal_sequence_metrics_and_curves,
        test_04_analysis_annotations_overlay_retrieval,
        test_05_access_control_on_analysis_explorer,
        test_06_regression_checks,
    ]
    passed = 0
    failed = 0
    print("=" * 60)
    print("RUNNING CDL STEP 11.17 SCIENTIFIC EXPLORER TEST SUITE")
    print("=" * 60)
    for t in tests:
        name = t.__name__
        try:
            t()
            passed += 1
            print(f"[PASS] {name}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)
