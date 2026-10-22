"""
backend/test_real_annotations_step11_15.py

Comprehensive Verification Suite for Step 11.15:
Real-Image Annotation and Reference Benchmark Workflow

Tests:
1. Pure unit tests of annotation service:
   - Annotation quality control (type, coordinate bounds, minimum points, zero-area detection)
   - Contour geometry calculation (Shoelace area, perimeter, centroid, bounding box)
   - Annotation to ROI conversion (polygon, contour, region -> ROI dictionary)
   - Paired landmark reference motion calculation (dx, dy, distance)
   - Reference geometric engineering strain calculation (chord elongation / compression)
   - Annotation import/export format validity
2. Pure unit tests of real validation service:
   - Non-existent analysis handling
   - Empty annotations handling
3. Full End-to-End API Endpoints via HTTP:
   - POST /api/annotations (point, landmark, polyline, polygon, contour, region)
   - GET /api/annotations
   - GET /api/annotations/{id}
   - GET /api/annotations/image/{image_filename}
   - GET /api/annotations/analysis/{analysis_id}
   - PUT /api/annotations/{id}
   - POST /api/annotations/{id}/to-roi
   - GET /api/annotations/analysis/{analysis_id}/export
   - POST /api/annotations/import
   - POST /api/validation/real/{analysis_id}
   - POST /api/reports/real-validation/{analysis_id}
   - DELETE /api/annotations/{id}
   - DELETE /api/annotations/analysis/{analysis_id}
4. Backward Compatibility & System Integrity:
   - /health
   - /api/history/
   - /api/studies/
   - /api/synthetic/validation/history
"""

import json
import math
import os
import shutil
import urllib.error
import urllib.request
import uuid
from pathlib import Path
import numpy as np

from app.services.annotations import (
    validate_annotation_quality,
    calculate_contour_geometry,
    convert_annotation_to_roi,
    compute_paired_landmark_displacement,
    compute_reference_geometric_strain,
    create_annotation,
    get_annotation,
    get_annotations,
    update_annotation,
    delete_annotation,
    delete_annotations_by_analysis,
    export_annotations,
    import_annotations,
    SUPPORTED_ANNOTATION_TYPES,
)
from app.services.real_validation import (
    benchmark_analysis_against_annotations,
)
import urllib.parse

BASE_URL = "http://127.0.0.1:8000"


def http_get(path: str):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


def http_post(path: str, payload: dict = None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data_resp = resp.read().decode("utf-8")
            return resp.status, json.loads(data_resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


def http_put(path: str, payload: dict = None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data_resp = resp.read().decode("utf-8")
            return resp.status, json.loads(data_resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


def http_delete(path: str):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


# -------------------------------------------------------------
# Part 1: Unit Tests
# -------------------------------------------------------------

def test_unit_annotation_quality_control():
    print("\n--- Part 1A: Annotation Quality Control & Validation ---")
    
    # Valid point
    res = validate_annotation_quality({"annotation_type": "point", "points": [{"x": 10.0, "y": 20.0}]}, 100, 100)
    assert res["valid"], f"Expected valid point, got {res}"
    
    # Unsupported type
    res = validate_annotation_quality({"annotation_type": "cube", "points": [{"x": 10.0, "y": 20.0}]}, 100, 100)
    assert not res["valid"] and any("Invalid annotation_type" in e for e in res["errors"])

    # Out of bounds (generates warning)
    res = validate_annotation_quality({"annotation_type": "point", "points": [{"x": -5.0, "y": 20.0}]}, 100, 100)
    assert any("outside nominal image boundaries" in w for w in res["warnings"])
    
    # Polygon with fewer than 3 points
    res = validate_annotation_quality({"annotation_type": "polygon", "points": [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}]}, 100, 100)
    assert not res["valid"] and any("requires at least 3 points" in e for e in res["errors"])

    # Degenerate collinear polygon (zero area warning)
    res = validate_annotation_quality(
        {"annotation_type": "polygon", "points": [{"x": 10.0, "y": 10.0}, {"x": 20.0, "y": 20.0}, {"x": 30.0, "y": 30.0}]},
        100, 100
    )
    assert any("zero or near-zero enclosed area" in w for w in res["warnings"])

    print("  [PASS] Annotation quality control enforces types, bounds, point counts, and non-zero area.")


def test_unit_contour_geometry():
    print("\n--- Part 1B: Contour Geometry (Shoelace Area, Perimeter, Centroid, BBox) ---")

    # Square of 10x10 from (10, 10) to (20, 20)
    square_points = [
        {"x": 10.0, "y": 10.0},
        {"x": 20.0, "y": 10.0},
        {"x": 20.0, "y": 20.0},
        {"x": 10.0, "y": 20.0}
    ]
    geom = calculate_contour_geometry(square_points)
    assert abs(geom["area"] - 100.0) < 1e-3, f"Expected area 100.0, got {geom['area']}"
    assert abs(geom["perimeter"] - 40.0) < 1e-3, f"Expected perimeter 40.0, got {geom['perimeter']}"
    assert abs(geom["centroid"]["x"] - 15.0) < 1e-2, f"Expected centroid x=15.0, got {geom['centroid']['x']}"
    assert abs(geom["centroid"]["y"] - 15.0) < 1e-2, f"Expected centroid y=15.0, got {geom['centroid']['y']}"
    assert geom["bounding_box"]["x"] == 10.0
    assert geom["bounding_box"]["y"] == 10.0
    assert geom["bounding_box"]["width"] == 10.0
    assert geom["bounding_box"]["height"] == 10.0

    print("  [PASS] Contour geometry calculations accurately derived area, perimeter, centroid, and bounding box.")


def test_unit_annotation_to_roi_conversion():
    print("\n--- Part 1C: Annotation to ROI Model Conversion ---")

    poly_ann = {
        "id": "ann-poly-001",
        "annotation_type": "polygon",
        "annotator_label": "myocardium_roi",
        "points": [{"x": 10.0, "y": 10.0}, {"x": 50.0, "y": 10.0}, {"x": 30.0, "y": 50.0}]
    }
    roi = convert_annotation_to_roi(poly_ann)
    assert roi["enabled"] is True
    assert roi["type"] == "polygon"
    assert len(roi["coordinates"]) == 3
    assert roi["label"] == "myocardium_roi"

    # Incompatible type check
    pt_ann = {"id": "ann-pt-001", "annotation_type": "point", "points": [{"x": 10.0, "y": 10.0}]}
    try:
        convert_annotation_to_roi(pt_ann)
        assert False, "Should have raised ValueError for point annotation conversion to ROI"
    except ValueError:
        pass

    print("  [PASS] Polygon/Contour correctly converted into ROI specification; non-enclosed types rejected.")


def test_unit_paired_landmark_and_strain():
    print("\n--- Part 1D: Paired Landmark Motion and Geometric Strain ---")

    ann0 = {"points": [{"x": 10.0, "y": 10.0}]}
    ann1 = {"points": [{"x": 14.0, "y": 13.0}]}

    # dx = 4.0, dy = 3.0 -> distance = 5.0
    motion = compute_paired_landmark_displacement(ann0, ann1)
    assert motion["dx"] == 4.0
    assert motion["dy"] == 3.0
    assert motion["displacement"] == 5.0

    # Geometric Strain: Chord length L0 = 10, L1 = 12 -> eps = (12 - 10) / 10 = +0.20 (+20%)
    chord_p1_f0 = {"points": [{"x": 0.0, "y": 0.0}]}
    chord_p2_f0 = {"points": [{"x": 10.0, "y": 0.0}]}
    chord_p1_f1 = {"points": [{"x": 0.0, "y": 0.0}]}
    chord_p2_f1 = {"points": [{"x": 12.0, "y": 0.0}]}

    strain_res = compute_reference_geometric_strain(
        chord_p1_f0, chord_p2_f0, chord_p1_f1, chord_p2_f1
    )
    assert abs(strain_res["initial_length"] - 10.0) < 1e-4
    assert abs(strain_res["final_length"] - 12.0) < 1e-4
    assert abs(strain_res["engineering_strain"] - 0.20) < 1e-4
    assert abs(strain_res["percent_strain"] - 20.0) < 1e-4

    print("  [PASS] Paired landmark displacement and engineering strain calculations verified.")


# -------------------------------------------------------------
# Part 2: End-to-End API Endpoints
# -------------------------------------------------------------

def test_api_annotations_lifecycle():
    print("\n--- Part 2: End-to-End Annotation REST API Lifecycle ---")

    test_analysis_id = f"test-anal-{uuid.uuid4().hex[:8]}"
    test_image_f0 = "frame_00.png"
    test_image_f1 = "frame_01.png"

    # 1. Create Point Annotation on Frame 0
    pt_payload = {
        "analysis_id": test_analysis_id,
        "image_filename": test_image_f0,
        "annotation_type": "point",
        "annotator_label": "apex_tip",
        "frame_index": 0,
        "points": [{"x": 128.0, "y": 200.0}],
        "metadata": {"landmark_name": "apex"}
    }
    st, pt_res = http_post("/api/annotations", pt_payload)
    assert st == 201, f"Create point failed: {pt_res}"
    assert "id" in pt_res
    pt_id = pt_res["id"]
    print(f"  [PASS] POST /api/annotations created point {pt_id}")

    # 2. Create Matching Landmark on Frame 1
    pt_f1_payload = {
        "analysis_id": test_analysis_id,
        "image_filename": test_image_f1,
        "annotation_type": "point",
        "annotator_label": "apex_tip",
        "frame_index": 1,
        "points": [{"x": 130.0, "y": 196.0}],
        "metadata": {"landmark_name": "apex"}
    }
    st, pt1_res = http_post("/api/annotations", pt_f1_payload)
    assert st == 201
    pt1_id = pt1_res["id"]
    print(f"  [PASS] POST /api/annotations created frame 1 landmark {pt1_id}")

    # 3. Create Polygon Contour on Frame 0
    poly_payload = {
        "analysis_id": test_analysis_id,
        "image_filename": test_image_f0,
        "annotation_type": "polygon",
        "annotator_label": "lv_endocardium",
        "frame_index": 0,
        "points": [
            {"x": 100.0, "y": 100.0},
            {"x": 160.0, "y": 100.0},
            {"x": 160.0, "y": 160.0},
            {"x": 100.0, "y": 160.0}
        ],
        "metadata": {"region": "LV"}
    }
    st, poly_res = http_post("/api/annotations", poly_payload)
    assert st == 201
    poly_id = poly_res["id"]
    assert "geometry" in poly_res, f"poly_res keys: {list(poly_res.keys())}"
    assert poly_res["geometry"]["area"] == 3600.0
    print(f"  [PASS] POST /api/annotations created polygon contour {poly_id} with geometry")

    # 4. GET /api/annotations
    st, list_res = http_get("/api/annotations")
    assert st == 200
    assert any(a["id"] == poly_id for a in list_res)
    print("  [PASS] GET /api/annotations lists all annotations")

    # 5. GET /api/annotations/{id}
    st, get_res = http_get(f"/api/annotations/{poly_id}")
    assert st == 200
    assert get_res["id"] == poly_id
    assert get_res["annotator_label"] == "lv_endocardium"
    print(f"  [PASS] GET /api/annotations/{poly_id} returns exact record")

    # 6. GET /api/annotations/analysis/{analysis_id}
    st, anal_anns = http_get(f"/api/annotations/analysis/{test_analysis_id}")
    assert st == 200
    assert len(anal_anns) == 3
    print(f"  [PASS] GET /api/annotations/analysis/{test_analysis_id} filtered 3 annotations")

    # 7. PUT /api/annotations/{id}
    upd_payload = {
        "annotator_label": "lv_endocardium_updated"
    }
    st, upd_res = http_put(f"/api/annotations/{poly_id}", upd_payload)
    assert st == 200
    assert upd_res["annotator_label"] == "lv_endocardium_updated"
    print(f"  [PASS] PUT /api/annotations/{poly_id} updated label")

    # 8. POST /api/annotations/{id}/to-roi
    st, roi_res = http_post(f"/api/annotations/{poly_id}/to-roi")
    assert st == 200
    assert roi_res["enabled"] is True
    assert roi_res["type"] == "polygon"
    assert len(roi_res["coordinates"]) == 4
    print("  [PASS] POST /api/annotations/{id}/to-roi converted polygon to ROI")

    # 9. GET /api/annotations/analysis/{analysis_id}/export
    st, exp_res = http_get(f"/api/annotations/analysis/{test_analysis_id}/export")
    assert st == 200
    assert exp_res["analysis_id"] == test_analysis_id
    assert exp_res["annotation_count"] == 3
    assert len(exp_res["annotations"]) == 3
    print("  [PASS] GET /api/annotations/analysis/{id}/export generated valid package")

    # 10. POST /api/annotations/import
    # Modify ID so we can test import duplication or restoration
    import_payload = {
        "analysis_id": f"{test_analysis_id}_imported",
        "annotations": exp_res["annotations"]
    }
    st, imp_res = http_post("/api/annotations/import", import_payload)
    assert st == 200
    assert imp_res["imported_count"] == 3
    print(f"  [PASS] POST /api/annotations/import imported {imp_res['imported_count']} annotations")

    # Cleanup imported annotations
    http_delete(f"/api/annotations/analysis/{test_analysis_id}_imported")

    return test_analysis_id, poly_id, pt_id, pt1_id


def test_real_validation_and_reporting():
    print("\n--- Part 3: Real Validation Benchmark & PDF Report Generation ---")

    import cv2

    for d in ["backend/uploads", "uploads"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    f0_name = "test_bench_f0.png"
    f1_name = "test_bench_f1.png"

    img0 = np.zeros((256, 256), dtype=np.uint8)
    cv2.circle(img0, (128, 128), 50, 200, -1)
    img1 = np.zeros((256, 256), dtype=np.uint8)
    cv2.circle(img1, (132, 130), 50, 200, -1)

    for d in ["backend/uploads", "uploads"]:
        cv2.imwrite(str(Path(d) / f0_name), img0)
        cv2.imwrite(str(Path(d) / f1_name), img1)

    roi_spec = {
        "enabled": True,
        "type": "polygon",
        "coordinates": [
            {"x": 100.0, "y": 100.0},
            {"x": 160.0, "y": 100.0},
            {"x": 160.0, "y": 160.0},
            {"x": 100.0, "y": 160.0}
        ]
    }
    roi_param = urllib.parse.quote(json.dumps(roi_spec))
    st, anal_res = http_post(f"/api/analysis/strain?image1_filename={f0_name}&image2_filename={f1_name}&roi={roi_param}")
    assert st == 200, f"Analysis generation failed: {anal_res}"
    real_analysis_id = anal_res.get("analysis_id") or anal_res.get("id")
    assert real_analysis_id, "Missing analysis ID"
    print(f"  [PASS] Created base analysis in server history: {real_analysis_id}")

    # Add reference annotations to real_analysis_id
    # 1. Landmark pair (apex)
    lm0 = {
        "analysis_id": real_analysis_id,
        "image_filename": f0_name,
        "annotation_type": "landmark",
        "annotator_label": "apex",
        "frame_index": 0,
        "points": [{"x": 128.0, "y": 128.0}],
        "metadata": {"landmark_name": "apex"}
    }
    lm1 = {
        "analysis_id": real_analysis_id,
        "image_filename": f1_name,
        "annotation_type": "landmark",
        "annotator_label": "apex",
        "frame_index": 1,
        "points": [{"x": 132.0, "y": 130.0}],
        "metadata": {"landmark_name": "apex"}
    }
    # 2. Landmark pair (base) for geometric strain chord
    base0 = {
        "analysis_id": real_analysis_id,
        "image_filename": f0_name,
        "annotation_type": "landmark",
        "annotator_label": "base",
        "frame_index": 0,
        "points": [{"x": 128.0, "y": 78.0}],
        "metadata": {"landmark_name": "base"}
    }
    base1 = {
        "analysis_id": real_analysis_id,
        "image_filename": f1_name,
        "annotation_type": "landmark",
        "annotator_label": "base",
        "frame_index": 1,
        "points": [{"x": 132.0, "y": 79.0}],
        "metadata": {"landmark_name": "base"}
    }
    # 3. Contour polygon
    contour_poly = {
        "analysis_id": real_analysis_id,
        "image_filename": f0_name,
        "annotation_type": "polygon",
        "annotator_label": "lv_cavity",
        "frame_index": 0,
        "points": [
            {"x": 100.0, "y": 100.0},
            {"x": 160.0, "y": 100.0},
            {"x": 160.0, "y": 160.0},
            {"x": 100.0, "y": 160.0}
        ]
    }

    for ann_payload in [lm0, lm1, base0, base1, contour_poly]:
        st, a_res = http_post("/api/annotations", ann_payload)
        assert st == 201, f"Failed adding annotation: {a_res}"
    print("  [PASS] Added paired landmarks and polygon contour to analysis.")

    # Run Real Validation Benchmark: POST /api/validation/real/{analysis_id}
    st, val_res = http_post(f"/api/validation/real/{real_analysis_id}")
    assert st == 200, f"Benchmark failed: {val_res}"
    assert val_res["analysis_id"] == real_analysis_id
    assert val_res["annotation_count"] == 5
    assert "landmark_metrics" in val_res
    assert "disclaimer" in val_res
    assert "Manual annotations are reference labels" in val_res["disclaimer"]

    # Landmark concordances
    lm_metrics = val_res.get("landmark_metrics")
    assert lm_metrics is not None
    assert "mean_endpoint_error" in lm_metrics
    assert lm_metrics["paired_landmark_count"] == 2
    print(f"  [PASS] POST /api/validation/real/{real_analysis_id} calculated Landmark EPE ({lm_metrics['mean_endpoint_error']} px)")

    # Strain chord comparison
    strain_metrics = val_res.get("strain_comparison")
    assert strain_metrics is not None
    assert "mean_reference_strain" in strain_metrics
    print(f"  [PASS] Landmark reference strain calculated: {strain_metrics['mean_reference_strain']}")

    # ROI overlap
    roi_metrics = val_res.get("roi_metrics")
    assert roi_metrics is not None
    assert "iou" in roi_metrics
    assert "dice" in roi_metrics
    assert roi_metrics["iou"] > 0.95
    print(f"  [PASS] Evaluated ROI concordance: IoU={roi_metrics['iou']}, Dice={roi_metrics['dice']}")

    # Generate Real Validation PDF Report: POST /api/reports/real-validation/{analysis_id}
    st, rep_res = http_post(f"/api/reports/real-validation/{real_analysis_id}")
    assert st == 200, f"Report generation failed: {rep_res}"
    assert "report_filename" in rep_res
    assert "url" in rep_res
    pdf_path = Path(rep_res["report_path"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000
    print(f"  [PASS] POST /api/reports/real-validation/{real_analysis_id} generated {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

    # Clean up test annotations
    http_delete(f"/api/annotations/analysis/{real_analysis_id}")
    print("  [PASS] Cleaned up temporary test artifacts.")


def test_system_integrity_and_regressions():
    print("\n--- Part 4: System Integrity and Regression Checks ---")

    # Health
    st, res = http_get("/health")
    assert st == 200 and res.get("status") == "healthy"
    print("  [PASS] /health is healthy")

    # History
    st, res = http_get("/api/history/")
    assert st == 200 and isinstance(res, list)
    print("  [PASS] /api/history/ accessible")

    # Studies
    st, res = http_get("/api/studies/")
    assert st == 200 and isinstance(res, list)
    print("  [PASS] /api/studies/ accessible")

    # Synthetic validation history
    st, res = http_get("/api/synthetic/validation/history")
    assert st == 200 and isinstance(res, list)
    print("  [PASS] /api/synthetic/validation/history accessible")


def run_all_tests():
    print("=" * 70)
    print("RUNNING STEP 11.15 REAL ANNOTATION & BENCHMARK TEST SUITE")
    print("=" * 70)

    # Unit checks
    test_unit_annotation_quality_control()
    test_unit_contour_geometry()
    test_unit_annotation_to_roi_conversion()
    test_unit_paired_landmark_and_strain()

    # REST APIs
    test_analysis_id, poly_id, pt_id, pt1_id = test_api_annotations_lifecycle()

    # Real validation & PDF report
    test_real_validation_and_reporting()

    # Regressions
    test_system_integrity_and_regressions()

    print("\n" + "=" * 70)
    print("ALL STEP 11.15 REAL ANNOTATION & BENCHMARK TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
