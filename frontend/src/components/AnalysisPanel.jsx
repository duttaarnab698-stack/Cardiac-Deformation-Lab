import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { uploadImage, analyzeStrain, getStudies, addAnalysisToStudy } from "../services/api";
import AnalysisMaps from "./AnalysisMaps";
import FingerprintChart from "./FingerprintChart";
import SummaryCards from "./SummaryCards";
import SectionNav from "./SectionNav";
import InterpretationPanel from "./InterpretationPanel";
import MethodologySection from "./MethodologySection";
import CalibrationPanel from "./CalibrationPanel";
import ROISelector from "./ROISelector";
import ROIComparisonView from "./ROIComparisonView";
import { useAnalysis } from "../context/AnalysisContext";

export default function AnalysisPanel() {
  const { setLatestAnalysisResult } = useAnalysis();

  // Images state
  const [image1, setImage1] = useState(null);
  const [image2, setImage2] = useState(null);
  const [image1Preview, setImage1Preview] = useState(null);
  const [image2Preview, setImage2Preview] = useState(null);

  // Loading & error state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [processingStage, setProcessingStage] = useState(0);

  // Region of Interest (ROI) State
  const [roi, setRoi] = useState({
    enabled: false,
    type: "rectangle",
    coordinates: null,
  });

  // Calibration State
  const [calibration, setCalibration] = useState({
    enabled: false,
    pixel_spacing_x: "",
    pixel_spacing_y: "",
    unit: "mm",
  });

  // Study Selector State
  const [availableStudies, setAvailableStudies] = useState([]);
  const [selectedStudyId, setSelectedStudyId] = useState("");

  // Advanced Options Accordion
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Generate object preview URLs when files change
  useEffect(() => {
    if (image1 instanceof File) {
      const url = URL.createObjectURL(image1);
      setImage1Preview(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setImage1Preview(null);
    }
  }, [image1]);

  useEffect(() => {
    if (image2 instanceof File) {
      const url = URL.createObjectURL(image2);
      setImage2Preview(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setImage2Preview(null);
    }
  }, [image2]);

  // Load studies
  useEffect(() => {
    getStudies()
      .then((data) => setAvailableStudies(data || []))
      .catch(() => {});
  }, []);

  // Selected study object
  const activeStudy = useMemo(() => {
    return availableStudies.find((s) => s.id === selectedStudyId) || null;
  }, [availableStudies, selectedStudyId]);

  const handleAnalyze = async () => {
    if (!image1 || !image2) {
      setError("Please select both Reference Frame (Image 1) and Target Frame (Image 2).");
      return;
    }

    // Validate calibration inputs if enabled
    let calPayload = null;
    if (calibration.enabled) {
      const sx = parseFloat(calibration.pixel_spacing_x);
      const sy = parseFloat(calibration.pixel_spacing_y);
      if (isNaN(sx) || isNaN(sy) || sx <= 0 || sy <= 0) {
        setError("Spatial calibration requires valid positive numbers (> 0) for Pixel Spacing X and Y.");
        return;
      }
      calPayload = {
        enabled: true,
        pixel_spacing_x: sx,
        pixel_spacing_y: sy,
        unit: calibration.unit,
      };
    }

    // Validate optional ROI configuration if enabled
    let roiPayload = null;
    if (roi.enabled) {
      if (!roi.coordinates) {
        setError("ROI analysis is enabled, but no region has been defined. Please draw an ROI on the Reference Image canvas.");
        return;
      }
      roiPayload = roi;
    }

    setLoading(true);
    setError(null);
    setProcessingStage(1);

    try {
      // 1. Upload both images to backend
      setProcessingStage(1); // Uploading
      const upload1 = await uploadImage(image1);
      const upload2 = await uploadImage(image2);

      const savedFilename1 = upload1.saved_filename;
      const savedFilename2 = upload2.saved_filename;

      if (!savedFilename1 || !savedFilename2) {
        throw new Error("Failed to retrieve saved filenames from upload service.");
      }

      // 2. Run motion estimation & strain analysis
      setProcessingStage(2); // Estimating Farnebäck flow
      setTimeout(() => setProcessingStage(3), 600); // Computing displacement & strain

      const analysisData = await analyzeStrain(savedFilename1, savedFilename2, calPayload, roiPayload);
      setProcessingStage(4); // Generating tensors & colormaps
      setResult(analysisData);
      setLatestAnalysisResult(analysisData);

      // 3. Link to selected study if requested
      if (selectedStudyId && analysisData.analysis_id) {
        try {
          await addAnalysisToStudy(selectedStudyId, analysisData.analysis_id);
        } catch {
          // Non-blocking error
        }
      }
    } catch (err) {
      setError(err.message || "An unexpected error occurred during deformation analysis.");
    } finally {
      setLoading(false);
      setProcessingStage(0);
    }
  };

  const fp = result?.cardiac_deformation_fingerprint?.fingerprint;
  const disp = result?.displacement;
  const strainStats = result?.strain_statistics;
  const adv = result?.advanced_metrics;

  return (
    <div className="cdl-analysis-panel-root">
      {/* 3-ZONE SCIENTIFIC WORKSPACE */}
      <section className="cdl-workspace-3zone" aria-label="Analysis Configuration and Workspace">
        {/* ====================================================================
            ZONE 1: CONFIGURATION & SETUP (LEFT)
            ==================================================================== */}
        <div className="cdl-zone-left">
          {/* Study Association */}
          <div className="cdl-config-card">
            <div className="cdl-config-card-header">
              <h3 className="cdl-config-card-title">
                <span>📁</span>
                <span>Study Association</span>
              </h3>
              <span className="cdl-config-badge">COHORT</span>
            </div>

            <div className="cdl-config-group">
              <label htmlFor="study-select-input" className="cdl-config-label">
                <span>Assign to Study</span>
                {activeStudy?.subject_code && (
                  <span className="cdl-subject-tag">{activeStudy.subject_code}</span>
                )}
              </label>
              <select
                id="study-select-input"
                className="cdl-config-select"
                value={selectedStudyId}
                onChange={(e) => setSelectedStudyId(e.target.value)}
              >
                <option value="">Standalone Analysis (No Study)</option>
                {availableStudies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} {s.subject_code ? `(${s.subject_code})` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Image Inputs */}
          <div className="cdl-config-card">
            <div className="cdl-config-card-header">
              <h3 className="cdl-config-card-title">
                <span>🖼️</span>
                <span>Frame Selection</span>
              </h3>
              <span className="cdl-config-badge">PAIR</span>
            </div>

            {/* Reference Image Slot */}
            <div className="cdl-config-group">
              <span className="cdl-config-label">
                <span>Reference Frame (Image 1, e.g. ED)</span>
              </span>
              <div className={`cdl-upload-slot ${image1 ? "has-file" : ""}`}>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImage1(e.target.files?.[0] || null)}
                />
                <span className="cdl-upload-icon">{image1 ? "✓" : "📤"}</span>
                <span className="cdl-upload-title">
                  {image1 ? image1.name : "Choose Reference Frame"}
                </span>
                <span className="cdl-upload-subtext">
                  {image1 ? `${(image1.size / 1024).toFixed(1)} KB` : "Drop image or browse"}
                </span>
              </div>
            </div>

            {/* Target Image Slot */}
            <div className="cdl-config-group">
              <span className="cdl-config-label">
                <span>Target Frame (Image 2, e.g. ES)</span>
              </span>
              <div className={`cdl-upload-slot ${image2 ? "has-file" : ""}`}>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImage2(e.target.files?.[0] || null)}
                />
                <span className="cdl-upload-icon">{image2 ? "✓" : "📤"}</span>
                <span className="cdl-upload-title">
                  {image2 ? image2.name : "Choose Target Frame"}
                </span>
                <span className="cdl-upload-subtext">
                  {image2 ? `${(image2.size / 1024).toFixed(1)} KB` : "Drop image or browse"}
                </span>
              </div>
            </div>
          </div>

          {/* Spatial Calibration */}
          <div className="cdl-config-card">
            <div className="cdl-config-card-header">
              <h3 className="cdl-config-card-title">
                <span>📏</span>
                <span>Spatial Calibration</span>
              </h3>
              <span className="cdl-config-badge">
                {calibration.enabled ? calibration.unit : "OFF"}
              </span>
            </div>

            <div className="cdl-toggle-row" onClick={() => setCalibration((c) => ({ ...c, enabled: !c.enabled }))}>
              <span className="cdl-toggle-label">
                <input
                  type="checkbox"
                  className="cdl-checkbox-styled"
                  checked={calibration.enabled}
                  onChange={(e) => setCalibration((c) => ({ ...c, enabled: e.target.checked }))}
                />
                <span>Enable Physical Scaling</span>
              </span>
            </div>

            {calibration.enabled && (
              <>
                <div className="cdl-config-group">
                  <label className="cdl-config-label">Pixel Spacing X ({calibration.unit}/px)</label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.0001"
                    placeholder="e.g. 1.0"
                    className="cdl-config-input"
                    value={calibration.pixel_spacing_x}
                    onChange={(e) => setCalibration((c) => ({ ...c, pixel_spacing_x: e.target.value }))}
                  />
                </div>

                <div className="cdl-config-group">
                  <label className="cdl-config-label">Pixel Spacing Y ({calibration.unit}/px)</label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.0001"
                    placeholder="e.g. 1.0"
                    className="cdl-config-input"
                    value={calibration.pixel_spacing_y}
                    onChange={(e) => setCalibration((c) => ({ ...c, pixel_spacing_y: e.target.value }))}
                  />
                </div>

                <div className="cdl-config-group">
                  <label className="cdl-config-label">Physical Unit</label>
                  <select
                    className="cdl-config-select"
                    value={calibration.unit}
                    onChange={(e) => setCalibration((c) => ({ ...c, unit: e.target.value }))}
                  >
                    <option value="mm">Millimeters (mm)</option>
                    <option value="cm">Centimeters (cm)</option>
                    <option value="μm">Micrometers (μm)</option>
                  </select>
                </div>
              </>
            )}
          </div>

          {/* Region of Interest (ROI) */}
          <div className="cdl-config-card">
            <div className="cdl-config-card-header">
              <h3 className="cdl-config-card-title">
                <span>🎯</span>
                <span>Region of Interest</span>
              </h3>
              <span className="cdl-config-badge">
                {roi.enabled ? roi.type.toUpperCase() : "FULL"}
              </span>
            </div>

            <div className="cdl-toggle-row" onClick={() => setRoi((r) => ({ ...r, enabled: !r.enabled }))}>
              <span className="cdl-toggle-label">
                <input
                  type="checkbox"
                  className="cdl-checkbox-styled"
                  checked={roi.enabled}
                  onChange={(e) => setRoi((r) => ({ ...r, enabled: e.target.checked }))}
                />
                <span>Enable Myocardial ROI Mask</span>
              </span>
            </div>

            {roi.enabled && (
              <div className="cdl-config-group">
                <label className="cdl-config-label">Geometry Shape</label>
                <select
                  className="cdl-config-select"
                  value={roi.type}
                  onChange={(e) => setRoi((r) => ({ ...r, type: e.target.value, coordinates: null }))}
                >
                  <option value="rectangle">Rectangle Boundary</option>
                  <option value="ellipse">Ellipse Boundary</option>
                  <option value="polygon">Custom Polygon Contour</option>
                </select>
              </div>
            )}
          </div>

          {/* Advanced Flow Parameters (Collapsible Accordion) */}
          <div className="cdl-config-card">
            <div
              className="cdl-accordion-header"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <span>⚙️ Optical Flow Parameters</span>
              <span>{showAdvanced ? "▲" : "▼"}</span>
            </div>

            {showAdvanced && (
              <div className="cdl-accordion-body">
                <div><strong>Algorithm:</strong> Farnebäck Dense Flow</div>
                <div><strong>Window Size:</strong> 15 px (Multi-scale)</div>
                <div><strong>Polynomial Sigma:</strong> 1.2 Gaussian</div>
                <div><strong>Pyramid Levels:</strong> 3 Scales (0.5 factor)</div>
                <div><strong>Iterations:</strong> 3 per level</div>
              </div>
            )}
          </div>
        </div>

        {/* ====================================================================
            ZONE 2: CENTER IMAGE WORKSPACE CANVAS
            ==================================================================== */}
        <div className="cdl-zone-center">
          <div className="cdl-image-workspace-card">
            <div className="cdl-workspace-header">
              <h3 className="cdl-workspace-header-title">
                <span>🔬</span>
                <span>Planar Deformation Comparison Canvas</span>
              </h3>
              <span className="cdl-comparison-tag">
                {image1 && image2 ? "Pair Loaded" : "Awaiting Frames"}
              </span>
            </div>

            {/* If ROI is enabled and image1 is loaded, render the interactive ROISelector canvas on Image 1 */}
            {roi.enabled && image1 ? (
              <div>
                <ROISelector
                  imageFile={image1}
                  roi={roi}
                  onChange={setRoi}
                  disabled={loading}
                />
              </div>
            ) : (
              /* Dual Viewport Canvas Stage */
              <div className="cdl-dual-viewport-grid">
                {/* Reference Canvas */}
                <div className="cdl-viewport-box">
                  <div className="cdl-viewport-header">
                    <span className="cdl-viewport-title">
                      <span>1️⃣</span>
                      <span>Reference Frame (ED)</span>
                    </span>
                    <span>{image1 ? image1.name : "Empty"}</span>
                  </div>
                  <div className="cdl-viewport-stage">
                    {image1Preview ? (
                      <img
                        src={image1Preview}
                        alt="Reference Frame"
                        className="cdl-canvas-preview-img"
                      />
                    ) : (
                      <div className="cdl-canvas-empty-state">
                        <span className="cdl-empty-wave-icon">🫀</span>
                        <span className="cdl-empty-stage-text">
                          Upload Reference Frame (e.g. End-Diastole) to inspect geometry
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Transition Connector */}
                <div className="cdl-viewport-connector">
                  <span className="cdl-connector-badge">Dense Flow</span>
                  <span className="cdl-connector-arrow">➔</span>
                </div>

                {/* Target Canvas */}
                <div className="cdl-viewport-box">
                  <div className="cdl-viewport-header">
                    <span className="cdl-viewport-title">
                      <span>2️⃣</span>
                      <span>Target Frame (ES)</span>
                    </span>
                    <span>{image2 ? image2.name : "Empty"}</span>
                  </div>
                  <div className="cdl-viewport-stage">
                    {image2Preview ? (
                      <img
                        src={image2Preview}
                        alt="Target Frame"
                        className="cdl-canvas-preview-img"
                      />
                    ) : (
                      <div className="cdl-canvas-empty-state">
                        <span className="cdl-empty-wave-icon">📈</span>
                        <span className="cdl-empty-stage-text">
                          Upload Target Frame (e.g. End-Systole) for displacement estimation
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ====================================================================
            ZONE 3: STICKY ANALYSIS SUMMARY & RUN CTA (RIGHT)
            ==================================================================== */}
        <div className="cdl-zone-right">
          <div className="cdl-summary-panel-card">
            <div className="cdl-summary-header">
              <h3 className="cdl-summary-title">Analysis Summary</h3>
              <span className="cdl-config-badge">READY</span>
            </div>

            <div className="cdl-summary-list">
              <div className="cdl-summary-item">
                <span className="cdl-summary-item-label">Study Cohort</span>
                <span className="cdl-summary-item-val">
                  {activeStudy ? activeStudy.title : "Standalone"}
                </span>
              </div>

              <div className="cdl-summary-item">
                <span className="cdl-summary-item-label">Subject Code</span>
                <span className="cdl-summary-item-val">
                  {activeStudy?.subject_code || "Unassigned"}
                </span>
              </div>

              <div className="cdl-summary-item">
                <span className="cdl-summary-item-label">Reference Frame</span>
                <span className="cdl-summary-item-val">
                  {image1 ? image1.name : "Not Selected"}
                </span>
              </div>

              <div className="cdl-summary-item">
                <span className="cdl-summary-item-label">Target Frame</span>
                <span className="cdl-summary-item-val">
                  {image2 ? image2.name : "Not Selected"}
                </span>
              </div>

              <div className="cdl-summary-item">
                <span className="cdl-summary-item-label">Calibration</span>
                <span className="cdl-summary-item-val">
                  {calibration.enabled
                    ? `${calibration.pixel_spacing_x || 1} ${calibration.unit}/px`
                    : "Pixel-space (px)"}
                </span>
              </div>

              <div className="cdl-summary-item">
                <span className="cdl-summary-item-label">Analysis Scope</span>
                <span className="cdl-summary-item-val">
                  {roi.enabled ? `ROI (${roi.type})` : "Full Image Field"}
                </span>
              </div>
            </div>

            {/* Run Analysis Action CTA */}
            <button
              type="button"
              className="cdl-btn-run-analysis"
              onClick={handleAnalyze}
              disabled={loading || !image1 || !image2}
            >
              <span>🔬</span>
              <span>{loading ? "Processing Kinematics..." : "Run Analysis"}</span>
            </button>

            {/* Multi-Stage Animated Processing Indicator */}
            {loading && (
              <div className="cdl-processing-box">
                <div className="cdl-processing-title">
                  <div className="cdl-processing-spinner" />
                  <span>Computing Deformation Pipeline</span>
                </div>
                <div className="cdl-stages-list">
                  <div className={`cdl-stage-item ${processingStage >= 1 ? "done" : "running"}`}>
                    <span>{processingStage >= 1 ? "✓" : "•"}</span>
                    <span>Uploading frame pair</span>
                  </div>
                  <div className={`cdl-stage-item ${processingStage >= 2 ? "done" : processingStage === 1 ? "running" : ""}`}>
                    <span>{processingStage >= 2 ? "✓" : "•"}</span>
                    <span>Estimating dense optical flow</span>
                  </div>
                  <div className={`cdl-stage-item ${processingStage >= 3 ? "done" : processingStage === 2 ? "running" : ""}`}>
                    <span>{processingStage >= 3 ? "✓" : "•"}</span>
                    <span>Computing displacement magnitude</span>
                  </div>
                  <div className={`cdl-stage-item ${processingStage >= 4 ? "done" : processingStage === 3 ? "running" : ""}`}>
                    <span>{processingStage >= 4 ? "✓" : "•"}</span>
                    <span>Decomposing principal strain tensor</span>
                  </div>
                </div>
              </div>
            )}

            {/* Error Banner */}
            {error && (
              <div className="cdl-alert-banner cdl-alert-error" style={{ fontSize: 12 }}>
                <span>⚠️ {error}</span>
              </div>
            )}

            {/* Success Quick Card */}
            {result && (
              <div className="cdl-result-quick-card">
                <div className="cdl-result-quick-title">
                  <span>✓</span>
                  <span>Analysis Ready</span>
                </div>
                {result.id && (
                  <Link
                    to={`/explorer/${result.id}`}
                    className="cdl-btn-open-explorer"
                  >
                    🔭 Open Explorer
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ====================================================================
          POST-ANALYSIS RESULTS PRESENTATION (BELOW WORKSTATION)
          ==================================================================== */}
      {result && (
        <div className="results-container" style={{ marginTop: 24 }}>
          {/* Compact In-Page Section Anchor Navigation */}
          <SectionNav />

          <div id="section-overview" className="results-overview-header">
            <div>
              <h2>Deformation Analysis Results</h2>
              <p className="results-meta">
                Compared Reference Frame <strong>{result.image1}</strong> &rarr; Target Frame <strong>{result.image2}</strong>
                {result.analysis_scope?.mode === "roi" && (
                  <span className="roi-meta-tag">
                    {" "}&bull; ROI: <strong>{result.analysis_scope.roi_type}</strong> ({result.analysis_scope.pixel_count} px)
                  </span>
                )}
              </p>
            </div>
            {result.id && (
              <Link
                to={`/explorer/${result.id}`}
                className="btn-primary"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "8px 16px",
                  fontSize: "13px",
                  textDecoration: "none",
                }}
                title="Open Advanced Scientific Analysis Explorer"
              >
                🔭 Open Explorer
              </Link>
            )}
          </div>

          {/* ROI vs Full Image Comparison (if ROI was analyzed) */}
          {result.roi_metrics && (
            <ROIComparisonView result={result} />
          )}

          {/* PART 1: 8 Key Metric Summary Cards */}
          <SummaryCards
            meanDisplacement={disp?.mean_displacement ?? fp?.D_mean}
            maxDisplacement={disp?.max_displacement ?? fp?.D_max}
            meanPrincipalStrain={
              strainStats?.principal_strain_1?.mean ??
              strainStats?.mean_principal_strain_1 ??
              fp?.epsilon_principal
            }
            maxPrincipalStrain={
              strainStats?.principal_strain_1?.max ??
              strainStats?.max_principal_strain_1 ??
              fp?.epsilon_max
            }
            motionCoherence={adv?.motion_coherence?.mean ?? fp?.C}
            anisotropy={adv?.anisotropy?.mean ?? fp?.AI}
            strainEntropy={adv?.entropy ?? fp?.H}
            temporalStability={fp?.TSI ?? null}
            calibration={result.calibration}
            physicalDisplacement={disp?.physical_space}
          />

          {/* PART 2 & 3: Structured Visualization Sections A, B, C, D with Fullscreen Viewer */}
          <AnalysisMaps result={result} />

          {/* PART 4: Enhanced 10-D Fingerprint Radar & Dimension Status Table */}
          {result.cardiac_deformation_fingerprint && (
            <div id="section-fingerprint" className="fingerprint-wrapper-section">
              <FingerprintChart
                fingerprintData={result.cardiac_deformation_fingerprint}
                fingerprint={fp}
              />
            </div>
          )}

          {/* PART 5: Mathematical Interpretation Panel */}
          <InterpretationPanel />

          {/* PART 6: Units and Methodology Reference */}
          <MethodologySection />
        </div>
      )}
    </div>
  );
}
