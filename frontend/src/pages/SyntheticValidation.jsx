import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  generateSyntheticDataset,
  validateSyntheticDataset,
  runRobustnessSweep,
  getValidationHistory,
  generateValidationReport,
  getReportDownloadUrl,
  API_BASE_URL,
} from "../services/api";
import ImageViewerModal from "../components/ImageViewerModal";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import "./SyntheticValidation.css";

const API_BASE = API_BASE_URL;


const DEFORMATION_MODES = [
  { value: "radial_expansion", label: "Radial Expansion" },
  { value: "radial_contraction", label: "Radial Contraction" },
  { value: "circumferential_deformation", label: "Circumferential Deformation (Twist)" },
  { value: "translation", label: "Rigid Translation" },
  { value: "uniform_scaling", label: "Uniform Scaling" },
  { value: "shear", label: "Mild Shear Strain" },
  { value: "combined", label: "Combined Complex Deformation" },
];

function formatVal(num, decimals = 4) {
  if (num === null || num === undefined) return "—";
  if (typeof num !== "number") return String(num);
  return num.toFixed(decimals);
}

function formatDate(isoStr) {
  if (!isoStr) return "N/A";
  try {
    const d = new Date(isoStr);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(isoStr);
  }
}

export default function SyntheticValidation() {
  // Generator configuration
  const [config, setConfig] = useState({
    width: 256,
    height: 256,
    inner_radius: 45,
    outer_radius: 75,
    deformation_mode: "radial_expansion",
    deformation_strength: 0.05,
    noise_level: 0.0,
    blur_sigma: 0.0,
    frame_count: 5,
  });

  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);
  const [currentDataset, setCurrentDataset] = useState(null);

  // Active preview frame
  const [activeFrameIdx, setActiveFrameIdx] = useState(0);

  // Validation benchmark state
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [valError, setValError] = useState(null);

  // Visual comparison active tab
  const [activeTab, setActiveTab] = useState("displacement"); // "displacement" | "strain" | "radial" | "circumferential"

  // Image modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalImg, setModalImg] = useState({ src: "", title: "", desc: "" });

  // Robustness sweep state
  const [sweeping, setSweeping] = useState(false);
  const [sweepData, setSweepData] = useState(null);
  const [sweepError, setSweepError] = useState(null);
  const [selectedBlurFilter, setSelectedBlurFilter] = useState(0.0);

  // Validation history state
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // PDF report state
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(null);
  const [pdfError, setPdfError] = useState(null);

  // Load history on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  async function fetchHistory() {
    setLoadingHistory(true);
    try {
      const data = await getValidationHistory();
      setHistory(data || []);
    } catch {
      // Ignore initial history failure
    } finally {
      setLoadingHistory(false);
    }
  }

  // Handle configuration changes
  const handleChange = (field, val) => {
    setConfig((prev) => ({
      ...prev,
      [field]: val,
    }));
  };

  // Generate synthetic dataset
  const handleGenerate = async (e) => {
    e.preventDefault();
    setGenerating(true);
    setGenError(null);
    setValidationResult(null);
    setSweepData(null);
    setPdfSuccess(null);
    setPdfError(null);

    try {
      const res = await generateSyntheticDataset(config);
      setCurrentDataset(res);
      setActiveFrameIdx(0);
    } catch (err) {
      setGenError(err.message || "Failed to generate synthetic dataset.");
    } finally {
      setGenerating(false);
    }
  };

  // Run validation benchmark
  const handleRunValidation = async () => {
    if (!currentDataset?.dataset_id) return;
    setValidating(true);
    setValError(null);
    setPdfSuccess(null);
    setPdfError(null);

    try {
      const res = await validateSyntheticDataset(currentDataset.dataset_id);
      setValidationResult(res);
      fetchHistory();
    } catch (err) {
      setValError(err.message || "Validation benchmark failed.");
    } finally {
      setValidating(false);
    }
  };

  // Run robustness sweep
  const handleRunSweep = async () => {
    if (!currentDataset?.dataset_id) return;
    setSweeping(true);
    setSweepError(null);

    try {
      const res = await runRobustnessSweep(currentDataset.dataset_id);
      setSweepData(res);
    } catch (err) {
      setSweepError(err.message || "Robustness sweep failed.");
    } finally {
      setSweeping(false);
    }
  };

  // Export PDF Report
  const handleExportPDF = async () => {
    if (!currentDataset?.dataset_id) return;
    setPdfLoading(true);
    setPdfError(null);
    setPdfSuccess(null);

    try {
      const res = await generateValidationReport(currentDataset.dataset_id);
      const dlUrl = getReportDownloadUrl(res.url);
      setPdfSuccess(dlUrl);
    } catch (err) {
      setPdfError(err.message || "Failed to generate validation report.");
    } finally {
      setPdfLoading(false);
    }
  };

  const openImageModal = (src, title, desc) => {
    setModalImg({ src, title, desc });
    setModalOpen(true);
  };

  // Filter robustness sweep data for chart by selected blur
  const filteredSweepData = useMemo(() => {
    return (sweepData?.results || [])
      .filter((r) => Math.abs(r.blur_sigma - selectedBlurFilter) < 0.01)
      .map((r) => ({
        noise: `σ=${r.noise_level}`,
        noise_num: r.noise_level,
        disp_rmse: r.displacement_rmse !== null ? Number(r.displacement_rmse.toFixed(4)) : null,
        strain_rmse: r.strain_rmse !== null ? Number(r.strain_rmse.toFixed(4)) : null,
        disp_corr: r.displacement_correlation !== null ? Number(r.displacement_correlation.toFixed(3)) : null,
      }));
  }, [sweepData, selectedBlurFilter]);

  // Determine active workflow step
  const activeStep = useMemo(() => {
    if (sweepData) return 5;
    if (validationResult) return 4;
    if (currentDataset) return 2;
    return 1;
  }, [sweepData, validationResult, currentDataset]);

  return (
    <div className="cdl-val-page">
      {/* 1. Page Header & Breadcrumbs */}
      <div className="cdl-val-header-wrap">
        <div className="cdl-val-title-area">
          <div className="cdl-val-breadcrumb">
            <Link to="/studies" className="bc-link">
              📁 Studies
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Synthetic Validation</span>
          </div>

          <div className="cdl-val-pill-row">
            <span className="cdl-val-badge cdl-val-badge-blue">
              🔬 Research Benchmark
            </span>
            <span className="cdl-val-badge cdl-val-badge-purple">
              Mathematical Ground Truth
            </span>
            {currentDataset && (
              <span className="cdl-val-badge cdl-val-badge-emerald">
                Dataset: {currentDataset.dataset_id.slice(0, 8)}...
              </span>
            )}
            {validationResult && (
              <span className="cdl-val-badge cdl-val-badge-blue">
                Farneback Flow Benchmarked
              </span>
            )}
          </div>

          <h1 className="cdl-val-title">Synthetic Validation &amp; Phantom Benchmark</h1>
          <p className="cdl-val-subtitle">
            Controlled artificial myocardial phantom generator and rigorous quantitative verification of optical flow and strain tensors against exact mathematical ground truth.
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="cdl-val-header-actions">
          {currentDataset && (
            <button
              type="button"
              className="cdl-val-btn-primary"
              onClick={handleRunValidation}
              disabled={validating}
              title="Run optical-flow estimation and benchmark against ground truth"
            >
              {validating ? (
                <>
                  <span className="cdl-val-spinner" /> Benchmarking...
                </>
              ) : (
                <>⚡ Run Validation</>
              )}
            </button>
          )}

          {currentDataset && (
            <button
              type="button"
              className="cdl-val-btn-secondary"
              onClick={handleRunSweep}
              disabled={sweeping}
              title="Run multi-condition noise and blur robustness sweep"
            >
              {sweeping ? (
                <>
                  <span className="cdl-val-spinner" /> Sweeping...
                </>
              ) : (
                <>🔬 Robustness Sweep</>
              )}
            </button>
          )}

          <button
            type="button"
            className="cdl-val-btn-secondary"
            onClick={handleExportPDF}
            disabled={pdfLoading || !validationResult}
            title="Export validation benchmark PDF report"
          >
            {pdfLoading ? "Generating..." : "📥 Export PDF"}
          </button>
        </div>
      </div>

      {/* 2. Top 5-Step Workflow Progress Tracker */}
      <div className="cdl-val-workflow-card">
        <div className="cdl-val-workflow-track">
          <div className={`cdl-val-workflow-step ${activeStep >= 1 ? (activeStep > 1 ? "completed" : "active") : ""}`}>
            <div className="cdl-val-step-num">{activeStep > 1 ? "✓" : "1"}</div>
            <div className="cdl-val-step-info">
              <span className="cdl-val-step-title">1. Generate Phantom</span>
              <span className="cdl-val-step-sub">Geometric parameters</span>
            </div>
          </div>

          <div className={`cdl-val-workflow-step ${activeStep >= 2 ? (activeStep > 2 ? "completed" : "active") : ""}`}>
            <div className="cdl-val-step-num">{activeStep > 2 ? "✓" : "2"}</div>
            <div className="cdl-val-step-info">
              <span className="cdl-val-step-title">2. Ground Truth</span>
              <span className="cdl-val-step-sub">Analytical vectors</span>
            </div>
          </div>

          <div className={`cdl-val-workflow-step ${activeStep >= 3 ? (activeStep > 3 ? "completed" : "active") : ""}`}>
            <div className="cdl-val-step-num">{activeStep > 3 ? "✓" : "3"}</div>
            <div className="cdl-val-step-info">
              <span className="cdl-val-step-title">3. Run Analysis</span>
              <span className="cdl-val-step-sub">Farneback optical flow</span>
            </div>
          </div>

          <div className={`cdl-val-workflow-step ${activeStep >= 4 ? (activeStep > 4 ? "completed" : "active") : ""}`}>
            <div className="cdl-val-step-num">{activeStep > 4 ? "✓" : "4"}</div>
            <div className="cdl-val-step-info">
              <span className="cdl-val-step-title">4. Quantify Error</span>
              <span className="cdl-val-step-sub">MAE, RMSE &amp; EPE</span>
            </div>
          </div>

          <div className={`cdl-val-workflow-step ${activeStep >= 5 ? "active" : ""}`}>
            <div className="cdl-val-step-num">5</div>
            <div className="cdl-val-step-info">
              <span className="cdl-val-step-title">5. Test Robustness</span>
              <span className="cdl-val-step-sub">Noise &amp; blur sweep</span>
            </div>
          </div>
        </div>
      </div>

      {/* Research Disclaimer Card */}
      <div className="cdl-val-disclaimer-card">
        <span className="cdl-val-disclaimer-badge">Non-Clinical Notice</span>
        <p className="cdl-val-disclaimer-text">
          This benchmark evaluates optical-flow motion and strain estimation algorithms against a simplified synthetic myocardial phantom with known analytical ground truth. It is designed for algorithmic quality assurance, numerical stability testing, and noise robustness analysis. It does <strong>not</strong> establish clinical validity or patient diagnostic accuracy.
        </p>
      </div>

      {/* PDF Export Banner */}
      {pdfSuccess && (
        <div className="cdl-val-banner cdl-val-banner-success">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span>✅</span>
            <div>
              <strong>Validation Report PDF generated successfully.</strong>
              <div style={{ fontSize: 12, opacity: 0.9 }}>Ready for download.</div>
            </div>
          </div>
          <a
            href={pdfSuccess}
            target="_blank"
            rel="noopener noreferrer"
            className="cdl-val-download-link"
          >
            📥 Download / View PDF
          </a>
        </div>
      )}

      {pdfError && (
        <div className="cdl-val-banner cdl-val-banner-error">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span>⚠️</span>
            <span>{pdfError}</span>
          </div>
        </div>
      )}

      {/* 3. Generator & Live Preview Two-Column Grid */}
      <div className="cdl-val-grid-2col">
        {/* Left Column: Generator Form */}
        <div className="cdl-val-card">
          <div className="cdl-val-card-header">
            <h3 className="cdl-val-card-title">
              <span>⚙️</span> Phantom Configuration
            </h3>
            <span style={{ fontSize: 11, color: "#64748b" }}>Geometric &amp; Kinematic Inputs</span>
          </div>

          <form onSubmit={handleGenerate} className="cdl-val-form">
            <div className="cdl-val-form-row">
              <label className="cdl-val-label-row">
                <span>Image Dimensions (Width × Height)</span>
                <span className="cdl-val-val-badge">{config.width} × {config.height} px</span>
              </label>
              <div className="cdl-val-input-pair">
                <input
                  type="number"
                  min="64"
                  max="512"
                  step="32"
                  value={config.width}
                  onChange={(e) => handleChange("width", parseInt(e.target.value, 10) || 256)}
                  className="cdl-val-num-input"
                  title="Width in pixels"
                />
                <span style={{ color: "#94a3b8", fontWeight: 700 }}>×</span>
                <input
                  type="number"
                  min="64"
                  max="512"
                  step="32"
                  value={config.height}
                  onChange={(e) => handleChange("height", parseInt(e.target.value, 10) || 256)}
                  className="cdl-val-num-input"
                  title="Height in pixels"
                />
              </div>
            </div>

            <div className="cdl-val-form-row">
              <label className="cdl-val-label-row">
                <span>Deformation Mode</span>
              </label>
              <select
                value={config.deformation_mode}
                onChange={(e) => handleChange("deformation_mode", e.target.value)}
                className="cdl-val-select"
              >
                {DEFORMATION_MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="cdl-val-form-row">
              <div className="cdl-val-label-row">
                <span>Deformation Strength</span>
                <span className="cdl-val-val-badge">{config.deformation_strength.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.01"
                max="0.20"
                step="0.01"
                value={config.deformation_strength}
                onChange={(e) => handleChange("deformation_strength", parseFloat(e.target.value))}
                className="cdl-val-slider"
              />
            </div>

            <div className="cdl-val-form-row dual">
              <div>
                <div className="cdl-val-label-row">
                  <span>Inner Radius</span>
                  <span className="cdl-val-val-badge">{config.inner_radius}px</span>
                </div>
                <input
                  type="range"
                  min="15"
                  max="60"
                  value={config.inner_radius}
                  onChange={(e) => handleChange("inner_radius", parseInt(e.target.value, 10))}
                  className="cdl-val-slider"
                />
              </div>
              <div>
                <div className="cdl-val-label-row">
                  <span>Outer Radius</span>
                  <span className="cdl-val-val-badge">{config.outer_radius}px</span>
                </div>
                <input
                  type="range"
                  min="55"
                  max="115"
                  value={config.outer_radius}
                  onChange={(e) => handleChange("outer_radius", parseInt(e.target.value, 10))}
                  className="cdl-val-slider"
                />
              </div>
            </div>

            <div className="cdl-val-form-row dual">
              <div>
                <div className="cdl-val-label-row">
                  <span>Noise (σ)</span>
                  <span className="cdl-val-val-badge">{config.noise_level.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="0.15"
                  step="0.01"
                  value={config.noise_level}
                  onChange={(e) => handleChange("noise_level", parseFloat(e.target.value))}
                  className="cdl-val-slider"
                />
              </div>
              <div>
                <div className="cdl-val-label-row">
                  <span>Blur Filter (σ)</span>
                  <span className="cdl-val-val-badge">{config.blur_sigma.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="3.0"
                  step="0.5"
                  value={config.blur_sigma}
                  onChange={(e) => handleChange("blur_sigma", parseFloat(e.target.value))}
                  className="cdl-val-slider"
                />
              </div>
            </div>

            <div className="cdl-val-form-row">
              <div className="cdl-val-label-row">
                <span>Temporal Frame Sequence</span>
                <span className="cdl-val-val-badge">{config.frame_count} Frames</span>
              </div>
              <input
                type="range"
                min="2"
                max="10"
                step="1"
                value={config.frame_count}
                onChange={(e) => handleChange("frame_count", parseInt(e.target.value, 10))}
                className="cdl-val-slider"
              />
            </div>

            {genError && (
              <div className="cdl-val-banner cdl-val-banner-error">
                <span>⚠️ {genError}</span>
              </div>
            )}

            <button type="submit" className="cdl-val-btn-primary" disabled={generating} style={{ justifyContent: "center", marginTop: 4 }}>
              {generating ? (
                <>
                  <span className="cdl-val-spinner" /> Synthesizing Dataset...
                </>
              ) : (
                <>🧪 Generate Phantom Dataset</>
              )}
            </button>
          </form>
        </div>

        {/* Right Column: Frame Preview & Ground Truth Summary */}
        <div className="cdl-val-card">
          <div className="cdl-val-card-header">
            <h3 className="cdl-val-card-title">
              <span>🖼️</span> Phantom Frame Explorer &amp; Analytical Ground Truth
            </h3>
            {currentDataset && (
              <span className="cdl-val-badge cdl-val-badge-slate" style={{ fontFamily: "monospace" }}>
                ID: {currentDataset.dataset_id.slice(0, 10)}...
              </span>
            )}
          </div>

          {!currentDataset ? (
            <div style={{ textAlign: "center", padding: "48px 16px", color: "#64748b" }}>
              <span style={{ fontSize: 36, display: "block", marginBottom: 12 }}>🫀</span>
              <h4 style={{ margin: "0 0 6px 0", color: "#0f172a" }}>No Synthetic Dataset Active</h4>
              <p style={{ margin: 0, fontSize: 13 }}>
                Configure the geometric and kinematic parameters on the left and click <strong>Generate Phantom Dataset</strong> to begin.
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* Active Frame Viewer Box */}
              <div className="cdl-val-preview-box">
                <div className="cdl-val-preview-tag">Synthetic Phantom Canvas</div>
                <div
                  className="cdl-val-frame-img-box"
                  onClick={() =>
                    openImageModal(
                      `${API_BASE}${currentDataset.frames[activeFrameIdx]}`,
                      `Synthetic Frame ${activeFrameIdx}`,
                      `Deformation Mode: ${config.deformation_mode} (Strength ${config.deformation_strength})`
                    )
                  }
                  title="Click to view full resolution"
                >
                  <img
                    src={`${API_BASE}${currentDataset.frames[activeFrameIdx]}`}
                    alt={`Frame ${activeFrameIdx}`}
                  />
                </div>
                <div className="cdl-val-frame-meta-bar">
                  <span>Frame {activeFrameIdx + 1} of {currentDataset.frame_count}</span>
                  <span>{activeFrameIdx === 0 ? "Baseline Reference (t=0)" : `Progressive step ${activeFrameIdx}`}</span>
                </div>
              </div>

              {/* Scrubber Thumbnails */}
              <div className="cdl-val-thumb-strip">
                {currentDataset.frames.map((url, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`cdl-val-thumb-btn ${idx === activeFrameIdx ? "selected" : ""}`}
                    onClick={() => setActiveFrameIdx(idx)}
                    title={`Inspect Frame ${idx}`}
                  >
                    <img src={`${API_BASE}${url}`} alt={`Thumb ${idx}`} />
                    <span className="cdl-val-thumb-badge">#{idx}</span>
                  </button>
                ))}
              </div>

              {/* Analytical Ground Truth Summary Strip */}
              <div className="cdl-val-gt-strip">
                <div className="cdl-val-gt-chip">
                  <span className="chip-label">Deformation Mode</span>
                  <span className="chip-val" style={{ fontSize: 12 }}>{config.deformation_mode}</span>
                </div>
                <div className="cdl-val-gt-chip">
                  <span className="chip-label">GT Mean Disp</span>
                  <span className="chip-val">
                    {formatVal(currentDataset.metadata?.ground_truth_summary?.mean_displacement)} px
                  </span>
                </div>
                <div className="cdl-val-gt-chip">
                  <span className="chip-label">GT Myo Strain</span>
                  <span className="chip-val">
                    {formatVal(currentDataset.metadata?.ground_truth_summary?.mean_principal_strain_1)}
                  </span>
                </div>
                <div className="cdl-val-gt-chip">
                  <span className="chip-label">Resolution</span>
                  <span className="chip-val">{config.width}×{config.height}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="cdl-val-preview-actions">
                <button
                  type="button"
                  className="cdl-val-btn-primary"
                  onClick={handleRunValidation}
                  disabled={validating}
                >
                  {validating ? (
                    <>
                      <span className="cdl-val-spinner" /> Running Benchmark...
                    </>
                  ) : (
                    <>⚡ Run Validation Benchmark</>
                  )}
                </button>

                <button
                  type="button"
                  className="cdl-val-btn-secondary"
                  onClick={handleRunSweep}
                  disabled={sweeping}
                >
                  {sweeping ? (
                    <>
                      <span className="cdl-val-spinner" /> Testing Robustness...
                    </>
                  ) : (
                    <>🔬 Run Robustness Sweep</>
                  )}
                </button>
              </div>

              {valError && <div className="cdl-val-banner cdl-val-banner-error"><span>⚠️ {valError}</span></div>}
              {sweepError && <div className="cdl-val-banner cdl-val-banner-error"><span>⚠️ {sweepError}</span></div>}
            </div>
          )}
        </div>
      </div>

      {/* 4. Validation Benchmark Results Section */}
      {validationResult && (
        <section className="cdl-val-results-section">
          <div className="cdl-val-card-header">
            <div>
              <h2 className="cdl-val-card-title" style={{ fontSize: 19 }}>
                <span>📊</span> Algorithmic Accuracy vs. Analytical Ground Truth
              </h2>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                Benchmarked against OpenCV Farneback Optical Flow &amp; Finite Strain Tensors
              </span>
            </div>
            <span className="cdl-val-badge cdl-val-badge-emerald">
              Validation Complete
            </span>
          </div>

          {/* KPI Metrics Cards */}
          <div className="cdl-val-kpi-grid">
            <div className="cdl-val-kpi-card">
              <span className="cdl-val-kpi-label">Displacement MAE</span>
              <span className="cdl-val-kpi-num">
                {formatVal(validationResult.validation?.summary?.displacement_mae)} px
              </span>
              <span className="cdl-val-kpi-sub">Mean Absolute Error over myocardial ring</span>
            </div>

            <div className="cdl-val-kpi-card">
              <span className="cdl-val-kpi-label">Displacement RMSE</span>
              <span className="cdl-val-kpi-num">
                {formatVal(validationResult.validation?.summary?.displacement_rmse)} px
              </span>
              <span className="cdl-val-kpi-sub">Root Mean Squared Error</span>
            </div>

            <div className="cdl-val-kpi-card highlight">
              <span className="cdl-val-kpi-label">Endpoint Error (EPE)</span>
              <span className="cdl-val-kpi-num" style={{ color: "#2563eb" }}>
                {formatVal(validationResult.validation?.summary?.mean_endpoint_error)} px
              </span>
              <span className="cdl-val-kpi-sub">
                Max EPE: {formatVal(validationResult.validation?.summary?.max_endpoint_error)} px
              </span>
            </div>

            <div className="cdl-val-kpi-card">
              <span className="cdl-val-kpi-label">Principal Strain RMSE</span>
              <span className="cdl-val-kpi-num">
                {formatVal(validationResult.validation?.summary?.strain_rmse)}
              </span>
              <span className="cdl-val-kpi-sub">Dimensionless principal strain error</span>
            </div>

            <div className="cdl-val-kpi-card">
              <span className="cdl-val-kpi-label">Displacement Correlation</span>
              <span className="cdl-val-kpi-num">
                {formatVal(validationResult.validation?.summary?.displacement_correlation, 3)}
              </span>
              <span className="cdl-val-kpi-sub">Pearson correlation coefficient (r)</span>
            </div>

            <div className="cdl-val-kpi-card">
              <span className="cdl-val-kpi-label">Radial / Circ RMSE</span>
              <span className="cdl-val-kpi-num" style={{ fontSize: 18 }}>
                {formatVal(validationResult.validation?.summary?.radial_rmse)} / {formatVal(validationResult.validation?.summary?.circumferential_rmse)}
              </span>
              <span className="cdl-val-kpi-sub">Radial vs. circumferential strain RMSE</span>
            </div>
          </div>

          {/* Tri-View Comparison Section */}
          <div className="cdl-val-triview-wrap">
            <div className="cdl-val-tab-bar">
              <button
                type="button"
                className={`cdl-val-tab-btn ${activeTab === "displacement" ? "active" : ""}`}
                onClick={() => setActiveTab("displacement")}
              >
                Displacement Fields
              </button>
              <button
                type="button"
                className={`cdl-val-tab-btn ${activeTab === "strain" ? "active" : ""}`}
                onClick={() => setActiveTab("strain")}
              >
                Principal Strain
              </button>
              <button
                type="button"
                className={`cdl-val-tab-btn ${activeTab === "radial" ? "active" : ""}`}
                onClick={() => setActiveTab("radial")}
              >
                Radial Deformation
              </button>
              <button
                type="button"
                className={`cdl-val-tab-btn ${activeTab === "circumferential" ? "active" : ""}`}
                onClick={() => setActiveTab("circumferential")}
              >
                Circumferential Deformation
              </button>
            </div>

            {/* Tri-View Grid: GT vs Estimated vs Error */}
            {validationResult.visualizations?.[activeTab] && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div className="cdl-val-triview-grid">
                  {/* Ground Truth Map */}
                  <div className="cdl-val-map-card gt">
                    <div className="cdl-val-map-header">
                      <span className="cdl-val-map-title gt">1. Analytical Ground Truth</span>
                      <span className="cdl-val-badge cdl-val-badge-slate" style={{ fontSize: 10 }}>Exact Solution</span>
                    </div>
                    <div
                      className="cdl-val-map-canvas"
                      onClick={() =>
                        openImageModal(
                          `${API_BASE}${validationResult.visualizations[activeTab].gt_url}`,
                          `Ground Truth — ${activeTab}`,
                          "Exact analytical mathematical solution"
                        )
                      }
                      title="Click to view full resolution"
                    >
                      <img
                        src={`${API_BASE}${validationResult.visualizations[activeTab].gt_url}`}
                        alt="Ground Truth Map"
                      />
                    </div>
                    <div className="cdl-val-map-caption">
                      Analytical mathematical transformation
                    </div>
                  </div>

                  {/* Estimated Map */}
                  <div className="cdl-val-map-card est">
                    <div className="cdl-val-map-header">
                      <span className="cdl-val-map-title est">2. Estimated Result</span>
                      <span className="cdl-val-badge cdl-val-badge-slate" style={{ fontSize: 10 }}>Algorithm Output</span>
                    </div>
                    <div
                      className="cdl-val-map-canvas"
                      onClick={() =>
                        openImageModal(
                          `${API_BASE}${validationResult.visualizations[activeTab].est_url}`,
                          `Estimated — ${activeTab}`,
                          "Algorithmic estimate derived from image pairs"
                        )
                      }
                      title="Click to view full resolution"
                    >
                      <img
                        src={`${API_BASE}${validationResult.visualizations[activeTab].est_url}`}
                        alt="Estimated Result Map"
                      />
                    </div>
                    <div className="cdl-val-map-caption">
                      OpenCV Farneback flow / strain tensor calculation
                    </div>
                  </div>

                  {/* Absolute Error Map */}
                  <div className="cdl-val-map-card err">
                    <div className="cdl-val-map-header">
                      <span className="cdl-val-map-title err">3. Absolute Error |Est - GT|</span>
                      <span className="cdl-val-badge cdl-val-badge-slate" style={{ fontSize: 10 }}>Difference Heatmap</span>
                    </div>
                    <div
                      className="cdl-val-map-canvas"
                      onClick={() =>
                        openImageModal(
                          `${API_BASE}${validationResult.visualizations[activeTab].error_url}`,
                          `Absolute Error — ${activeTab}`,
                          "Absolute difference heatmap (|Estimated - Ground Truth|)"
                        )
                      }
                      title="Click to view full resolution"
                    >
                      <img
                        src={`${API_BASE}${validationResult.visualizations[activeTab].error_url}`}
                        alt="Absolute Error Map"
                      />
                    </div>
                    <div className="cdl-val-map-caption">
                      Spatial error dispersion across myocardium
                    </div>
                  </div>
                </div>

                {/* Error Map Quantitative Statistics Strip */}
                <div className="cdl-val-error-strip">
                  <div className="cdl-val-error-item">
                    <span>Mean Error:</span>
                    <strong>{formatVal(validationResult.visualizations[activeTab].statistics?.mean_error)}</strong>
                  </div>
                  <div className="cdl-val-error-item">
                    <span>Median Error:</span>
                    <strong>{formatVal(validationResult.visualizations[activeTab].statistics?.median_error)}</strong>
                  </div>
                  <div className="cdl-val-error-item">
                    <span>Max Error:</span>
                    <strong>{formatVal(validationResult.visualizations[activeTab].statistics?.max_error)}</strong>
                  </div>
                  <div className="cdl-val-error-item">
                    <span>RMSE:</span>
                    <strong>{formatVal(validationResult.visualizations[activeTab].statistics?.rmse)}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* 5. Robustness Sweep Analysis Section */}
      {sweepData && (
        <section className="cdl-val-robustness-section">
          <div className="cdl-val-card-header">
            <div>
              <h3 className="cdl-val-card-title">
                <span>🔬</span> Robustness Sweep Analysis
              </h3>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                Degradation curves across increasing additive Gaussian noise and spatial blur
              </span>
            </div>
            <div className="cdl-val-blur-selector">
              <span style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginRight: 4 }}>Filter Blur σ:</span>
              {[0.0, 1.0, 2.0].map((b) => (
                <button
                  key={b}
                  type="button"
                  className={`cdl-val-blur-btn ${Math.abs(selectedBlurFilter - b) < 0.01 ? "active" : ""}`}
                  onClick={() => setSelectedBlurFilter(b)}
                >
                  σ={b.toFixed(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="cdl-val-chart-canvas">
            <span style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", display: "block", marginBottom: 10 }}>
              RMSE Error Trajectory vs Additive Noise σ (Blur Filter σ={selectedBlurFilter.toFixed(1)})
            </span>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={filteredSweepData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="noise" stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis stroke="#64748b" domain={[0, "auto"]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8, color: "#fff", fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 12, paddingTop: 6 }} />
                <Line
                  type="monotone"
                  dataKey="disp_rmse"
                  name="Displacement RMSE (px)"
                  stroke="#38bdf8"
                  strokeWidth={2.5}
                  dot={{ r: 4, stroke: "#38bdf8", strokeWidth: 2, fill: "#ffffff" }}
                />
                <Line
                  type="monotone"
                  dataKey="strain_rmse"
                  name="Principal Strain RMSE"
                  stroke="#a855f7"
                  strokeWidth={2.5}
                  dot={{ r: 4, stroke: "#a855f7", strokeWidth: 2, fill: "#ffffff" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Sweep Results Table */}
          <div className="cdl-val-table-box">
            <table className="cdl-val-table">
              <thead>
                <tr>
                  <th>Noise Level</th>
                  <th>Blur Level</th>
                  <th>Disp RMSE (px)</th>
                  <th>Disp MAE (px)</th>
                  <th>Mean EPE (px)</th>
                  <th>Strain RMSE</th>
                  <th>Strain Corr (r)</th>
                </tr>
              </thead>
              <tbody>
                {sweepData.results.map((row, i) => (
                  <tr key={i}>
                    <td>σ={row.noise_level}</td>
                    <td>σ={row.blur_sigma}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(row.displacement_rmse)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(row.displacement_mae)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(row.mean_endpoint_error)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(row.strain_rmse)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(row.strain_correlation, 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 6. Validation Benchmark History */}
      <section className="cdl-val-history-section">
        <div className="cdl-val-card-header">
          <div>
            <h3 className="cdl-val-card-title">
              <span>🕒</span> Validation Benchmark History
            </h3>
            <span style={{ fontSize: 12, color: "#64748b" }}>
              Permanent record of past synthetic benchmark runs
            </span>
          </div>
          <button
            type="button"
            className="cdl-val-btn-secondary"
            onClick={fetchHistory}
            disabled={loadingHistory}
            style={{ fontSize: 12, padding: "5px 12px" }}
          >
            {loadingHistory ? "Refreshing..." : "↻ Refresh History"}
          </button>
        </div>

        {history.length === 0 ? (
          <p style={{ color: "#64748b", fontSize: 13, margin: "10px 0" }}>
            No past synthetic validation benchmarks recorded yet.
          </p>
        ) : (
          <div className="cdl-val-table-box">
            <table className="cdl-val-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Dataset ID</th>
                  <th>Deformation Mode</th>
                  <th>Dimensions</th>
                  <th>Strength</th>
                  <th>Noise / Blur</th>
                  <th>Disp RMSE (px)</th>
                  <th>Mean EPE (px)</th>
                  <th>Strain RMSE</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, idx) => (
                  <tr key={item.id || idx}>
                    <td>{formatDate(item.timestamp)}</td>
                    <td>
                      <code className="cdl-val-badge cdl-val-badge-slate" style={{ fontSize: 10 }}>
                        {item.dataset_id?.slice(0, 8)}...
                      </code>
                    </td>
                    <td>
                      <strong style={{ color: "#0f172a" }}>{item.deformation_mode}</strong>
                    </td>
                    <td>{item.dimensions || "—"}</td>
                    <td>{item.deformation_strength || "—"}</td>
                    <td>σ={item.noise_level} / σ={item.blur_sigma}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(item.metrics_summary?.displacement_rmse)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(item.metrics_summary?.mean_endpoint_error)}</td>
                    <td style={{ fontFamily: "monospace" }}>{formatVal(item.metrics_summary?.strain_rmse)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 7. Scientific Limitations & Algorithmic Notes */}
      <div className="cdl-val-limitations-card">
        <h4 className="cdl-val-limitations-title">
          <span>🔬</span> Scientific Limitations &amp; Algorithmic Notes
        </h4>
        <ul className="cdl-val-limitations-list">
          <li>
            <strong>Controlled Analytical Deformation:</strong> Synthetic phantom motion is governed by exact affine/radial coordinate equations. Real myocardial tissue deformation is 3D, viscoelastic, and anisotropic.
          </li>
          <li>
            <strong>Texture vs. Ultrasound Physics:</strong> Synthetic phantoms utilize procedural waveforms. Real echocardiographic imaging contains acoustic speckle physics, clutter, reverberations, dropouts, and lateral attenuation.
          </li>
          <li>
            <strong>Optical Flow Brightness Constancy:</strong> Gradient-based optical flow assumes brightness constancy and small displacements. Out-of-plane cardiac motion naturally violates 2D brightness constancy.
          </li>
          <li>
            <strong>Non-Diagnostic Computational Benchmarking:</strong> This verification layer measures algorithmic deviation from known mathematical models. It does not validate clinical diagnostic accuracy or patient outcomes.
          </li>
        </ul>
      </div>

      {/* Image Modal */}
      <ImageViewerModal
        isOpen={modalOpen}
        imageSrc={modalImg.src}
        title={modalImg.title}
        description={modalImg.desc}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
