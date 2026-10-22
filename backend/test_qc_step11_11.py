import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path
import numpy as np
import cv2

BASE_URL = "http://127.0.0.1:8000"


def http_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def http_post(endpoint, params=None, json_body=None):
    query_str = ""
    if params:
        query_str = "?" + urllib.parse.urlencode(params)
    url = f"{BASE_URL}{endpoint}{query_str}"
    data = json.dumps(json_body).encode() if json_body is not None else b""
    headers = {"Content-Type": "application/json"} if json_body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def setup_qc_test_images():
    for d in ["backend/uploads", "uploads"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    h, w = 128, 128

    # 1. Good quality pair (sharp circle with gradient, standard 128x128)
    good1 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        good1[y, :, :] = int(y / h * 120)
    cv2.circle(good1, (64, 64), 22, (255, 255, 255), -1)
    cv2.circle(good1, (64, 64), 12, (180, 180, 180), -1)

    good2 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        good2[y, :, :] = int(y / h * 120)
    cv2.circle(good2, (67, 66), 24, (255, 255, 255), -1)
    cv2.circle(good2, (67, 66), 11, (180, 180, 180), -1)

    # 2. Low contrast image (narrow intensity distribution std < 8)
    low_contrast = np.full((h, w, 3), 100, dtype=np.uint8)
    cv2.circle(low_contrast, (64, 64), 20, (108, 108, 108), -1)

    # 3. Blurred image (heavily blurred with large Gaussian kernel)
    blurred = cv2.GaussianBlur(good1, (25, 25), 10.0)

    # 4. Differently sized image (96x96 instead of 128x128)
    diff_dim = np.zeros((96, 96, 3), dtype=np.uint8)
    cv2.circle(diff_dim, (48, 48), 18, (255, 255, 255), -1)

    files = [
        ("qc_good_1.png", good1),
        ("qc_good_2.png", good2),
        ("qc_low_contrast.png", low_contrast),
        ("qc_blurred.png", blurred),
        ("qc_diff_dim.png", diff_dim),
    ]

    for fname, img in files:
        for d in ["backend/uploads", "uploads"]:
            cv2.imwrite(str(Path(d) / fname), img)

    return {name: name for name, _ in files}


def run_all_qc_tests():
    print("=" * 70)
    print("RUNNING STEP 11.11 AUTOMATED QUALITY CONTROL VERIFICATION SUITE")
    print("=" * 70)

    img_names = setup_qc_test_images()
    g1 = img_names["qc_good_1.png"]
    g2 = img_names["qc_good_2.png"]
    low_c = img_names["qc_low_contrast.png"]
    blur = img_names["qc_blurred.png"]
    diff_dim = img_names["qc_diff_dim.png"]

    # ─────────────────────────────────────────────────────────────
    # TEST A — Good-quality image pair
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST A] Good-Quality Image Pair")
    status, a_good = http_post("/api/analysis/strain", params={"image1_filename": g1, "image2_filename": g2})
    assert status == 200, f"Test A Failed to run strain analysis: {a_good}"
    good_id = a_good.get("analysis_id") or a_good.get("id")
    assert "quality_control" in a_good, "quality_control field missing from analysis result"
    qc_good = a_good["quality_control"]
    assert qc_good is not None, "quality_control is None"
    assert "score" in qc_good and "level" in qc_good
    assert "components" in qc_good
    assert qc_good["score"] >= 75, f"Expected good score >= 75, got {qc_good['score']}"
    assert qc_good["level"] in ("High", "Moderate")
    print(f"  [PASS] Quality Control generated: Score {qc_good['score']}/100 ({qc_good['level']}).")

    # ─────────────────────────────────────────────────────────────
    # TEST B — Low-contrast image (Verify warning)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST B] Low-Contrast Image Quality Check")
    status, a_lc = http_post("/api/analysis/strain", params={"image1_filename": low_c, "image2_filename": g2})
    assert status == 200, f"Test B failed: {a_lc}"
    qc_lc = a_lc.get("quality_control") or {}
    all_warnings_lc = " ".join(qc_lc.get("warnings", [])).lower()
    assert "contrast is low" in all_warnings_lc or "contrast" in all_warnings_lc, \
        f"Expected low-contrast warning, got warnings: {qc_lc.get('warnings')}"
    print(f"  [PASS] Correctly flagged low-contrast warning: {qc_lc.get('warnings')}")

    # ─────────────────────────────────────────────────────────────
    # TEST C — Blurred image (Verify warning)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST C] Blurred Image Sharpness Check")
    status, a_blur = http_post("/api/analysis/strain", params={"image1_filename": blur, "image2_filename": g2})
    assert status == 200, f"Test C failed: {a_blur}"
    qc_blur = a_blur.get("quality_control") or {}
    all_warnings_blur = " ".join(qc_blur.get("warnings", [])).lower()
    assert "blurred" in all_warnings_blur or "laplacian" in all_warnings_blur or "sharpness" in all_warnings_blur, \
        f"Expected blur warning, got warnings: {qc_blur.get('warnings')}"
    print(f"  [PASS] Correctly flagged blur warning: {qc_blur.get('warnings')}")

    # ─────────────────────────────────────────────────────────────
    # TEST D — Different image dimensions (Verify compatibility warning)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST D] Different Image Dimensions Compatibility Check")
    status, a_dim = http_post("/api/analysis/strain", params={"image1_filename": g1, "image2_filename": diff_dim})
    assert status == 200, f"Test D failed: {a_dim}"
    qc_dim = a_dim.get("quality_control") or {}
    all_warnings_dim = " ".join(qc_dim.get("warnings", [])).lower()
    assert "different dimensions" in all_warnings_dim or "resized" in all_warnings_dim, \
        f"Expected dimension compatibility warning, got: {qc_dim.get('warnings')}"
    print(f"  [PASS] Correctly identified image dimension resizing warning: {qc_dim.get('warnings')}")

    # ─────────────────────────────────────────────────────────────
    # TEST E — ROI Quality Component
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST E] ROI Quality Component Evaluation")
    # Valid ROI
    roi_valid = {
        "enabled": True,
        "type": "rectangle",
        "coordinates": {"x": 30, "y": 30, "width": 60, "height": 60}
    }
    status, a_roi = http_post(
        "/api/analysis/strain",
        params={"image1_filename": g1, "image2_filename": g2, "roi": json.dumps(roi_valid)}
    )
    assert status == 200
    qc_roi = a_roi.get("quality_control") or {}
    roi_comp = qc_roi["components"]["roi_quality"]
    assert roi_comp["applicable"] is True
    assert roi_comp["status"] == "Good"
    assert roi_comp["metrics"]["pixel_count"] > 0
    print(f"  [PASS] ROI quality evaluated: Status '{roi_comp['status']}', Area: {roi_comp['metrics']['area_percentage']}%")

    # ─────────────────────────────────────────────────────────────
    # TEST F — Tracked ROI Quality Component
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST F] Tracked ROI Quality Component Evaluation")
    tracked_roi = {
        "enabled": True,
        "mode": "tracked",
        "type": "rectangle",
        "coordinates": {"x": 40, "y": 40, "width": 45, "height": 45}
    }
    status, a_track = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", g1), ("filenames", g2), ("filenames", g1), ("roi", json.dumps(tracked_roi))]
    )
    assert status == 200, f"Failed tracked temporal analysis: {a_track}"
    qc_track = a_track.get("quality_control") or {}
    trk_comp = qc_track["components"]["tracking_quality"]
    assert trk_comp["applicable"] is True
    assert "mean_confidence" in trk_comp["metrics"]
    print(f"  [PASS] Tracked ROI evaluated: Status '{trk_comp['status']}', Mean Confidence: {trk_comp['metrics']['mean_confidence']}")

    # ─────────────────────────────────────────────────────────────
    # TEST G — Temporal Analysis Quality Component
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST G] Temporal Analysis Quality Component Evaluation")
    status, a_temp = http_post(
        "/api/analysis/temporal-strain",
        params=[("filenames", g1), ("filenames", g2), ("filenames", g1), ("filenames", g2)]
    )
    assert status == 200
    qc_temp = a_temp.get("quality_control") or {}
    temp_comp = qc_temp["components"]["temporal_quality"]
    assert temp_comp["applicable"] is True
    assert temp_comp["metrics"]["frame_count"] == 4
    print(f"  [PASS] Temporal quality evaluated: Status '{temp_comp['status']}', Frames: {temp_comp['metrics']['frame_count']}")

    # ─────────────────────────────────────────────────────────────
    # TEST H — Missing Calibration (Info notice, not failure)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST H] Missing Calibration Notice Evaluation")
    # Analysis a_good was uncalibrated
    cal_comp = qc_good["components"]["calibration_consistency"]
    assert cal_comp["calibrated"] is False
    assert cal_comp["status"] == "Uncalibrated"
    # Ensure informational message is present
    all_info_good = " ".join(qc_good.get("info", [])).lower()
    assert "spatial calibration was not provided" in all_info_good, \
        f"Expected informational calibration notice, got info: {qc_good.get('info')}"
    # Verify score was NOT failed down to Poor (<60) due to lack of calibration alone
    assert qc_good["score"] >= 75
    print("  [PASS] Uncalibrated analysis correctly tagged with informational notice without penalizing score.")

    # ─────────────────────────────────────────────────────────────
    # TEST I — Invalid Numerical Values (Safe handling)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST I] Invalid Numerical Values & Extreme Strain Handling")
    from app.services.quality_control import evaluate_strain_quality, evaluate_motion_quality
    # Test non-finite in strain
    strain_corrupt = {"principal_strain_1": {"mean": float("nan"), "max": 99.0}}
    res_s = evaluate_strain_quality(strain_corrupt)
    assert any("non-finite" in w.lower() for w in res_s["warnings"])
    assert res_s["score"] < 70

    # Test extreme velocity in motion
    motion_extreme = {"mean_displacement": 0.001, "max_displacement": 150.0, "std_displacement": 20.0}
    res_m = evaluate_motion_quality(motion_extreme)
    assert any("unstable" in w.lower() or "near-zero" in w.lower() for w in res_m["warnings"])
    print("  [PASS] Robust warning generation verified for non-finite and extreme numerical values.")

    # ─────────────────────────────────────────────────────────────
    # TEST J — Old History Entry Backward Compatibility
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST J] Backward Compatibility for Analysis Records Without QC")
    from app.services.quality_control import evaluate_analysis_quality
    import copy

    # 1. Create a simulated legacy analysis record with no "quality_control" attribute
    legacy_record = copy.deepcopy(a_good)
    if "quality_control" in legacy_record:
        del legacy_record["quality_control"]
    legacy_history_entry = {
        "id": "legacy-sample-1999",
        "timestamp": "2025-01-01T12:00:00Z",
        "type": "single_pair",
        "summary": {
            "mean_displacement": 1.5,
            "max_displacement": 3.2,
            "mean_principal_strain": 0.05,
        },
        "result": legacy_record
    }

    # Evaluate legacy record directly with QC service
    legacy_qc = evaluate_analysis_quality(legacy_history_entry)
    assert legacy_qc is not None
    assert "score" in legacy_qc and "level" in legacy_qc
    assert "components" in legacy_qc
    assert legacy_qc["score"] > 0
    print(f"  [PASS] Legacy analysis evaluated safely by QC engine: Score {legacy_qc['score']}/100 ({legacy_qc['level']}).")

    # ─────────────────────────────────────────────────────────────
    # TEST K — Quality Control API Endpoints
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST K] Quality Control API Endpoints (GET & POST /api/quality/{id})")
    status, q_get = http_get(f"/api/quality/{good_id}")
    assert status == 200
    assert q_get["score"] == qc_good["score"]

    status, q_post = http_post(f"/api/quality/{good_id}")
    assert status == 200
    assert q_post["score"] == qc_good["score"]
    print(f"  [PASS] Verified GET /api/quality/{good_id} and POST /api/quality/{good_id}.")

    # ─────────────────────────────────────────────────────────────
    # TEST L — Comparison Page with Quality Control
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST L] Multi-Analysis Comparison Quality Control Integration")
    second_id = a_roi.get("analysis_id") or a_roi.get("id")
    status, comp_res = http_post("/api/comparison", json_body={"analysis_ids": [good_id, second_id]})
    assert status == 200
    # Check that each analysis has quality_control in metadata
    for a in comp_res["analyses"]:
        assert "quality_control" in a["metadata"]
        assert a["metadata"]["quality_control"] is not None
        assert "score" in a["metadata"]["quality_control"]

    # Check that comparison table includes Computational Quality Control category
    cat_keys = [r["category_key"] for r in comp_res["comparison_table"]]
    assert "quality" in cat_keys, f"Expected 'quality' category in comparison table, got: {cat_keys}"
    print(f"  [PASS] Comparison response contains 'quality' category and metadata QC scores.")

    # ─────────────────────────────────────────────────────────────
    # TEST M — PDF Report with Quality Control Section
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST M] PDF Report Generation with Quality Control Section")
    status, rep_res = http_post(f"/api/reports/{good_id}")
    assert status == 200
    pdf_path = Path("reports") / f"cardiac_analysis_{good_id}.pdf"
    assert pdf_path.exists(), f"Report file not found at {pdf_path}"
    assert pdf_path.stat().st_size > 5000, f"Report size too small ({pdf_path.stat().st_size} bytes)"

    # Verify text inside the generated PDF by decompressing ReportLab ASCII85+Flate streams
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    import base64, zlib, re
    found_qc = False
    pattern = re.compile(rb'/Filter\s+\[\s*/ASCII85Decode\s+/FlateDecode\s*\]\s*/Length\s+(\d+)\s*>>\s*stream[\r\n]+(.*?)~>endstream', re.DOTALL)
    for m in pattern.finditer(pdf_bytes):
        try:
            raw = base64.a85decode(m.group(2) + b'~>', adobe=True)
            dec = zlib.decompress(raw)
            if b"Computational Analysis Quality" in dec or b"Quality Score" in dec:
                found_qc = True
                break
        except Exception:
            pass

    assert found_qc or (b"Computational Analysis Quality" in pdf_bytes), \
        "Expected Quality section in generated PDF"
    print(f"  [PASS] Generated PDF verified on disk with Quality Control section: {pdf_path.name} ({pdf_path.stat().st_size} bytes).")

    print("\n" + "=" * 70)
    print("ALL TESTS (TEST A through TEST M) PASSED SUCCESSFULLY! STEP 11.11 VERIFIED.")
    print("=" * 70)


if __name__ == "__main__":
    run_all_qc_tests()
