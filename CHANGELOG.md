# Changelog
All notable changes to the **Cardiac Deformation Lab** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.4] - 2026-10-18
### Added
- **Step 11.20 — Final Testing, Documentation, Demo & Deployment Readiness**:
  - Comprehensive master automated test suite `backend/test_complete_suite_step11_20.py` verifying all 16 core functional modules with 100% pass rate.
  - Complete scientific documentation in `docs/SCIENTIFIC_METHODS.md` detailing continuum mechanics, infinitesimal strain tensors, Farnebäck optical flow, and polar coordinate transformations.
  - Comprehensive physical assumptions and limitations documentation in `docs/LIMITATIONS.md` outlining apparent motion vs. true physical strain, 2D planar constraints, and speckle decorrelation.
  - 5-to-10 minute presentation demonstration script in `docs/DEMO_GUIDE.md`.
  - Comprehensive Project Status & Verification Matrix in `docs/PROJECT_STATUS.md`.
  - 35-section master `README.md` with system architecture diagrams, API reference tables, and deployment blueprints.
- **Step 11.19 — Production Hardening, Performance & Security**:
  - SlowAPI rate limiting middleware on compute-heavy analysis and upload endpoints.
  - Magic-byte validation (`imghdr`/signature checks) and canonical path traversal defenses.
  - Standardized JSON error response schemas across all API routers.
  - In-memory LRU caching for repeated analytical computations.
- **Step 11.18 — Publication-Ready Research Report & Scientific Export System**:
  - Multi-page PDF generation via ReportLab in `backend/app/services/research_report.py`.
  - Comprehensive scientific export ZIP archives bundling calibrated CSV tables, 300 DPI figures, and JSON metadata.
  - Frontend report preview, single-click downloads, and audit trail export.
- **Step 11.17 — Interactive Analysis Explorer**:
  - High-performance multi-layer viewer in `frontend/src/pages/AnalysisExplorer.jsx`.
  - Dynamic cross-sectional line profile extraction and intensity histograms.
  - Synchronized dual-window baseline vs. follow-up image comparison.
- **Step 11.16 — Research Workspace, User Accounts, Authentication & RBAC**:
  - JWT bearer token authentication and bcrypt password hashing in `backend/app/services/auth.py`.
  - Role-based access control (`admin`, `researcher`, `reviewer`) with study ownership isolation.
  - Frontend authentication context, login/register views, and protected routing.
- **Step 11.15 — Real-Image Annotation & Reference Benchmark Workflow**:
  - Manual landmark and contour annotation service in `backend/app/services/annotations.py`.
  - Concordance benchmark comparing optical flow trajectories against human reference annotations.
  - Dedicated frontend annotation editor and comparison dashboard in `RealValidation.jsx`.
- **Step 11.14 — Synthetic / Phantom Data Generator & Quantitative Benchmark**:
  - Controllable kinematic phantom generator in `backend/app/services/synthetic_data.py`.
  - Exact analytical ground-truth strain fields (radial contraction, shear, rotation).
  - Quantitative benchmark error metrics: Endpoint Error (EPE), RMSE, and MAE.
- **Step 11.13 — Advanced Statistical & Research Analytics**:
  - Statistical analysis service in `backend/app/services/statistics.py`.
  - Pearson & Spearman rank correlations, longitudinal change metrics, variability, and effect sizes (Cohen's $d$).
- **Step 11.12 — Longitudinal / Multi-Session Study Analysis**:
  - Multi-session trend tracking service in `backend/app/services/longitudinal.py`.
  - Longitudinal timeline series, delta progression, and multi-visit comparisons.
- **Step 11.11 — Automated Analysis Quality Control & Validation Layer**:
  - 8-metric technical fidelity scoring engine in `backend/app/services/quality_control.py`.
  - Composite QC score ($0\text{--}100$), quality tier categorization, and validation warning flags.

### Changed
- Standardized non-clinical research prototype disclaimer across all API endpoints, frontend views, PDF headers, and documentation.
- Synchronized project version to `v1.0.4` across backend, frontend footer, package manifests, and reports.
- Resolved scalar vs. dictionary metric extraction in longitudinal analysis and comparison services.
- Updated FastAPI route query parameters to replace deprecated `regex` with `pattern`.

---

## [1.0.0] - 2026-10-15
### Added
- Initial core computational biomechanics implementation:
  - Step 11.1: Image upload, validation, CLAHE and Gaussian preprocessing.
  - Step 11.2: Farnebäck dense optical flow motion estimation and quiver field visualization.
  - Step 11.3: Cauchy infinitesimal strain tensor calculation ($\varepsilon_{xx}, \varepsilon_{yy}, \varepsilon_{xy}$).
  - Step 11.4: Principal strain decomposition ($\varepsilon_1, \varepsilon_2$) and principal angle calculation.
  - Step 11.5: Advanced deformation invariants (equivalent von Mises strain, volumetric area dilatation).
  - Step 11.6: Polar coordinate conversion (radial $\varepsilon_{rr}$ and circumferential $\varepsilon_{\theta\theta}$ strain).
  - Step 11.7: Multi-frame temporal sequence analysis and displacement curve generation.
  - Step 11.8: Interactive rectangular, elliptical, and polygonal Region of Interest (ROI) masking.
  - Step 11.9: Pyramidal Lucas-Kanade automatic ROI tracking across cardiac cycles.
  - Step 11.10: Spatial pixel-to-millimeter calibration and physical velocity estimation.

