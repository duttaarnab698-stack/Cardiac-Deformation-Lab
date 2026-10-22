"""
backend/test_roi_verification.py

Comprehensive Verification Test Suite for Step 11.8:
Region of Interest (ROI) and Cardiac Region Analysis
Uses standard urllib against running Uvicorn server on http://127.0.0.1:8000.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
import numpy as np
import cv2

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.services.roi import (
    create_rectangular_mask,
    create_elliptical_mask,
    create_polygon_mask,
    validate_and_create_roi_mask,
    calculate_masked_displacement_statistics,
    calculate_masked_strain_statistics,
    calculate_masked_advanced_metrics,
    calculate_masked_cardiac_deformation
)

BASE_URL = "http://127.0.0.1:8000"

class TestClient:
    def get(self, path):
        req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def post(self, path, payload=None):
        req = urllib.request.Request(f"{BASE_URL}{path}", method="POST")
        if payload is not None:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(payload).encode("utf-8")
        else:
            req.data = b""
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

client = TestClient()


def create_synthetic_frames():
    """Create three 120x120 synthetic cardiac phantom frames."""
    h, w = 120, 120
    frame1 = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(frame1, (60, 60), 35, 180, -1)
    cv2.circle(frame1, (60, 60), 20, 40, -1)

    frame2 = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(frame2, (62, 59), 32, 180, -1)
    cv2.circle(frame2, (62, 59), 17, 40, -1)

    frame3 = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(frame3, (63, 58), 30, 180, -1)
    cv2.circle(frame3, (63, 58), 15, 40, -1)

    upload_dir = backend_dir / "uploads"
    upload_dir.mkdir(exist_ok=True)

    fn1 = "test_roi_f1.png"
    fn2 = "test_roi_f2.png"
    fn3 = "test_roi_f3.png"

    cv2.imwrite(str(upload_dir / fn1), frame1)
    cv2.imwrite(str(upload_dir / fn2), frame2)
    cv2.imwrite(str(upload_dir / fn3), frame3)

    return fn1, fn2, fn3


def run_tests():
    print("=" * 70)
    print("STEP 11.8: REGION OF INTEREST (ROI) VERIFICATION SUITE")
    print("=" * 70)

    fn1, fn2, fn3 = create_synthetic_frames()

    # ─────────────────────────────────────────────────────────────
    # UNIT TESTS: MASK CREATION & GEOMETRY
    # ─────────────────────────────────────────────────────────────
    print("\n--- [UNIT TEST 1] Rectangular Mask Creation ---")
    rect_mask = create_rectangular_mask(100, 100, 10, 20, 30, 40)
    assert rect_mask.shape == (100, 100), "Shape mismatch"
    assert np.count_nonzero(rect_mask) == 30 * 40, f"Expected 1200 pixels, got {np.count_nonzero(rect_mask)}"
    print("[PASS] Rectangular mask created with exact dimensions.")

    print("\n--- [UNIT TEST 2] Elliptical Mask Creation ---")
    ellipse_mask = create_elliptical_mask(100, 100, 50, 50, 20, 15)
    assert ellipse_mask.shape == (100, 100), "Shape mismatch"
    assert np.count_nonzero(ellipse_mask) > 0, "Ellipse mask must have active pixels"
    print(f"[PASS] Elliptical mask created with {np.count_nonzero(ellipse_mask)} active pixels.")

    print("\n--- [UNIT TEST 3] Polygon Mask Creation ---")
    poly_pts = [{"x": 20, "y": 20}, {"x": 60, "y": 20}, {"x": 40, "y": 60}]
    poly_mask = create_polygon_mask(100, 100, poly_pts)
    assert poly_mask.shape == (100, 100), "Shape mismatch"
    assert np.count_nonzero(poly_mask) > 0, "Polygon mask must have active pixels"
    print(f"[PASS] Triangular polygon mask created with {np.count_nonzero(poly_mask)} active pixels.")

    print("\n--- [UNIT TEST 4] Boundary Clipping & Out-of-Bounds Validation ---")
    clipped_mask = create_rectangular_mask(100, 100, 80, 80, 50, 50)
    assert np.count_nonzero(clipped_mask) == 20 * 20, f"Expected 400 clipped pixels, got {np.count_nonzero(clipped_mask)}"
    print("[PASS] Partially out-of-bounds geometry clipped properly.")

    valid, err, _ = validate_and_create_roi_mask(
        {"enabled": True, "type": "rectangle", "coordinates": {"x": 200, "y": 200, "width": 50, "height": 50}},
        100, 100
    )
    assert not valid, "Should reject rectangle completely outside image bounds"
    print(f"[PASS] Out-of-bounds rejected correctly: '{err}'")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST A: Full Image Analysis (Backward Compatibility)
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST A] Full Image Analysis (No ROI) ---")
    status_a, data_a = client.post(f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}")
    assert status_a == 200, f"Failed: {data_a}"
    assert data_a["analysis_scope"]["mode"] == "full_image"
    assert data_a["roi_metrics"] is None
    assert "displacement" in data_a
    assert "strain_statistics" in data_a
    assert "cardiac_deformation_fingerprint" in data_a
    print("[PASS] Full-image analysis preserved with zero regressions.")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST B: Rectangular ROI Analysis
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST B] Single-Pair Analysis with Rectangular ROI ---")
    roi_b = {
        "enabled": True,
        "type": "rectangle",
        "coordinates": {"x": 40, "y": 40, "width": 40, "height": 40}
    }
    encoded_b = urllib.parse.quote(json.dumps(roi_b))
    status_b, data_b = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={encoded_b}"
    )
    assert status_b == 200, f"Failed: {data_b}"
    assert data_b["analysis_scope"]["mode"] == "roi"
    assert data_b["analysis_scope"]["roi_type"] == "rectangle"
    assert data_b["roi_metrics"] is not None
    assert data_b["roi_metrics"]["pixel_count"] == 40 * 40
    assert "roi_overlay" in data_b["outputs"]
    overlay_path = Path(data_b["outputs"]["roi_overlay"])
    if not overlay_path.is_absolute():
        overlay_path = backend_dir / overlay_path
    assert overlay_path.exists(), f"ROI overlay file not found: {overlay_path}"
    assert data_b["roi_metrics"]["fingerprint"] is not None
    assert data_b["full_image_metrics"] is not None
    print(f"[PASS] Rectangular ROI analysis computed successfully (ROI pixels: {data_b['roi_metrics']['pixel_count']}).")
    print(f"  Full mean disp: {data_b['full_image_metrics']['displacement']['mean_displacement']:.4f} px")
    print(f"  ROI mean disp:  {data_b['roi_metrics']['displacement']['mean_displacement']:.4f} px")
    print(f"  ROI overlay image saved at: {data_b['outputs']['roi_overlay']}")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST C: Elliptical ROI Analysis
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST C] Single-Pair Analysis with Elliptical ROI ---")
    roi_c = {
        "enabled": True,
        "type": "ellipse",
        "coordinates": {"center_x": 60, "center_y": 60, "radius_x": 25, "radius_y": 20}
    }
    encoded_c = urllib.parse.quote(json.dumps(roi_c))
    status_c, data_c = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={encoded_c}"
    )
    assert status_c == 200, f"Failed: {data_c}"
    assert data_c["analysis_scope"]["roi_type"] == "ellipse"
    assert data_c["roi_metrics"]["pixel_count"] > 0
    print(f"[PASS] Elliptical ROI analysis passed with {data_c['roi_metrics']['pixel_count']} active pixels.")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST D: Polygonal ROI Analysis
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST D] Single-Pair Analysis with Polygonal ROI ---")
    roi_d = {
        "enabled": True,
        "type": "polygon",
        "coordinates": {"points": [{"x": 30, "y": 30}, {"x": 90, "y": 30}, {"x": 60, "y": 90}]}
    }
    encoded_d = urllib.parse.quote(json.dumps(roi_d))
    status_d, data_d = client.post(
        f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={encoded_d}"
    )
    assert status_d == 200, f"Failed: {data_d}"
    assert data_d["analysis_scope"]["roi_type"] == "polygon"
    assert data_d["roi_metrics"]["pixel_count"] > 0
    print(f"[PASS] Polygonal ROI analysis passed with {data_d['roi_metrics']['pixel_count']} active pixels.")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST E: History Persistence of ROI Data
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST E] History Persistence of ROI Records ---")
    h_status, records = client.get("/api/history")
    assert h_status == 200
    assert len(records) > 0

    latest = records[0]
    assert "roi" in latest["summary"]
    assert latest["summary"]["roi"]["enabled"] is True
    assert latest["summary"]["roi"]["type"] == "polygon"
    print(f"[PASS] History successfully saved ROI record: {latest['summary']['roi']}")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST F: PDF Report Generation with ROI
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST F] PDF Report Generation with ROI Section ---")
    rep_status, rep_data = client.post(f"/api/reports/{latest['id']}")
    assert rep_status == 200, f"Report failed: {rep_data}"
    rep_path = Path(rep_data["report_path"])
    if not rep_path.is_absolute():
        rep_path = backend_dir / rep_path
    assert rep_path.exists(), f"PDF report not found: {rep_path}"
    assert str(rep_path).endswith(".pdf")
    print(f"[PASS] PDF report generated with ROI metadata at: {rep_data['report_path']}")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST G: Temporal Sequence Analysis with ROI
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST G] Temporal Sequence Analysis with ROI ---")
    roi_g = {
        "enabled": True,
        "type": "rectangle",
        "coordinates": {"x": 35, "y": 35, "width": 50, "height": 50}
    }
    encoded_g = urllib.parse.quote(json.dumps(roi_g))
    temp_path = f"/api/analysis/temporal-strain?filenames={fn1}&filenames={fn2}&filenames={fn3}&roi={encoded_g}"
    status_g, data_g = client.post(temp_path)
    assert status_g == 200, f"Temporal failed: {data_g}"
    assert data_g["analysis_scope"]["mode"] == "roi"
    assert data_g["roi_metrics"] is not None
    assert "principal_strain_1" in data_g["roi_metrics"]
    assert "displacement" in data_g["roi_metrics"]
    assert data_g["roi_fingerprint"] is not None
    print(f"[PASS] Temporal sequence with ROI completed across {data_g['frame_count']} frames.")
    print(f"  Temporal ROI mean principal strain: {data_g['roi_metrics']['principal_strain_1']['summary']['mean']:.4f}")
    print(f"  Temporal Full mean principal strain: {data_g['full_image_metrics']['principal_strain_1']['summary']['mean']:.4f}")

    # ─────────────────────────────────────────────────────────────
    # INTEGRATION TEST H: Validation Error Handling
    # ─────────────────────────────────────────────────────────────
    print("\n--- [TEST H] Validation Error Handling ---")
    # Bad ROI type
    bad_type = {"enabled": True, "type": "triangle", "coordinates": {}}
    enc_bad_type = urllib.parse.quote(json.dumps(bad_type))
    h1_status, _ = client.post(f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={enc_bad_type}")
    assert h1_status == 400
    print("[PASS] Rejected unsupported ROI type with HTTP 400.")

    # Missing coordinates
    bad_coords = {"enabled": True, "type": "rectangle"}
    enc_bad_coords = urllib.parse.quote(json.dumps(bad_coords))
    h2_status, _ = client.post(f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={enc_bad_coords}")
    assert h2_status == 400
    print("[PASS] Rejected missing coordinates with HTTP 400.")

    # Negative dimensions
    neg_dim = {"enabled": True, "type": "rectangle", "coordinates": {"x": 10, "y": 10, "width": -5, "height": 20}}
    enc_neg_dim = urllib.parse.quote(json.dumps(neg_dim))
    h3_status, _ = client.post(f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={enc_neg_dim}")
    assert h3_status == 400
    print("[PASS] Rejected negative dimensions with HTTP 400.")

    # Less than 3 points for polygon
    short_poly = {"enabled": True, "type": "polygon", "coordinates": {"points": [{"x": 10, "y": 10}, {"x": 20, "y": 20}]}}
    enc_short_poly = urllib.parse.quote(json.dumps(short_poly))
    h4_status, _ = client.post(f"/api/analysis/strain?image1_filename={fn1}&image2_filename={fn2}&roi={enc_short_poly}")
    assert h4_status == 400
    print("[PASS] Rejected polygon with < 3 points with HTTP 400.")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! (Step 11.8 complete)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
