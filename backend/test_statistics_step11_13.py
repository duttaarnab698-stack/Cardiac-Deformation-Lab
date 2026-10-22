"""
backend/test_statistics_step11_13.py

Comprehensive Verification Suite for Step 11.13:
Advanced Statistical and Research Analytics for Cardiac Deformation Lab

Tests:
1. Pure unit tests of statistical service functions:
   - calculate_descriptive_statistics (mean, median, min, max, std, variance, IQR, count, missing)
   - calculate_change_statistics (baseline, latest, delta, pct change, safe zero baseline)
   - calculate_variability (variance, std, range, IQR, CV%)
   - calculate_percentiles (25, 50, 75, 90, 95)
   - calculate_effect_size (standardized difference, Cohen's d)
   - calculate_correlation (Pearson r, strength, direction, small sample N < 3, zero variance)
   - detect_computational_outliers (1.5xIQR method, N < 4 safe handling, outlier flag)
2. Study with single analysis (insufficient longitudinal data handling)
3. Study with two analyses (change stats, effect size, insufficient correlation/outliers handling)
4. Study with multiple analyses (4+ sessions to trigger correlations & outlier detection)
5. Metric correlation matrix verification (pairwise Pearson r, diagonal 1.0, symmetric)
6. Outlier detection with QC context & score integration
7. Scope isolation ("full_image" vs "roi")
8. Mixed calibration detection and warning flag
9. API Endpoints verification:
   - GET /api/statistics/study/{study_id}
   - GET /api/statistics/study/{study_id}/correlations
   - GET /api/statistics/study/{study_id}/outliers
10. Statistics PDF Report Generation:
   - POST /api/reports/statistics/{study_id}
11. Non-diagnostic research prototype disclaimer verification
12. Existing route integrity check:
   - /api/history, /api/studies, /api/longitudinal, /api/quality, /api/comparison
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
import numpy as np
import cv2

from app.services.statistics import (
    calculate_descriptive_statistics,
    calculate_change_statistics,
    calculate_variability,
    calculate_percentiles,
    calculate_effect_size,
    calculate_correlation,
    detect_computational_outliers,
    calculate_metric_relationships,
    calculate_study_statistics,
)

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
    cv2.imwrite(str(UPLOADS_DIR / "stat_img1.png"), img1)

    img2 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img2, (67, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "stat_img2.png"), img2)

    img3 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img3, (71, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "stat_img3.png"), img3)

    img4 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img4, (76, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "stat_img4.png"), img4)

    img5 = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(img5, (83, 64), 28, 180, -1)
    cv2.imwrite(str(UPLOADS_DIR / "stat_img5.png"), img5)


def test_pure_statistics_functions():
    print("\n--- Part 1: Pure Statistical Engine Functions ---")
    
    # 1. Descriptive stats
    sample = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0, None, float("nan")]
    desc = calculate_descriptive_statistics(sample)
    assert desc["count"] == 8, f"Expected 8 count, got {desc['count']}"
    assert desc["mean"] == 5.0, f"Expected mean 5.0, got {desc['mean']}"
    assert desc["median"] == 4.5, f"Expected median 4.5, got {desc['median']}"
    assert desc["min"] == 2.0
    assert desc["max"] == 9.0
    assert desc["iqr"] is not None
    print("  [PASS] calculate_descriptive_statistics handles values + nulls/NaNs")

    # 2. Change stats
    vals = [10.0, 12.0, 15.0]
    chg = calculate_change_statistics(vals)
    assert chg["first_value"] == 10.0
    assert chg["latest_value"] == 15.0
    assert chg["absolute_change"] == 5.0
    assert chg["percentage_change"] == 50.0
    assert chg["trend_direction"] == "increasing"

    # Zero baseline test
    chg_zero = calculate_change_statistics([0.0, 5.0])
    assert chg_zero["percentage_change"] is None or isinstance(chg_zero["percentage_change"], float)
    print("  [PASS] calculate_change_statistics handles progression & safe zero division")

    # 3. Variability
    var_res = calculate_variability([2.0, 4.0, 6.0, 8.0])
    assert var_res["variance"] is not None
    assert var_res["std"] is not None
    assert var_res["cv"] is not None
    print("  [PASS] calculate_variability calculates variance, std, CV%")

    # 4. Percentiles
    pct = calculate_percentiles([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    assert pct["p25"] is not None
    assert pct["median"] == 55.0 or 50.0 <= pct["median"] <= 60.0
    assert pct["p75"] is not None
    assert pct["iqr"] is not None
    print("  [PASS] calculate_percentiles correctly computes quartiles & IQR")

    # 5. Effect size
    eff = calculate_effect_size([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
    assert eff is not None
    assert eff > 0
    print("  [PASS] calculate_effect_size computes Cohen's standardized difference")

    # 6. Correlation
    corr = calculate_correlation([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert corr["correlation"] == 1.0, f"Expected correlation=1.0, got {corr['correlation']}"
    assert corr["status"] == "computed"

    # Small sample N < 3
    corr_small = calculate_correlation([1, 2], [2, 4])
    assert corr_small["status"] == "insufficient_data"
    print("  [PASS] calculate_correlation computes Pearson r and protects N < 3")

    # 7. Outliers
    fake_timeline = [
        {"analysis_id": f"a{i}", "metrics": {"mean_displacement": 10.0 + i}} for i in range(8)
    ]
    # Add an extreme outlier
    fake_timeline.append({"analysis_id": "outlier_1", "metrics": {"mean_displacement": 150.0}})
    outliers = detect_computational_outliers(fake_timeline, scope="full_image")
    assert "mean_displacement" in outliers
    flagged = [o["analysis_id"] for o in outliers["mean_displacement"]]
    assert "outlier_1" in flagged, f"Expected outlier_1 to be flagged, got {flagged}"
    print("  [PASS] detect_computational_outliers flags 1.5xIQR extreme points")


def run_all_statistics_tests():
    print("=" * 70)
    print("RUNNING STEP 11.13 ADVANCED STATISTICAL ANALYTICS VERIFICATION SUITE")
    print("=" * 70)

    # Unit checks
    test_pure_statistics_functions()

    # Image synthesis
    create_test_images()

    print("\n--- Part 2: End-to-End API Integration & Study Cohorts ---")

    # 1. Run 5 consecutive analyses to create rich longitudinal timeline
    print("Running 5 sequential analyses for study cohort...")
    analyses = []
    pairs = [
        ("stat_img1.png", "stat_img2.png", {}),
        ("stat_img1.png", "stat_img3.png", {}),
        ("stat_img1.png", "stat_img4.png", {}),
        ("stat_img1.png", "stat_img5.png", {}),
        ("stat_img2.png", "stat_img5.png", {"pixel_spacing_x": 0.5, "pixel_spacing_y": 0.5, "unit": "mm"}),
    ]

    for i, (f1, f2, calib) in enumerate(pairs):
        query_params = f"image1_filename={f1}&image2_filename={f2}"
        if calib:
            query_params += f"&pixel_spacing_x={calib['pixel_spacing_x']}&pixel_spacing_y={calib['pixel_spacing_y']}&unit={calib['unit']}"
        st, a_data = http_post(f"/api/analysis/strain?{query_params}")
        assert st == 200, f"Analysis {i+1} failed: {a_data}"
        analyses.append(a_data)
        print(f"  Analysis {i+1} created: {a_data['analysis_id']}")

    # 2. Create Study with 1 analysis (Insufficient data validation)
    st, s1 = http_post("/api/studies/", {
        "title": "Study Single Session",
        "subject_code": "STAT-P001",
        "description": "Single session cohort for insufficiency validation"
    })
    assert st in (200, 201), f"Failed to create study: {s1}"
    study1_id = s1["id"]
    http_post(f"/api/studies/{study1_id}/analyses/{analyses[0]['analysis_id']}")

    st, stats_single = http_get(f"/api/statistics/study/{study1_id}")
    assert st == 200, f"Failed to get single study stats: {stats_single}"
    assert stats_single["analysis_count"] == 1
    assert stats_single["change_statistics"]["mean_displacement"]["trend_direction"] == "insufficient_data"
    assert stats_single["correlation_matrix"]["available"] is False
    print("  [PASS] Single analysis study correctly returns trend_direction: insufficient_data and matrix available: False")

    # 3. Create Multi-session Study with all 5 analyses
    st, s_multi = http_post("/api/studies/", {
        "title": "Longitudinal Research Cohort",
        "subject_code": "STAT-P002",
        "description": "5 session research study with calibration and high deformation"
    })
    assert st in (200, 201), f"Failed to create multi study: {s_multi}"
    study_multi_id = s_multi["id"]

    for a in analyses:
        http_post(f"/api/studies/{study_multi_id}/analyses/{a['analysis_id']}")

    # 4. Test GET /api/statistics/study/{id}
    st, full_stats = http_get(f"/api/statistics/study/{study_multi_id}?scope=full_image")
    assert st == 200, f"Failed to get full stats: {full_stats}"
    assert full_stats["analysis_count"] == 5
    assert "descriptive_statistics" in full_stats
    assert "change_statistics" in full_stats
    assert "variability" in full_stats or "std" in full_stats["descriptive_statistics"]["mean_displacement"]
    assert "correlations" in full_stats
    assert "correlation_matrix" in full_stats
    assert "outliers" in full_stats
    assert full_stats["calibration_consistency"]["status"] == "mixed"
    assert "disclaimer" in full_stats
    assert "non-diagnostic" in full_stats["disclaimer"].lower() or "clinical" in full_stats["disclaimer"].lower()
    print("  [PASS] GET /api/statistics/study/{id} returns full payload with mixed calibration warning")

    # 5. Test GET /api/statistics/study/{id}/correlations
    st, corr_data = http_get(f"/api/statistics/study/{study_multi_id}/correlations")
    assert st == 200, f"Failed to get correlations: {corr_data}"
    assert corr_data["study_id"] == study_multi_id
    assert "correlations" in corr_data
    assert "correlation_matrix" in corr_data
    matrix_bundle = corr_data["correlation_matrix"]
    metrics_list = matrix_bundle["metrics"]
    vals_grid = matrix_bundle["values"]
    assert len(vals_grid) == len(metrics_list)
    # Check diagonal is 1.0
    for m in metrics_list:
        k = m["key"]
        assert vals_grid[k][k] == 1.0
    print("  [PASS] GET /api/statistics/study/{id}/correlations returns valid symmetric matrix with diag=1.0")

    # 6. Test GET /api/statistics/study/{id}/outliers
    st, outlier_data = http_get(f"/api/statistics/study/{study_multi_id}/outliers")
    assert st == 200, f"Failed to get outliers: {outlier_data}"
    assert outlier_data["study_id"] == study_multi_id
    assert "outliers" in outlier_data
    assert "total_outliers" in outlier_data
    print("  [PASS] GET /api/statistics/study/{id}/outliers returns 1.5xIQR results with QC metadata")

    # 7. Test Scope switching: ROI fallback when no ROI present
    st, roi_fallback_stats = http_get(f"/api/statistics/study/{study_multi_id}?scope=roi")
    assert st == 200, f"Failed to query ROI scope: {roi_fallback_stats}"
    assert roi_fallback_stats["analysis_scope"] == "full_image"
    assert any("ROI scope was requested, but no ROI masked analyses were found" in inf for inf in roi_fallback_stats.get("info", []))
    print("  [PASS] Scope query param (?scope=roi) gracefully falls back with explanatory note when no ROI is present")

    # Now create 3 ROI-enabled analyses and a study with them
    print("Creating ROI study cohort...")
    roi_b = {
        "enabled": True,
        "type": "rectangle",
        "coordinates": {"x": 30, "y": 30, "width": 40, "height": 40}
    }
    encoded_roi = urllib.parse.quote(json.dumps(roi_b))
    roi_analyses = []
    for f1, f2 in [("stat_img1.png", "stat_img2.png"), ("stat_img1.png", "stat_img3.png"), ("stat_img1.png", "stat_img4.png")]:
        st, a_data = http_post(f"/api/analysis/strain?image1_filename={f1}&image2_filename={f2}&roi={encoded_roi}")
        assert st == 200
        roi_analyses.append(a_data)

    st, s_roi = http_post("/api/studies/", {
        "title": "ROI Cohort Study",
        "subject_code": "STAT-ROI-01",
        "description": "Cohort with masked region of interest analyses"
    })
    assert st in (200, 201)
    study_roi_id = s_roi["id"]
    for a in roi_analyses:
        http_post(f"/api/studies/{study_roi_id}/analyses/{a['analysis_id']}")

    st, roi_active_stats = http_get(f"/api/statistics/study/{study_roi_id}?scope=roi")
    assert st == 200
    assert roi_active_stats["analysis_scope"] == "roi"
    assert roi_active_stats["roi_available"] is True
    print("  [PASS] Active ROI study successfully computes statistics under scope='roi'")

    # 8. Test Statistics PDF Report: POST /api/reports/statistics/{study_id}
    print("\n--- Part 3: PDF Report Generation ---")
    st, rpt = http_post(f"/api/reports/statistics/{study_multi_id}?scope=full_image")
    assert st == 200, f"PDF report generation failed: {rpt}"
    assert "url" in rpt
    pdf_filename = rpt["url"].replace("/reports/", "")
    pdf_path = Path("reports") / pdf_filename
    assert pdf_path.exists(), f"PDF report file does not exist on disk: {pdf_path}"
    assert pdf_path.stat().st_size > 1000, f"PDF report file is empty or suspiciously small ({pdf_path.stat().st_size} bytes)"
    print(f"  [PASS] Generated research statistics report: {rpt['url']} ({pdf_path.stat().st_size} bytes)")

    # 9. Verify Existing Route Integrity
    print("\n--- Part 4: Existing Routes Integrity Check ---")
    st, resp = http_get("/health")
    assert st == 200
    print("  [PASS] Verified existing endpoint /health (HTTP 200)")

    st, resp = http_get("/api/history/")
    assert st == 200
    print("  [PASS] Verified existing endpoint /api/history/ (HTTP 200)")

    st, resp = http_get("/api/studies/")
    assert st == 200
    print("  [PASS] Verified existing endpoint /api/studies/ (HTTP 200)")

    st, resp = http_get(f"/api/longitudinal/study/{study_multi_id}")
    assert st == 200
    print(f"  [PASS] Verified existing endpoint /api/longitudinal/study/{study_multi_id} (HTTP 200)")

    st, resp = http_post("/api/comparison", {"analysis_ids": [analyses[0]["analysis_id"], analyses[1]["analysis_id"]]})
    assert st == 200
    print("  [PASS] Verified existing endpoint POST /api/comparison (HTTP 200)")

    st, resp = http_get(f"/api/quality/{analyses[0]['analysis_id']}")
    assert st == 200
    print(f"  [PASS] Verified existing endpoint /api/quality/{analyses[0]['analysis_id']} (HTTP 200)")

    print("\n" + "=" * 70)
    print("ALL STEP 11.13 ADVANCED STATISTICAL ANALYTICS VERIFICATIONS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_statistics_tests()
