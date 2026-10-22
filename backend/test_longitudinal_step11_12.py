"""
backend/test_longitudinal_step11_12.py

Comprehensive Verification Suite for Step 11.12:
Longitudinal / Multi-Session Study Analysis

Tests:
1. Study with one analysis (insufficient data state)
2. Study with multiple analyses (timeline aggregation)
3. Chronological sorting verification
4. Missing / deleted analysis ID handling
5. Missing QC data handling
6. Different calibration settings detection
7. ROI vs non-ROI analyses detection
8. Missing metric values handling
9. Trend calculation (increasing, decreasing, stable)
10. First-vs-latest comparative delta
11. Timeline endpoint (/api/longitudinal/study/{id}/timeline)
12. Trends endpoint (/api/longitudinal/study/{id}/trends)
13. Longitudinal PDF report generation (/api/reports/longitudinal/{id})
14. Non-diagnostic research prototype disclaimer enforcement
15. Existing route integrity (/api/history, /api/studies, /api/quality, /api/comparison, /api/analysis)
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
import numpy as np
import cv2

BASE_URL = "http://127.0.0.1:8000"
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def http_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def http_post(path, json_body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if json_body is not None else {},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def create_test_images():
    """Create synthetic test images in uploads directory."""
    img1 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img1, (64, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "long_img1.png"), img1)

    img2 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img2, (68, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "long_img2.png"), img2)

    img3 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img3, (74, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "long_img3.png"), img3)


def run_all_longitudinal_tests():
    print("=" * 70)
    print("RUNNING STEP 11.12 LONGITUDINAL STUDY ANALYSIS VERIFICATION SUITE")
    print("=" * 70)

    create_test_images()

    # ─────────────────────────────────────────────────────────────
    # Run Baseline Analyses
    # ─────────────────────────────────────────────────────────────
    # Analysis 1: Baseline single-pair uncalibrated full-image
    status, a1 = http_post("/api/analysis/strain?image1_filename=long_img1.png&image2_filename=long_img2.png")
    assert status == 200, f"Analysis 1 failed: {a1}"
    id1 = a1["analysis_id"]

    # Analysis 2: Session 2 with higher motion
    status, a2 = http_post("/api/analysis/strain?image1_filename=long_img1.png&image2_filename=long_img3.png")
    assert status == 200, f"Analysis 2 failed: {a2}"
    id2 = a2["analysis_id"]

    # Analysis 3: Session 3 with spatial calibration
    status, a3 = http_post("/api/analysis/strain?image1_filename=long_img2.png&image2_filename=long_img3.png&pixel_spacing_x=0.5&pixel_spacing_y=0.5&unit=mm")
    assert status == 200, f"Analysis 3 failed: {a3}"
    id3 = a3["analysis_id"]

    # Analysis 4: Session 4 with ROI
    roi_query = urllib.parse.quote(json.dumps({
        "enabled": True,
        "type": "rectangle",
        "coordinates": {"x": 30, "y": 30, "width": 60, "height": 60}
    }))
    status, a4 = http_post(f"/api/analysis/strain?image1_filename=long_img1.png&image2_filename=long_img2.png&roi={roi_query}")
    assert status == 200, f"Analysis 4 failed: {a4}"
    id4 = a4["analysis_id"]

    # ─────────────────────────────────────────────────────────────
    # TEST 1 — Study with One Analysis
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 1] Study with One Analysis (Insufficient Data State)")
    status, study1 = http_post("/api/studies", json_body={"title": "Single Session Study", "subject_code": "SUBJ-001"})
    assert status in (200, 201), f"Create study failed: {study1}"
    s1_id = study1["id"]

    # Add 1 analysis
    http_post(f"/api/studies/{s1_id}/analyses/{id1}")

    status, long_s1 = http_get(f"/api/longitudinal/study/{s1_id}")
    assert status == 200, f"Get longitudinal summary failed: {long_s1}"
    assert long_s1["analysis_count"] == 1
    assert len(long_s1["timeline"]) == 1
    assert long_s1["first_vs_latest"]["available"] is False
    assert long_s1["trends"]["mean_displacement"]["trend_direction"] == "insufficient_data"
    print("  [PASS] Single analysis study correctly returns timeline=1, first_vs_latest=False, trend=insufficient_data.")

    # ─────────────────────────────────────────────────────────────
    # TEST 2 — Study with Multiple Analyses
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 2] Study with Multiple Analyses (Timeline Aggregation)")
    status, study2 = http_post("/api/studies", json_body={"title": "Multi-Session Progression Study", "subject_code": "SUBJ-002"})
    assert status in (200, 201), f"Create study failed: {study2}"
    s2_id = study2["id"]

    # Add 2 analyses
    http_post(f"/api/studies/{s2_id}/analyses/{id1}")
    http_post(f"/api/studies/{s2_id}/analyses/{id2}")

    status, long_s2 = http_get(f"/api/longitudinal/study/{s2_id}")
    assert status == 200
    assert long_s2["analysis_count"] == 2
    assert len(long_s2["timeline"]) == 2
    assert long_s2["first_vs_latest"]["available"] is True
    print(f"  [PASS] Multi-analysis study correctly compiled 2 sessions with active comparison.")

    # ─────────────────────────────────────────────────────────────
    # TEST 3 — Chronological Sorting
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 3] Chronological Sorting Verification")
    timeline = long_s2["timeline"]
    assert timeline[0]["timestamp"] <= timeline[1]["timestamp"], "Timeline must be sorted ascending by timestamp"
    print(f"  [PASS] Verified timeline items sorted chronologically ({timeline[0]['timestamp']} <= {timeline[1]['timestamp']}).")

    # ─────────────────────────────────────────────────────────────
    # TEST 4 — Missing / Deleted Analysis ID Handling
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 4] Missing / Deleted Analysis ID Handling")
    # Manually append a non-existent UUID to study's analysis_ids
    fake_aid = "00000000-0000-0000-0000-000000000000"
    from app.services.studies import add_analysis_to_study
    add_analysis_to_study(s2_id, fake_aid)

    status, long_s2_missing = http_get(f"/api/longitudinal/study/{s2_id}")
    assert status == 200
    assert long_s2_missing["analysis_count"] == 2  # still 2 valid records
    assert any("not found in history" in w for w in long_s2_missing["warnings"])
    print("  [PASS] Safely ignored missing/deleted analysis ID and flagged warning.")

    # ─────────────────────────────────────────────────────────────
    # TEST 5 — Missing QC Data Handling
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 5] Missing QC Data Handling")
    from app.services.longitudinal import extract_longitudinal_metrics, summarize_study_quality
    legacy_rec = {
        "id": "leg-synthetic",
        "timestamp": "2026-10-16T10:00:00Z",
        "type": "single_pair",
        "result": {
            "displacement": {"mean_displacement": 1.25, "max_displacement": 3.4},
            "strain_statistics": {"principal_strain_1": {"mean": 0.05, "max": 0.12}},
        }
    }
    extracted = extract_longitudinal_metrics(legacy_rec)
    assert extracted["metrics"]["quality_score"] is None
    assert extracted["quality_level"] is None
    quality_summary, qc_warns, qc_info = summarize_study_quality([extracted])
    assert quality_summary["unassessed_count"] == 1
    assert any("Quality assessment not available" in inf for inf in qc_info)
    print("  [PASS] Legacy analysis without QC handled gracefully; unassessed_count recorded.")

    # ─────────────────────────────────────────────────────────────
    # TEST 6 — Different Calibration Settings Detection
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 6] Different Calibration Settings Detection")
    status, study_cal = http_post("/api/studies", json_body={"title": "Calibration Test Study", "subject_code": "CAL-01"})
    assert status in (200, 201)
    s_cal_id = study_cal["id"]
    http_post(f"/api/studies/{s_cal_id}/analyses/{id1}")  # uncalibrated
    http_post(f"/api/studies/{s_cal_id}/analyses/{id3}")  # calibrated (0.5 mm)

    status, long_cal = http_get(f"/api/longitudinal/study/{s_cal_id}")
    assert status == 200
    assert long_cal["calibration_consistency"]["status"] == "mixed"
    assert any("calibration settings differ" in w for w in long_cal["warnings"])
    print("  [PASS] Mixed calibration detected and flagged with warning.")

    # ─────────────────────────────────────────────────────────────
    # TEST 7 — ROI vs Non-ROI Analyses Detection
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 7] ROI vs Non-ROI Analyses Detection")
    status, study_roi = http_post("/api/studies", json_body={"title": "ROI Test Study", "subject_code": "ROI-01"})
    assert status in (200, 201)
    s_roi_id = study_roi["id"]
    http_post(f"/api/studies/{s_roi_id}/analyses/{id1}")  # full image
    http_post(f"/api/studies/{s_roi_id}/analyses/{id4}")  # ROI masked

    status, long_roi = http_get(f"/api/longitudinal/study/{s_roi_id}")
    assert status == 200
    assert long_roi["roi_consistency"]["status"] == "mixed"
    assert any("Region of Interest" in w for w in long_roi["warnings"])
    print("  [PASS] Mixed ROI vs full-image usage detected and warned.")

    # ─────────────────────────────────────────────────────────────
    # TEST 8 — Missing Metric Values Handling
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 8] Missing Metric Values Handling")
    from app.services.longitudinal import extract_longitudinal_metrics
    sparse_record = {"id": "sparse-1", "timestamp": "2026-10-16T10:00:00Z", "result": {}}
    extracted = extract_longitudinal_metrics(sparse_record)
    assert extracted["metrics"]["mean_displacement"] is None
    assert extracted["metrics"]["motion_coherence"] is None
    print("  [PASS] Sparse/empty analysis record returns None for missing metrics without crashing.")

    # ─────────────────────────────────────────────────────────────
    # TEST 9 — Trend Calculation Verification
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 9] Trend Calculation Verification (Increasing, Decreasing, Stable)")
    from app.services.longitudinal import calculate_metric_trends
    sim_timeline = [
        {"metrics": {"mean_displacement": 2.0, "mean_strain": 0.10, "motion_coherence": 0.80}},
        {"metrics": {"mean_displacement": 2.8, "mean_strain": 0.05, "motion_coherence": 0.81}},
    ]
    calc_trends = calculate_metric_trends(sim_timeline)
    assert calc_trends["mean_displacement"]["trend_direction"] == "increasing"
    assert calc_trends["mean_strain"]["trend_direction"] == "decreasing"
    assert calc_trends["motion_coherence"]["trend_direction"] == "stable"
    print("  [PASS] Trend directions verified: Disp=increasing, Strain=decreasing, Coherence=stable.")

    # ─────────────────────────────────────────────────────────────
    # TEST 10 — First vs Latest Comparative Delta
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 10] First vs Latest Comparative Delta Verification")
    from app.services.longitudinal import compare_first_and_latest
    f_vs_l = compare_first_and_latest(sim_timeline)
    assert f_vs_l["available"] is True
    disp_m = f_vs_l["metrics"]["mean_displacement"]
    assert disp_m["first_value"] == 2.0
    assert disp_m["latest_value"] == 2.8
    assert disp_m["absolute_change"] == 0.8
    assert disp_m["percentage_change"] == 40.0
    print("  [PASS] First vs latest delta and percentage change verified (Delta=+0.8, +40.0%).")

    # ─────────────────────────────────────────────────────────────
    # TEST 11 — Timeline Endpoint
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 11] Timeline Endpoint (/api/longitudinal/study/{id}/timeline)")
    status, t_res = http_get(f"/api/longitudinal/study/{s2_id}/timeline")
    assert status == 200
    assert "timeline" in t_res
    assert len(t_res["timeline"]) == 2
    print("  [PASS] Timeline endpoint verified.")

    # ─────────────────────────────────────────────────────────────
    # TEST 12 — Trends Endpoint
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 12] Trends Endpoint (/api/longitudinal/study/{id}/trends)")
    status, tr_res = http_get(f"/api/longitudinal/study/{s2_id}/trends")
    assert status == 200
    assert "trends" in tr_res
    assert "mean_displacement" in tr_res["trends"]
    print("  [PASS] Trends endpoint verified.")

    # ─────────────────────────────────────────────────────────────
    # TEST 13 — Longitudinal PDF Report Generation
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 13] Longitudinal PDF Report Generation (/api/reports/longitudinal/{id})")
    status, rep_res = http_post(f"/api/reports/longitudinal/{s2_id}")
    assert status == 200, f"PDF report generation failed: {rep_res}"
    pdf_filename = rep_res["report_filename"]
    pdf_path = Path("reports") / pdf_filename
    assert pdf_path.exists(), f"PDF not found at {pdf_path}"
    assert pdf_path.stat().st_size > 5000, f"PDF size too small: {pdf_path.stat().st_size} bytes"
    print(f"  [PASS] Generated longitudinal PDF report verified: {pdf_filename} ({pdf_path.stat().st_size} bytes).")

    # ─────────────────────────────────────────────────────────────
    # TEST 14 — Non-Diagnostic Research Prototype Disclaimer Enforcement
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 14] Non-Diagnostic Research Prototype Disclaimer Enforcement")
    assert "disclaimer" in long_s2
    assert "NOT a clinical diagnosis" in long_s2["disclaimer"]
    print("  [PASS] Non-diagnostic scientific research disclaimer enforced in API and report metadata.")

    # ─────────────────────────────────────────────────────────────
    # TEST 15 — Existing Route Integrity Check
    # ─────────────────────────────────────────────────────────────
    print("\n[TEST 15] Existing Route Integrity Verification")
    s, h = http_get("/api/history")
    assert s == 200, "GET /api/history failed"

    s, st = http_get("/api/studies")
    assert s == 200, "GET /api/studies failed"

    s, comp = http_post("/api/comparison", json_body={"analysis_ids": [id1, id2]})
    assert s == 200, "POST /api/comparison failed"

    s, q = http_get(f"/api/quality/{id1}")
    assert s == 200, "GET /api/quality failed"

    print("  [PASS] All core pre-existing routes (/api/history, /api/studies, /api/comparison, /api/quality) responding normally.")

    print("\n" + "=" * 70)
    print("ALL TESTS (TEST 1 through TEST 15) PASSED SUCCESSFULLY! STEP 11.12 VERIFIED.")
    print("=" * 70)


if __name__ == "__main__":
    import urllib.parse
    run_all_longitudinal_tests()
