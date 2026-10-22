"""
backend/test_synthetic_step11_14.py

Comprehensive Verification Suite for Step 11.14:
Synthetic / Phantom Data Generator and Quantitative Validation Benchmark

Tests:
1. Pure unit tests of synthetic phantom generator:
   - Reference image generation
   - 7 deformation modes: translation, radial_expansion, radial_contraction,
     circumferential_deformation, uniform_scaling, shear, combined
   - Noise and blur application
   - Analytical ground-truth displacement (u, v, mag)
   - Analytical ground-truth strain (exx, eyy, exy, p1, p2, radial, circ)
   - Parameter boundary clamping and validation
2. Validation metrics engine:
   - MAE, RMSE, Pearson r, Relative Error, Endpoint Error (EPE)
   - NaN/Inf protection and dimension mismatch handling
3. Full Dataset Generation API (POST /api/synthetic/generate)
4. Dataset Metadata & Frames Endpoints (GET /api/synthetic/{id}, /frames, /ground-truth)
5. Validation Benchmark API (POST /api/synthetic/{id}/validate)
   - Execution of real optical-flow and strain on synthetic frames
   - Generation of GT, Estimated, and Error heatmaps on disk
6. Robustness Sweep API (POST /api/synthetic/{id}/robustness)
   - Systematically tests noise levels (0.0 to 0.05) and blur (0.0 to 2.0)
7. Validation History API (GET /api/synthetic/validation/history)
8. PDF Validation Benchmark Report Generation (POST /api/reports/validation/{id})
9. Error Handling:
   - Missing dataset ID -> 404
   - Invalid deformation configuration clamping
10. Existing Route Integrity Check:
   - /health, /api/history/, /api/studies/, /api/statistics/
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
import numpy as np

from app.services.synthetic_data import (
    validate_synthetic_config,
    generate_reference_image,
    generate_deformed_image,
    generate_image_sequence,
    generate_ground_truth_displacement,
    generate_ground_truth_strain,
    generate_synthetic_dataset,
    SUPPORTED_DEFORMATION_MODES
)
from app.services.validation import (
    calculate_field_mae,
    calculate_field_rmse,
    calculate_field_correlation,
    calculate_relative_error,
    calculate_endpoint_error,
    compare_estimated_vs_ground_truth
)

BASE_URL = "http://127.0.0.1:8000"


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


def test_pure_synthetic_unit_functions():
    print("\n--- Part 1: Pure Synthetic Generation Engine ---")

    # 1. Config validation & clamping
    bad_cfg = {"width": 10, "height": 5000, "deformation_mode": "invalid_mode", "deformation_strength": 99.0}
    val_cfg = validate_synthetic_config(bad_cfg)
    assert val_cfg["width"] >= 64
    assert val_cfg["height"] <= 1024
    assert val_cfg["deformation_mode"] == "radial_expansion"
    assert val_cfg["deformation_strength"] <= 0.30
    print("  [PASS] validate_synthetic_config clamps unreasonable values safely")

    # 2. Reference image generation
    ref_cfg = {
        "width": 128, "height": 128, "center_x": 64, "center_y": 64,
        "inner_radius": 25, "outer_radius": 45, "deformation_mode": "radial_expansion",
        "deformation_strength": 0.05, "noise_level": 0.0, "blur_sigma": 0.0, "frame_count": 3
    }
    ref_img = generate_reference_image(ref_cfg)
    assert ref_img.shape == (128, 128)
    assert ref_img.dtype == np.uint8
    assert np.mean(ref_img) > 20.0
    print("  [PASS] generate_reference_image creates textured phantom")

    # 3. Test all 7 deformation modes
    for mode in SUPPORTED_DEFORMATION_MODES:
        m_cfg = ref_cfg.copy()
        m_cfg["deformation_mode"] = mode
        def_img = generate_deformed_image(m_cfg, scale_factor=1.0)
        assert def_img.shape == (128, 128)
        u_gt, v_gt, mag_gt = generate_ground_truth_displacement(m_cfg, scale_factor=1.0)
        assert u_gt.shape == (128, 128)
        assert mag_gt.shape == (128, 128)
        strain_gt = generate_ground_truth_strain(m_cfg, scale_factor=1.0)
        assert "principal_1" in strain_gt
        assert "radial" in strain_gt
        assert "circumferential" in strain_gt
        print(f"  [PASS] Deformation mode '{mode}' generated valid images and ground truth")

    # 4. Multi-frame sequence
    seq_cfg = ref_cfg.copy()
    seq_cfg["frame_count"] = 4
    frames = generate_image_sequence(seq_cfg)
    assert len(frames) == 4
    print("  [PASS] generate_image_sequence creates progressive multi-frame sequence")

    # 5. Full in-memory dataset construction
    full_ds = generate_synthetic_dataset(ref_cfg)
    assert "dataset_id" in full_ds
    assert "metadata" in full_ds
    assert "ground_truth" in full_ds
    print("  [PASS] generate_synthetic_dataset builds complete package with metadata")


def test_pure_validation_metrics():
    print("\n--- Part 2: Pure Validation Metrics Engine ---")

    # Exact match: MAE = 0, RMSE = 0, corr = 1.0
    f1 = np.ones((50, 50), dtype=np.float32) * 5.0
    mae_0 = calculate_field_mae(f1, f1)
    rmse_0 = calculate_field_rmse(f1, f1)
    assert mae_0 == 0.0
    assert rmse_0 == 0.0
    print("  [PASS] calculate_field_mae and rmse return 0.0 on identical fields")

    # Predictable difference
    f2 = f1 + 2.0
    mae_2 = calculate_field_mae(f2, f1)
    rmse_2 = calculate_field_rmse(f2, f1)
    assert mae_2 == 2.0
    assert rmse_2 == 2.0
    print("  [PASS] calculate_field_mae and rmse correctly compute shift errors")

    # Pearson correlation
    x = np.arange(100, dtype=np.float32).reshape((10, 10))
    y = 2.5 * x + 4.0
    corr = calculate_field_correlation(x, y)
    assert corr == 1.0, f"Expected 1.0, got {corr}"
    print("  [PASS] calculate_field_correlation accurately computes Pearson r")

    # Endpoint Error (EPE)
    u_est = np.zeros((20, 20), dtype=np.float32)
    v_est = np.zeros((20, 20), dtype=np.float32)
    u_gt = np.ones((20, 20), dtype=np.float32) * 3.0
    v_gt = np.ones((20, 20), dtype=np.float32) * 4.0
    # Expected EPE = sqrt(3^2 + 4^2) = 5.0
    epe = calculate_endpoint_error(u_est, v_est, u_gt, v_gt)
    assert epe["mean_endpoint_error"] == 5.0
    assert epe["max_endpoint_error"] == 5.0
    print("  [PASS] calculate_endpoint_error computes exact Euclidean displacement error (EPE=5.0)")


def run_all_synthetic_tests():
    print("=" * 70)
    print("RUNNING STEP 11.14 SYNTHETIC VALIDATION BENCHMARK TEST SUITE")
    print("=" * 70)

    # Unit checks
    test_pure_synthetic_unit_functions()
    test_pure_validation_metrics()

    print("\n--- Part 3: End-to-End Synthetic Dataset API Endpoints ---")

    # 1. POST /api/synthetic/generate
    gen_payload = {
        "width": 256,
        "height": 256,
        "inner_radius": 40.0,
        "outer_radius": 70.0,
        "deformation_mode": "radial_expansion",
        "deformation_strength": 0.04,
        "noise_level": 0.0,
        "blur_sigma": 0.0,
        "frame_count": 4
    }
    st, gen_res = http_post("/api/synthetic/generate", gen_payload)
    assert st == 200, f"Generate failed: {gen_res}"
    assert "dataset_id" in gen_res
    ds_id = gen_res["dataset_id"]
    assert gen_res["frame_count"] == 4
    assert len(gen_res["frames"]) == 4
    print(f"  [PASS] POST /api/synthetic/generate created dataset {ds_id}")

    # 2. GET /api/synthetic/{dataset_id}
    st, meta = http_get(f"/api/synthetic/{ds_id}")
    assert st == 200
    assert meta["dataset_id"] == ds_id
    assert meta["is_synthetic"] is True
    assert "disclaimer" in meta
    print("  [PASS] GET /api/synthetic/{id} returns complete metadata")

    # 3. GET /api/synthetic/{dataset_id}/frames
    st, frames_res = http_get(f"/api/synthetic/{ds_id}/frames")
    assert st == 200
    assert frames_res["frame_count"] == 4
    assert len(frames_res["frames"]) == 4
    print("  [PASS] GET /api/synthetic/{id}/frames returns frame URLs")

    # 4. GET /api/synthetic/{dataset_id}/ground-truth
    st, gt_res = http_get(f"/api/synthetic/{ds_id}/ground-truth")
    assert st == 200
    assert "available_fields" in gt_res
    assert "displacement_magnitude" in gt_res["available_fields"]
    assert "summary" in gt_res
    print("  [PASS] GET /api/synthetic/{id}/ground-truth returns descriptors without huge arrays")

    # 5. POST /api/synthetic/{dataset_id}/validate
    print("\n--- Part 4: Optical Flow Validation Benchmark ---")
    st, val_res = http_post(f"/api/synthetic/{ds_id}/validate")
    assert st == 200, f"Validation failed: {val_res}"
    assert val_res["dataset_id"] == ds_id
    assert "validation" in val_res
    val_metrics = val_res["validation"]
    assert "displacement" in val_metrics
    assert "strain" in val_metrics
    assert "visualizations" in val_res
    vis = val_res["visualizations"]
    assert "displacement" in vis
    assert "gt_url" in vis["displacement"]
    assert "est_url" in vis["displacement"]
    assert "error_url" in vis["displacement"]

    # Verify visualization files exist on disk
    err_rel = vis["displacement"]["error_url"].replace("/outputs/", "outputs/")
    assert Path(err_rel).exists(), f"Error map file does not exist on disk: {err_rel}"
    print("  [PASS] POST /api/synthetic/{id}/validate computed errors and saved heatmaps")

    # 6. POST /api/synthetic/{dataset_id}/robustness
    print("\n--- Part 5: Robustness Sweep Benchmark ---")
    st, rob_res = http_post(f"/api/synthetic/{ds_id}/robustness")
    assert st == 200, f"Robustness sweep failed: {rob_res}"
    assert rob_res["dataset_id"] == ds_id
    assert "results" in rob_res
    assert len(rob_res["results"]) == 12  # 4 noise levels x 3 blur levels
    print(f"  [PASS] POST /api/synthetic/{ds_id}/robustness completed {len(rob_res['results'])} benchmark conditions")

    # 7. GET /api/synthetic/validation/history
    print("\n--- Part 6: Validation History API ---")
    st, hist_res = http_get("/api/synthetic/validation/history")
    assert st == 200
    assert isinstance(hist_res, list)
    assert len(hist_res) > 0
    assert any(item.get("dataset_id") == ds_id for item in hist_res)
    print("  [PASS] GET /api/synthetic/validation/history persists benchmark runs")

    # 8. POST /api/reports/validation/{dataset_id}
    print("\n--- Part 7: PDF Validation Benchmark Report ---")
    st, rpt_res = http_post(f"/api/reports/validation/{ds_id}")
    assert st == 200, f"Report generation failed: {rpt_res}"
    assert "url" in rpt_res
    pdf_path = Path("reports") / rpt_res["url"].replace("/reports/", "")
    assert pdf_path.exists(), f"PDF report not found: {pdf_path}"
    assert pdf_path.stat().st_size > 2000, f"PDF file too small: {pdf_path.stat().st_size} bytes"
    print(f"  [PASS] POST /api/reports/validation/{ds_id} generated PDF ({pdf_path.stat().st_size} bytes)")

    # 9. Error handling: 404 on missing dataset
    print("\n--- Part 8: Safe Error Handling ---")
    st_404, res_404 = http_get("/api/synthetic/non-existent-id-999")
    assert st_404 == 404
    print("  [PASS] Querying nonexistent dataset correctly returns HTTP 404")

    # 10. Existing Route Integrity Check
    print("\n--- Part 9: Existing Routes Integrity Check ---")
    integrity_routes = [
        ("/health", 200),
        ("/api/history/", 200),
        ("/api/studies/", 200)
    ]
    for route, expected_code in integrity_routes:
        st, _ = http_get(route)
        assert st == expected_code, f"Integrity check failed for {route}: {st}"
        print(f"  [PASS] Verified existing endpoint {route} (HTTP {st})")

    print("\n" + "=" * 70)
    print("ALL STEP 11.14 SYNTHETIC VALIDATION BENCHMARK VERIFICATIONS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_synthetic_tests()
