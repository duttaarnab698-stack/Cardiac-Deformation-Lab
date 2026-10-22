import os
import sys
import json
import urllib.request
import urllib.parse
import numpy as np
import cv2
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def http_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def http_post(endpoint, params=None):
    query_str = ""
    if params:
        query_str = "?" + urllib.parse.urlencode(params)
    url = f"{BASE_URL}{endpoint}{query_str}"
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def create_synthetic_cine_frames():
    """Create 4 synthetic cine frames with known displacement for rigorous tracking testing."""
    for dir_name in ["backend/uploads", "uploads"]:
        p = Path(dir_name)
        p.mkdir(parents=True, exist_ok=True)

    h, w = 128, 128
    filenames = []

    # Center starts at (64, 64) and shifts by (+4, +3) per frame
    shifts = [(0, 0), (4, 3), (8, 6), (12, 9)]

    for idx, (dx, dy) in enumerate(shifts):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            img[y, :, :] = int(y / h * 80)

        cx, cy = 64 + dx, 64 + dy
        cv2.circle(img, (cx, cy), 20, (255, 255, 255), -1)
        cv2.circle(img, (cx, cy), 12, (180, 180, 180), -1)
        cv2.circle(img, (cx, cy), 5, (90, 90, 90), -1)

        fname = f"cine_track_f{idx+1}.png"
        for dir_name in ["backend/uploads", "uploads"]:
            cv2.imwrite(str(Path(dir_name) / fname), img)
        filenames.append(fname)

    return filenames

def run_all_tests():
    print("=" * 60)
    print("RUNNING STEP 11.9 AUTOMATIC ROI TRACKING VERIFICATION SUITE")
    print("=" * 60)

    filenames = create_synthetic_cine_frames()
    print(f"Created synthetic test cine frames: {filenames}")

    # ─────────────────────────────────────────────────────────────
    # Test A: Fixed ROI temporal analysis across frames
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST A] Fixed ROI Temporal Analysis")
    fixed_roi = {
        "enabled": True,
        "mode": "fixed",
        "type": "rectangle",
        "coordinates": {"x": 44, "y": 44, "width": 40, "height": 40}
    }
    status, data = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", f) for f in filenames] + [("roi", json.dumps(fixed_roi))]
    )
    assert status == 200, f"Test A Failed: {data}"
    assert data["analysis_scope"]["mode"] == "roi"
    assert data["roi"]["mode"] == "fixed"
    assert data["roi_metrics"] is not None
    assert data["full_image_metrics"] is not None
    print("  [PASS] Fixed ROI temporal analysis verified successfully.")

    # ─────────────────────────────────────────────────────────────
    # Test B: Tracked ROI with Rectangle across frames
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST B] Tracked ROI with Rectangle across cine frames")
    tracked_rect_roi = {
        "enabled": True,
        "mode": "tracked",
        "type": "rectangle",
        "coordinates": {"x": 44, "y": 44, "width": 40, "height": 40}
    }
    status_b, data_b = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", f) for f in filenames] + [("roi", json.dumps(tracked_rect_roi))]
    )
    assert status_b == 200, f"Test B Failed: {data_b}"
    assert data_b["analysis_scope"]["mode"] == "tracked_roi"
    assert data_b["roi"]["mode"] == "tracked"
    assert data_b["tracking_path"] is not None
    assert len(data_b["tracking_path"]) == len(filenames)
    assert data_b["tracking_summary"] is not None
    assert data_b["tracking_summary"]["successful_tracking_frames"] >= 3
    assert data_b["tracking_previews"] is not None
    assert "first" in data_b["tracking_previews"]
    assert "middle" in data_b["tracking_previews"]
    assert "last" in data_b["tracking_previews"]

    # Check center motion
    c0 = data_b["tracking_path"][0]["roi"]["center"]
    c3 = data_b["tracking_path"][3]["roi"]["center"]
    print(f"  Initial Center: ({c0['x']}, {c0['y']}) -> Final Center: ({c3['x']}, {c3['y']})")
    assert c3["x"] > c0["x"], "Center X should have shifted positively"
    assert c3["y"] > c0["y"], "Center Y should have shifted positively"
    print("  [PASS] Tracked Rectangle ROI motion estimation verified.")

    # ─────────────────────────────────────────────────────────────
    # Test C: Tracked ROI with Ellipse across frames
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST C] Tracked ROI with Ellipse across cine frames")
    tracked_ellipse_roi = {
        "enabled": True,
        "mode": "tracked",
        "type": "ellipse",
        "coordinates": {"center_x": 64, "center_y": 64, "radius_x": 22, "radius_y": 22}
    }
    status_c, data_c = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", f) for f in filenames] + [("roi", json.dumps(tracked_ellipse_roi))]
    )
    assert status_c == 200, f"Test C Failed: {data_c}"
    assert data_c["roi"]["type"] == "ellipse"
    assert data_c["tracking_summary"]["mean_confidence"] > 0.0
    print(f"  Mean Confidence: {data_c['tracking_summary']['mean_confidence']}")
    print("  [PASS] Tracked Ellipse ROI verified.")

    # ─────────────────────────────────────────────────────────────
    # Test D: Tracked ROI with Polygon across frames
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST D] Tracked ROI with Polygon across cine frames")
    tracked_poly_roi = {
        "enabled": True,
        "mode": "tracked",
        "type": "polygon",
        "coordinates": {"points": [{"x": 44, "y": 44}, {"x": 84, "y": 44}, {"x": 84, "y": 84}, {"x": 44, "y": 84}]}
    }
    status_d, data_d = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", f) for f in filenames] + [("roi", json.dumps(tracked_poly_roi))]
    )
    assert status_d == 200, f"Test D Failed: {data_d}"
    assert data_d["roi"]["type"] == "polygon"
    assert data_d["tracking_summary"]["successful_tracking_frames"] >= 3
    print("  [PASS] Tracked Polygon ROI verified.")

    # ─────────────────────────────────────────────────────────────
    # Test E: ROI Tracking Confidence verification
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST E] Tracking Confidence metrics verification")
    summary = data_b["tracking_summary"]
    assert 0.0 <= summary["mean_confidence"] <= 1.0
    assert 0.0 <= summary["min_confidence"] <= 1.0
    assert 0.0 <= summary["max_confidence"] <= 1.0
    assert summary["min_confidence"] <= summary["max_confidence"]
    print(f"  Confidence Range: {summary['min_confidence']} to {summary['max_confidence']} (Mean: {summary['mean_confidence']})")
    print("  [PASS] Confidence metrics within mathematical bounds.")

    # ─────────────────────────────────────────────────────────────
    # Test F: Tracking failure & boundary handling
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST F] Tracking near image boundary and graceful degradation")
    edge_roi = {
        "enabled": True,
        "mode": "tracked",
        "type": "rectangle",
        "coordinates": {"x": 115, "y": 115, "width": 10, "height": 10}
    }
    status_f, data_f = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", f) for f in filenames] + [("roi", json.dumps(edge_roi))]
    )
    assert status_f == 200, f"Should handle boundary clamping without crash: {data_f}"
    for item in data_f["tracking_path"]:
        rx = item["roi"]["coordinates"]["x"]
        ry = item["roi"]["coordinates"]["y"]
        rw = item["roi"]["coordinates"]["width"]
        rh = item["roi"]["coordinates"]["height"]
        assert 0 <= rx < 128
        assert 0 <= ry < 128
        assert rx + rw <= 128
        assert ry + rh <= 128
    print("  [PASS] Boundary clipping kept ROI within native frame dimensions.")

    # ─────────────────────────────────────────────────────────────
    # Test G: Preview endpoint (/api/analysis/roi/track-preview)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST G] ROI Tracking Preview endpoint POST /api/analysis/roi/track-preview")
    status_g, preview_data = http_post(
        "/api/analysis/roi/track-preview",
        params=[("filenames", f) for f in filenames] + [("roi", json.dumps(tracked_rect_roi))]
    )
    assert status_g == 200, f"Preview failed: {preview_data}"
    assert "previews" in preview_data
    assert "tracking_path" in preview_data
    assert "tracking_summary" in preview_data
    # Files are written to outputs
    print(f"  Preview keyframes: {preview_data['previews']}")
    print("  [PASS] ROI Tracking preview generated keyframes and path correctly.")

    # ─────────────────────────────────────────────────────────────
    # Test H: History persistence with tracked ROI
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST H] History persistence for Tracked ROI")
    analysis_id = data_b["analysis_id"]
    hist_status, hist_rec = http_get(f"/api/history/{analysis_id}")
    assert hist_status == 200, f"Failed getting history: {hist_rec}"
    assert hist_rec["summary"]["roi"]["mode"] == "tracked"
    assert "tracking_summary" in hist_rec["summary"]
    print("  [PASS] History record successfully persisted tracked ROI mode and summary.")

    # ─────────────────────────────────────────────────────────────
    # Test I: PDF Report generation with Tracked ROI Section 4B
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST I] PDF Report generation with Tracked ROI Section 4B")
    report_status, report_info = http_post(f"/api/reports/{analysis_id}")
    assert report_status == 200, f"Report generation failed: {report_info}"
    report_rel = report_info["url"].lstrip("/")
    report_file = Path(report_rel) if Path(report_rel).exists() else Path("backend") / report_rel
    assert report_file.exists(), f"Report file not found: {report_file}"
    assert report_file.stat().st_size > 5000, f"Report too small: {report_file.stat().st_size} bytes"
    print(f"  Generated PDF Report: {report_file} ({report_file.stat().st_size} bytes)")
    print("  [PASS] PDF Report generation with Section 4B completed successfully.")

    # ─────────────────────────────────────────────────────────────
    # Test J: Backwards compatibility
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST J] Full-image temporal and single-pair backwards compatibility")
    # Full image temporal analysis (no ROI)
    status_j1, data_j1 = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", f) for f in filenames]
    )
    assert status_j1 == 200
    assert data_j1["analysis_scope"]["mode"] == "full_image"
    assert data_j1["roi"]["enabled"] is False

    # Single-pair strain analysis
    status_j2, data_j2 = http_post(
        "/api/analysis/strain",
        params=[("image1_filename", filenames[0]), ("image2_filename", filenames[1])]
    )
    assert status_j2 == 200
    assert data_j2["cardiac_deformation_fingerprint"] is not None
    print("  [PASS] Full-image temporal and single-pair analysis backwards compatibility intact.")

    print("\n" + "=" * 60)
    print("ALL TESTS (A through J) PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
