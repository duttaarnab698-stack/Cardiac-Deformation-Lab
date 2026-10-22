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


def http_delete(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def setup_test_images():
    for d in ["backend/uploads", "uploads"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    h, w = 128, 128

    # Frame 1: baseline circle at (64, 64)
    img1 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        img1[y, :, :] = int(y / h * 80)
    cv2.circle(img1, (64, 64), 22, (255, 255, 255), -1)
    cv2.circle(img1, (64, 64), 12, (180, 180, 180), -1)

    # Frame 2: deformed circle shifted to (68, 66)
    img2 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        img2[y, :, :] = int(y / h * 80)
    cv2.circle(img2, (68, 66), 24, (255, 255, 255), -1)
    cv2.circle(img2, (68, 66), 11, (180, 180, 180), -1)

    # Frame 3: further deformed circle at (72, 69)
    img3 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        img3[y, :, :] = int(y / h * 80)
    cv2.circle(img3, (72, 69), 20, (255, 255, 255), -1)
    cv2.circle(img3, (72, 69), 10, (180, 180, 180), -1)

    # Frame 4: return toward (65, 65)
    img4 = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        img4[y, :, :] = int(y / h * 80)
    cv2.circle(img4, (65, 65), 22, (255, 255, 255), -1)
    cv2.circle(img4, (65, 65), 12, (180, 180, 180), -1)

    pairs = [
        ("comp_test_f1.png", img1),
        ("comp_test_f2.png", img2),
        ("comp_test_f3.png", img3),
        ("comp_test_f4.png", img4),
    ]

    for fname, img in pairs:
        for d in ["backend/uploads", "uploads"]:
            cv2.imwrite(str(Path(d) / fname), img)

    return [p[0] for p in pairs]


def run_tests():
    print("=" * 70)
    print("RUNNING STEP 11.10 ANALYSIS COMPARISON VERIFICATION SUITE")
    print("=" * 70)

    fnames = setup_test_images()
    f1, f2, f3, f4 = fnames
    print(f"Test frames initialized: {fnames}")

    # Generate baseline analyses for testing
    print("\n--- Generating Base Analyses ---")

    # 1. Single-pair analysis A (uncalibrated, full image)
    status, a1 = http_post("/api/analysis/strain", params={"image1_filename": f1, "image2_filename": f2})
    assert status == 200, f"Failed to generate analysis 1: {a1}"
    id1 = a1.get("analysis_id") or a1.get("id")
    print(f"Created Analysis 1 (Single-pair, uncalibrated): {id1}")

    # 2. Single-pair analysis B (uncalibrated, full image, different pair f1 -> f3)
    status, a2 = http_post("/api/analysis/strain", params={"image1_filename": f1, "image2_filename": f3})
    assert status == 200, f"Failed to generate analysis 2: {a2}"
    id2 = a2.get("analysis_id") or a2.get("id")
    print(f"Created Analysis 2 (Single-pair, uncalibrated): {id2}")

    # 3. Temporal analysis 1 (f1, f2, f3, f4)
    status, t1 = http_post("/api/analysis/temporal-strain", params=[("filenames", fn) for fn in [f1, f2, f3, f4]])
    assert status == 200, f"Failed to generate temporal analysis 1: {t1}"
    tid1 = t1.get("analysis_id") or t1.get("id")
    print(f"Created Temporal Analysis 1: {tid1}")

    # 4. Temporal analysis 2 (f1, f2, f3)
    status, t2 = http_post("/api/analysis/temporal-strain", params=[("filenames", fn) for fn in [f1, f2, f3]])
    assert status == 200, f"Failed to generate temporal analysis 2: {t2}"
    tid2 = t2.get("analysis_id") or t2.get("id")
    print(f"Created Temporal Analysis 2: {tid2}")

    # 5. Calibrated single-pair analysis (0.5 mm/pixel)
    status, a_cal = http_post(
        "/api/analysis/strain",
        params={
            "image1_filename": f1,
            "image2_filename": f2,
            "pixel_spacing_x": 0.5,
            "pixel_spacing_y": 0.5,
            "unit": "mm"
        }
    )
    assert status == 200, f"Failed to generate calibrated analysis: {a_cal}"
    id_cal = a_cal.get("analysis_id") or a_cal.get("id")
    print(f"Created Calibrated Analysis: {id_cal}")

    # 6. ROI single-pair analysis
    roi_payload = {
        "enabled": True,
        "type": "rectangle",
        "coordinates": {"x": 40, "y": 40, "width": 50, "height": 50}
    }
    status, a_roi = http_post(
        "/api/analysis/strain",
        params={
            "image1_filename": f1,
            "image2_filename": f2,
            "roi": json.dumps(roi_payload)
        }
    )
    assert status == 200, f"Failed to generate ROI analysis: {a_roi}"
    id_roi = a_roi.get("analysis_id") or a_roi.get("id")
    print(f"Created ROI Analysis: {id_roi}")

    # ─────────────────────────────────────────────────────────────
    # Test A: Compare 2 single-pair analyses
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST A] Compare 2 Single-Pair Analyses")
    status, comp_a = http_post("/api/comparison", json_body={"analysis_ids": [id1, id2]})
    assert status == 200, f"Test A Failed: {comp_a}"
    assert comp_a["analysis_count"] == 2
    assert "comparison_table" in comp_a and len(comp_a["comparison_table"]) > 0
    assert "largest_differences" in comp_a["differences"]
    assert len(comp_a["differences"]["largest_differences"]) > 0
    for diff in comp_a["differences"]["largest_differences"]:
        assert "metric_name" in diff
        assert "val1" in diff and "val2" in diff
        assert "difference" in diff
    print("  [PASS] Successfully compared 2 single-pair analyses with pairwise differences and largest divergent metrics.")

    # ─────────────────────────────────────────────────────────────
    # Test B: Compare 2 temporal analyses
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST B] Compare 2 Temporal Analyses")
    status, comp_b = http_post("/api/comparison", json_body={"analysis_ids": [tid1, tid2]})
    assert status == 200, f"Test B Failed: {comp_b}"
    assert comp_b["analysis_count"] == 2
    metric_keys = [r["metric_key"] for r in comp_b["comparison_table"]]
    assert "temporal_stability_index" in metric_keys or "frame_count" in metric_keys
    print("  [PASS] Successfully compared 2 temporal analyses including temporal sequence dynamics.")

    # ─────────────────────────────────────────────────────────────
    # Test C: Compare 3 analyses concurrently
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST C] Compare 3 Analyses Concurrently")
    status, comp_c = http_post("/api/comparison", json_body={"analysis_ids": [id1, id2, tid1]})
    assert status == 200, f"Test C Failed: {comp_c}"
    assert comp_c["analysis_count"] == 3
    # When >2 analyses, pairwise largest_differences is empty, but comparison table has 3 values per row
    for row in comp_c["comparison_table"][:5]:
        assert len(row["values"]) == 3
    print("  [PASS] Successfully compared 3 analyses with multi-series matrix.")

    # ─────────────────────────────────────────────────────────────
    # Test D: Calibrated vs Uncalibrated Comparison (Compatibility Warning)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST D] Calibrated vs Uncalibrated Compatibility Evaluation")
    status, comp_d = http_post("/api/comparison", json_body={"analysis_ids": [id_cal, id1]})
    assert status == 200, f"Test D Failed: {comp_d}"
    cal_compat = comp_d["calibration_compatibility"]
    assert cal_compat["status"] == "mixed_calibration"
    assert cal_compat["warning"] is not None and len(cal_compat["warning"]) > 0
    assert "pixel" in cal_compat["warning"].lower() or "calibration" in cal_compat["warning"].lower()
    print(f"  [PASS] Correctly flagged mixed spatial calibration warning: '{cal_compat['warning']}'")

    # ─────────────────────────────────────────────────────────────
    # Test E: Full Image vs ROI Scope (Compatibility Warning)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST E] Full Image vs ROI Scope Compatibility Evaluation")
    status, comp_e = http_post("/api/comparison", json_body={"analysis_ids": [id1, id_roi]})
    assert status == 200, f"Test E Failed: {comp_e}"
    roi_compat = comp_e["roi_compatibility"]
    assert roi_compat["status"] == "mixed_scope"
    assert roi_compat["warning"] is not None and len(roi_compat["warning"]) > 0
    assert "roi" in roi_compat["warning"].lower() or "region" in roi_compat["warning"].lower()
    print(f"  [PASS] Correctly flagged mixed analysis scope warning: '{roi_compat['warning']}'")

    # ─────────────────────────────────────────────────────────────
    # Test F: Same Study Analyses Context
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST F] Same Study Analyses Context Evaluation")
    # Create study
    status, study_a = http_post("/api/studies", json_body={"title": "Verification Study A"})
    assert status in (200, 201), f"Failed to create study: {study_a}"
    s_id_a = study_a["id"]
    # Link both id1 and id2 to Study A
    http_post(f"/api/studies/{s_id_a}/analyses/{id1}")
    http_post(f"/api/studies/{s_id_a}/analyses/{id2}")

    status, comp_f = http_post("/api/comparison", json_body={"analysis_ids": [id1, id2]})
    assert status == 200, f"Test F Failed: {comp_f}"
    study_ctx = comp_f["study_context"]
    assert study_ctx["status"] == "same_study"
    assert study_ctx["badge"] == "Same Study"
    print(f"  [PASS] Detected same study context: '{study_ctx['message']}'")

    # ─────────────────────────────────────────────────────────────
    # Test G: Different Study Analyses Context
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST G] Different Studies Context Evaluation")
    # Create study B
    status, study_b = http_post("/api/studies", json_body={"title": "Verification Study B"})
    assert status in (200, 201)
    s_id_b = study_b["id"]
    http_post(f"/api/studies/{s_id_b}/analyses/{tid1}")

    status, comp_g = http_post("/api/comparison", json_body={"analysis_ids": [id1, tid1]})
    assert status == 200, f"Test G Failed: {comp_g}"
    study_ctx_g = comp_g["study_context"]
    assert study_ctx_g["status"] == "different_studies"
    assert study_ctx_g["badge"] == "Different Studies"
    print(f"  [PASS] Detected different studies context: '{study_ctx_g['message']}'")

    # ─────────────────────────────────────────────────────────────
    # Test H: Fingerprint Comparison (10-D radar chart data)
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST H] 10-D Fingerprint Comparison Structure")
    fp_comp = comp_a.get("fingerprint_comparison")
    assert fp_comp is not None, "fingerprint_comparison is missing"
    assert len(fp_comp["parameters"]) == 10, f"Expected 10 radar parameters, got {len(fp_comp['parameters'])}"
    assert len(fp_comp["series"]) == 2, f"Expected 2 series, got {len(fp_comp['series'])}"
    for s in fp_comp["series"]:
        assert len(s["values"]) == 10, "Each series must have 10 values"
        for v in s["values"].values():
            assert 0.0 <= v <= 100.0, f"Fingerprint value out of range [0, 100]: {v}"
    print("  [PASS] 10-D Cardiac Deformation Fingerprint comparison structured and validated.")

    # ─────────────────────────────────────────────────────────────
    # Test I: Map Comparison Compatibility
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST I] Compatible Output Colormap Discovery")
    maps = comp_a.get("compatible_maps", [])
    assert len(maps) > 0, "No compatible maps found for comparison"
    map_keys = [m["key"] for m in maps]
    assert "principal_strain_heatmap" in map_keys or "displacement_heatmap" in map_keys
    for m in maps:
        assert len(m["paths"]) == 2
        for p in m["paths"]:
            assert p is not None
    print(f"  [PASS] Found {len(maps)} compatible colormaps for side-by-side inspection: {map_keys}")

    # ─────────────────────────────────────────────────────────────
    # Test J: Save Comparison to JSON
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST J] Save Comparison Endpoint (POST /api/comparison/save)")
    save_payload = {
        "analysis_ids": [id1, id2],
        "title": "Automated Test Comparison",
        "notes": "Biomechanics verification test record",
        "comparison": comp_a
    }
    status, save_res = http_post("/api/comparison/save", json_body=save_payload)
    assert status == 200, f"Failed to save comparison: {save_res}"
    saved_id = save_res["comparison"]["id"]
    assert saved_id is not None
    print(f"  Saved comparison ID: {saved_id}")

    # Verify retrieval from history
    status, history_list = http_get("/api/comparison/history")
    assert status == 200
    ids_in_hist = [c["id"] for c in history_list]
    assert saved_id in ids_in_hist, f"Saved ID {saved_id} not found in history list"
    print("  [PASS] Comparison successfully persisted and verified in history list.")

    # ─────────────────────────────────────────────────────────────
    # Test K: Delete Saved Comparison (DELETE /api/comparison/history/{id})
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST K] Delete Saved Comparison")
    status, del_res = http_delete(f"/api/comparison/history/{saved_id}")
    assert status == 200, f"Failed to delete comparison: {del_res}"

    # Verify removal
    status, history_after = http_get("/api/comparison/history")
    assert status == 200
    ids_after = [c["id"] for c in history_after]
    assert saved_id not in ids_after, f"Deleted ID {saved_id} still present in history"
    print("  [PASS] Successfully deleted saved comparison record.")

    # ─────────────────────────────────────────────────────────────
    # Test L: Comparison PDF Report & Individual Report Regression
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST L] Generate Comparison PDF Report & Verify Individual Reports")
    rep_payload = {
        "analysis_ids": [id1, id2],
        "title": "Automated Verification Comparison Report"
    }
    status, rep_res = http_post("/api/comparison/report", json_body=rep_payload)
    assert status == 200, f"Failed to generate comparison report: {rep_res}"
    pdf_path = Path(rep_res["report_path"])
    assert pdf_path.exists(), f"PDF report not found at {pdf_path}"
    pdf_size = pdf_path.stat().st_size
    assert pdf_size > 1000, f"PDF report suspiciously small: {pdf_size} bytes"
    print(f"  Comparison PDF generated successfully: {pdf_path.name} ({pdf_size} bytes)")

    # Regression verification: Individual analysis report generation
    status, ind_rep_res = http_post(f"/api/reports/{id1}")
    assert status == 200, f"Individual report generation regression failed: {ind_rep_res}"
    ind_pdf = Path("reports") / f"cardiac_analysis_{id1}.pdf"
    assert ind_pdf.exists(), f"Individual report PDF not found at {ind_pdf}"
    print(f"  Individual analysis PDF verified: {ind_pdf.name} ({ind_pdf.stat().st_size} bytes)")
    print("  [PASS] Comparison PDF generation and regression check completed cleanly.")

    print("\n" + "=" * 70)
    print("ALL TESTS (A through L) PASSED SUCCESSFULLY! STEP 11.10 FULLY VERIFIED.")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
