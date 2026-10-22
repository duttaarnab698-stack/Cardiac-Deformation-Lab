# Live Demonstration Guide & Presentation Script
## Cardiac Deformation Lab (v1.0.4)
### 5-to-10 Minute End-to-End Walkthrough for Technical & Scientific Audiences

---

> [!NOTE]
> **PURPOSE OF THIS GUIDE**  
> This script provides a structured, reproducible walkthrough for demonstrating the full computational capabilities of the **Cardiac Deformation Lab** to engineering teams, academic reviewers, and research collaborators.

---

## Pre-Demo Quick Checklist

Before initiating the presentation, verify that both the backend and frontend are active:
- **Backend**: Running on `http://localhost:8000` (FastAPI with interactive Swagger docs at `/docs`)
- **Frontend**: Running on `http://localhost:5173` (Vite dev server)
- **Demo Credentials**:
  - Email: `demo_researcher@lab.internal`
  - Password: `ResearchPassword123!`
  - Role: `researcher` (or `admin` / `reviewer`)

---

## Demonstration Script & Timeline (Total: 8–10 Minutes)

### Phase 1: Authentication & Workspace Isolation (0:00 – 1:00)
1. **Navigate to App**: Open browser at `http://localhost:5173`.
2. **Highlight Role-Based Access Control (RBAC)**:
   - Point out that user accounts are isolated via JSON-backed research identity management and hashed credentials.
   - Log in using `demo_researcher@lab.internal`.
3. **Workspace Dashboard**:
   - Show the primary workspace dashboard featuring recent studies, analysis counts, and quick navigation actions.
   - Emphasize the clear scientific disclaimer banner anchored in the header and footer:  
     *"Research Prototype — Not For Diagnostic Use"*.

---

### Phase 2: Study Management & Data Organization (1:00 – 2:00)
1. **Navigate to Studies**: Click **Studies** in the sidebar.
2. **Create New Research Study**:
   - Click **Create Study**.
   - Input Study Code: `STUDY-DEMO-2026`, Name: `Biventricular Mechanics Evaluation`, Description: `Investigating apparent optical strain in short-axis cine frames`.
3. **Study Isolation**:
   - Note that research studies isolate analysis records, temporal cine loops, and exports per researcher or research group.

---

### Phase 3: Image Upload & Preprocessing (2:00 – 3:00)
1. **Navigate to Analysis**: Click **Analysis** in the sidebar.
2. **Upload Frame Pair**:
   - Select **Reference Frame (End-Diastole)** and **Target Frame (End-Systole)** from demo dataset (or upload two cardiac ultrasound/MRI frames).
3. **Preprocessing Controls**:
   - Demonstrate the integrated preprocessing pipeline:
     - **CLAHE** (Contrast Limited Adaptive Histogram Equalization) for enhancing low-contrast acoustic speckle.
     - **Gaussian Spatial Smoothing** ($\sigma = 1.0\text{--}1.5$) to suppress high-frequency acquisition noise.
   - Click **Preview Preprocessed Images** to observe enhanced tissue contrast.

---

### Phase 4: Dense Motion Estimation & Strain Tensor Calculation (3:00 – 4:30)
1. **Execute Analysis**:
   - Set motion parameters: Algorithm = `Farnebäck`, Pyramid Scale = `0.5`, Window Size = `15`, Iterations = `5`.
   - Click **Run Deformation Analysis**.
2. **Inspect Interactive Deformation Maps**:
   - **Displacement Vector Field**: Display the 2D quiver plot showcasing vector directions and magnitude heatmaps.
   - **Cartesian Normal Strains**: Switch to $\varepsilon_{xx}$ (horizontal shortening/expansion) and $\varepsilon_{yy}$ (vertical shortening/expansion).
   - **In-Plane Shear Strain**: View $\varepsilon_{xy}$ showing rotational deformation.
   - **Principal Strains**: View $\varepsilon_1$ (tensile principal strain) and $\varepsilon_2$ (compressive principal strain).
   - **Equivalent (von Mises) Strain**: Show unified deformation intensity.
   - **Radial & Circumferential Decomposition**: Display polar coordinate transformation showing radial thickening ($\varepsilon_{rr} > 0$) and circumferential shortening ($\varepsilon_{\theta\theta} < 0$).

---

### Phase 5: Region of Interest (ROI) & Spatial Calibration (4:30 – 5:30)
1. **Spatial Calibration**:
   - Toggle **Enable Calibration**.
   - Set Pixel Spacing: `0.45 mm/px`, Frame Interval: `33.3 ms` ($30\text{ FPS}$).
   - Notice metrics dynamically convert from pixels to physical units: $\text{mm}$ displacement and $\text{mm/s}$ apparent velocity.
2. **Interactive ROI Masking**:
   - Draw an elliptical or polygonal ROI over the simulated left ventricular myocardium.
   - Observe real-time statistical recalculation: ROI Mean Strain, Peak Strain, Standard Deviation, and Area.

---

### Phase 6: Temporal Cine Loops & Automated Quality Control (5:30 – 6:45)
1. **Temporal Cine Loop Analysis**:
   - Navigate to **Temporal Analysis**. Load a multi-frame sequence.
   - Track ROI across cardiac cycle using Lucas-Kanade pyramidal tracking.
   - Review temporal strain curves: Time-to-peak shortening, instantaneous velocity, strain rate ($d\varepsilon/dt$).
2. **Automated Quality Control (QC) Layer**:
   - Open the **Quality Control** panel on the analysis results.
   - Show the composite QC Score (e.g., $88/100$ — *Optimal/High Quality*).
   - Break down sub-indices: Image Contrast ($92$), Motion Dispersion ($85$), Flow Coherence ($90$), Mask Integrity ($100$), Spatial Calibration ($100$).
   - Point out validation warnings (e.g., alert if displacement approaches zero or exceeds physiological bounds).

---

### Phase 7: Quantitative Benchmarking: Synthetic & Real-Image (6:45 – 8:00)
1. **Synthetic Phantom Validation**:
   - Navigate to **Synthetic Validation**.
   - Generate an analytical ring phantom with known contraction ($15\%$) and rotation ($5^\circ$).
   - Run the algorithmic benchmark.
   - Show the side-by-side error metrics:
     - End-Point Error (EPE): $< 0.15\text{ px}$
     - Strain RMSE: $< 0.008$
     - Proves numerical correctness against exact continuum mathematical formulas.
2. **Real-Image Annotation Workflow**:
   - Navigate to **Real-Image Validation**.
   - Show manual ground-truth reference landmarks and contours placed on real clinical research images.
   - Compare optical flow tracking trajectories against human expert annotations to assess algorithm concordance.

---

### Phase 8: Analysis Explorer, Reporting & Scientific Export (8:00 – 9:15)
1. **Interactive Analysis Explorer**:
   - Open `/explorer/:analysisId` to demonstrate synchronized multi-layer visualization, cross-sectional line profile sampling, and interactive histogram filtering.
2. **Publication-Ready Research Report**:
   - Click **Generate Research Report**.
   - Open the generated multi-page PDF featuring high-resolution vector figures, parameter audit trails, QC breakdown, and the embedded non-clinical disclaimer.
3. **Comprehensive Scientific Export Package**:
   - Click **Export Study ZIP Archive**.
   - Inspect the downloaded archive containing:
     - `analysis_metadata.json`
     - Calibrated CSV data tables (`displacement_raw.csv`, `strain_tensor.csv`)
     - Publication-ready 300 DPI visualization figures (`displacement_quiver.png`, `principal_strain_heatmap.png`)
     - Complete reproducibility manifest with software version and timestamps.

---

### Phase 9: Closing Discussion on Limitations & Open Science (9:15 – 10:00)
1. **Conclude with Methodological Transparency**:
   - Summarize the fundamental distinction between apparent optical image motion and true 3D in-vivo tissue strain.
   - Reiterate the absence of out-of-plane 3D capture in planar 2D cine loops.
   - Emphasize that the platform provides open, reproducible, and verifiable engineering infrastructure for biomechanics research without diagnostic overclaims.
2. **Open for Technical Q&A**.

