import { useState, useEffect, useMemo, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import {
  getAnalysisHistory,
  getAnalysisHistoryById,
  deleteAnalysisHistoryById,
  clearAnalysisHistory,
  generateAnalysisReport,
  getReportDownloadUrl,
  getOutputUrl,
} from "../services/api";
import FingerprintChart from "../components/FingerprintChart";
import TemporalChart from "../components/TemporalChart";
import SectionNav from "../components/SectionNav";
import InterpretationPanel from "../components/InterpretationPanel";
import MethodologySection from "../components/MethodologySection";
import ROIComparisonView from "../components/ROIComparisonView";
import TrackedROIKeyframeGallery from "../components/TrackedROIKeyframeGallery";
import TrackingTrajectoryChart from "../components/TrackingTrajectoryChart";
import QualityControlCard from "../components/QualityControlCard";
import ImageViewerModal from "../components/ImageViewerModal";
import "./Results.css";

function formatNumber(val, decimals = 4) {
  if (val === null || val === undefined) return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return val.toExponential(decimals);
  }
  return val.toFixed(decimals);
}

function formatDate(isoString) {
  if (!isoString) return "N/A";
  try {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

// Reusable Dark Visualization Panel Component
function ScientificVisPanel({ title, path, description, metricBadge, onExpand }) {
  const url = path ? getOutputUrl(path) : null;
  const [loading, setLoading] = useState(Boolean(url));
  const [hasError, setHasError] = useState(!url);

  return (
    <div className="cdl-vis-panel">
      <div className="cdl-vis-panel-header">
        <div className="cdl-vis-panel-titles">
          <h4 className="cdl-vis-panel-title">{title}</h4>
          <p className="cdl-vis-panel-desc">{description}</p>
        </div>
        <div className="cdl-vis-panel-actions">
          {url && !hasError && (
            <button
              className="cdl-vis-panel-expand"
              onClick={() => onExpand({ title, url, description })}
              title="Expand to Fullscreen View"
              aria-label={`Expand ${title}`}
            >
              ⛶
            </button>
          )}
        </div>
      </div>

      <div
        className="cdl-vis-canvas-wrap"
        onClick={() => {
          if (url && !hasError) {
            onExpand({ title, url, description });
          }
        }}
      >
        {loading && (
          <div className="cdl-vis-canvas-loading">
            <span className="spinner"></span>
            <span>Rendering visual field...</span>
          </div>
        )}

        {hasError ? (
          <div className="cdl-vis-canvas-empty">
            <span style={{ fontSize: "24px" }}>⚠️</span>
            <span>Visualization unavailable</span>
          </div>
        ) : (
          <img
            src={url}
            alt={title}
            className={`cdl-vis-canvas-img ${loading ? "hidden" : "visible"}`}
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setHasError(true);
            }}
          />
        )}

        {!hasError && !loading && (
          <div className="cdl-vis-hover-zoom">
            🔍 Click to inspect
          </div>
        )}
      </div>

      <div className="cdl-vis-panel-footer">
        <span>Scientific Canvas</span>
        {metricBadge && <span className="cdl-vis-panel-badge">{metricBadge}</span>}
      </div>
    </div>
  );
}

export default function Results() {
  const { latestAnalysisResult, latestTemporalResult } = useAnalysis();
  const location = useLocation();

  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState(null);

  // Selected analysis for inspection (either fetched by id or initial fallback to context)
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [_loadingDetail, setLoadingDetail] = useState(false);
  const [actionMsg, setActionMsg] = useState("");
  const [copiedId, setCopiedId] = useState(false);

  // Active visualization tab
  const [activeVisTab, setActiveVisTab] = useState("all");

  // History drawer state & filter toolbar
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [historyFilterType, setHistoryFilterType] = useState("all"); // "all" | "single_pair" | "temporal"

  // Report generation state per analysis ID: { [id]: { loading: boolean, reportUrl: string | null, error: string | null } }
  const [reportState, setReportState] = useState({});

  // Fullscreen image modal state
  const [modalState, setModalState] = useState({
    isOpen: false,
    imageSrc: null,
    title: "",
    description: "",
  });

  const handleSelectRecord = useCallback(async (recordId) => {
    setLoadingDetail(true);
    try {
      const detail = await getAnalysisHistoryById(recordId);
      setSelectedRecord(detail);
      setActionMsg("");
      // Smoothly scroll to overview section
      const overview = document.getElementById("section-overview");
      if (overview) {
        overview.scrollIntoView({ behavior: "smooth" });
      }
    } catch (err) {
      setActionMsg(`Failed to load record: ${err.message}`);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const records = await getAnalysisHistory();
      const list = records || [];
      setHistoryList(list);

      // Check if location state has a specific recordId to load
      const targetId = location?.state?.recordId;
      if (targetId) {
        const found = list.find((r) => r.id === targetId);
        if (found) {
          handleSelectRecord(targetId);
          return;
        }
      }

      // If no record is actively selected, select the first one if available
      if (!selectedRecord && list.length > 0 && !latestAnalysisResult && !latestTemporalResult) {
        setSelectedRecord(list[0]);
      }
    } catch (err) {
      setHistoryError(
        err.message || "Failed to connect to backend history service."
      );
    } finally {
      setLoadingHistory(false);
    }
  }, [location?.state?.recordId, selectedRecord, latestAnalysisResult, latestTemporalResult, handleSelectRecord]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);


  const handleDeleteRecord = async (e, recordId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this analysis record?")) {
      return;
    }

    try {
      await deleteAnalysisHistoryById(recordId);
      setActionMsg("Analysis record deleted successfully.");
      if (selectedRecord?.id === recordId) {
        setSelectedRecord(null);
      }
      await fetchHistory();
    } catch (err) {
      setActionMsg(`Delete failed: ${err.message}`);
    }
  };

  const handleClearAllHistory = async () => {
    if (
      !window.confirm(
        "Are you sure you want to clear all analysis history? This cannot be undone."
      )
    ) {
      return;
    }

    try {
      await clearAnalysisHistory();
      setSelectedRecord(null);
      setActionMsg("All analysis history cleared.");
      await fetchHistory();
    } catch (err) {
      setActionMsg(`Failed to clear history: ${err.message}`);
    }
  };

  const handleGenerateReport = async (e, recordId) => {
    if (e) e.stopPropagation();
    if (!recordId) return;

    setReportState((prev) => ({
      ...prev,
      [recordId]: { loading: true, reportUrl: null, error: null },
    }));

    try {
      const res = await generateAnalysisReport(recordId);
      const fullUrl = getReportDownloadUrl(res.url);
      setReportState((prev) => ({
        ...prev,
        [recordId]: { loading: false, reportUrl: fullUrl, error: null },
      }));
      setActionMsg(`Report generated successfully for analysis ${recordId.slice(0, 8)}`);
    } catch (err) {
      setReportState((prev) => ({
        ...prev,
        [recordId]: { loading: false, reportUrl: null, error: err.message },
      }));
      setActionMsg(`Report generation failed: ${err.message}`);
    }
  };

  // Determine what result data to display in detail workspace:
  const displayRecord = selectedRecord;
  const displayResult = displayRecord?.result || latestAnalysisResult || latestTemporalResult;
  const isTemporal =
    displayRecord?.type === "temporal" ||
    (!displayRecord && Boolean(latestTemporalResult) && !latestAnalysisResult);

  const activeRecordId = displayRecord?.id || displayResult?.analysis_id || displayResult?.id;
  const activeReport = activeRecordId ? reportState[activeRecordId] : null;

  const fp = displayResult?.cardiac_deformation_fingerprint?.fingerprint;

  const outputs = displayResult?.outputs || {};
  const advOutputs = displayResult?.advanced_outputs || {};
  const cardiacOutputs = displayResult?.cardiac_deformation_outputs || {};

  // Calibration Info
  const cal = displayResult?.calibration;
  const isCalibrated = Boolean(cal?.enabled);
  const dispUnit = isCalibrated ? (cal?.unit || "mm") : "px";

  // Real Displacement
  const meanDisp = isCalibrated
    ? (displayResult?.displacement?.physical_space?.mean ??
       displayResult?.displacement?.physical_space?.mean_displacement ??
       displayResult?.displacement?.mean_displacement ??
       fp?.D_mean)
    : (displayResult?.displacement?.mean_displacement ?? fp?.D_mean);

  const maxDisp = isCalibrated
    ? (displayResult?.displacement?.physical_space?.max ??
       displayResult?.displacement?.physical_space?.max_displacement ??
       displayResult?.displacement?.max_displacement ??
       fp?.D_max)
    : (displayResult?.displacement?.max_displacement ?? fp?.D_max);

  // Real Principal Strain
  const meanPrincipalStrain =
    displayResult?.strain_statistics?.principal_strain_1?.mean ??
    displayResult?.principal_strain_1?.summary?.mean ??
    fp?.epsilon_principal;

  const maxPrincipalStrain =
    displayResult?.strain_statistics?.principal_strain_1?.max ??
    displayResult?.principal_strain_1?.summary?.max ??
    fp?.epsilon_max;

  // Real Advanced Metrics
  const motionCoherence =
    displayResult?.advanced_metrics?.motion_coherence?.mean ?? fp?.C;
  const anisotropy =
    displayResult?.advanced_metrics?.anisotropy?.mean ?? fp?.AI;
  const strainEntropy =
    displayResult?.advanced_metrics?.entropy ?? fp?.H;


  // Real Quality Control
  const qc = displayResult?.quality_control;
  const qcScore = qc?.score;
  const qcLevel = qc?.level || (qcScore ? (qcScore >= 75 ? "High" : qcScore >= 50 ? "Moderate" : "Low") : "Evaluated");

  // Warnings list
  const warningsList = [
    ...(qc?.warnings || []),
    ...(displayResult?.tracking_warning ? [displayResult.tracking_warning] : []),
  ];

  // Copy Analysis ID to clipboard
  const handleCopyId = (e) => {
    e.stopPropagation();
    if (activeRecordId) {
      navigator.clipboard?.writeText(activeRecordId);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  // Direct client-side JSON export of real analysis result
  const handleExportJSON = () => {
    if (!displayResult) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(displayResult, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `cardiac_analysis_${(activeRecordId || "result").slice(0, 8)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleExpandImage = ({ title, url, description }) => {
    setModalState({
      isOpen: true,
      imageSrc: url,
      title,
      description,
    });
  };

  const handleCloseModal = () => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  };

  // Filtered History List
  const filteredHistory = useMemo(() => {
    return historyList.filter((item) => {
      if (historyFilterType === "single_pair" && item.type === "temporal") return false;
      if (historyFilterType === "temporal" && item.type !== "temporal") return false;
      if (historySearch.trim()) {
        const q = historySearch.toLowerCase();
        const idMatch = item.id?.toLowerCase().includes(q);
        const studyMatch = item.study?.title?.toLowerCase().includes(q);
        const typeMatch = item.type?.toLowerCase().includes(q);
        return idMatch || studyMatch || typeMatch;
      }
      return true;
    });
  }, [historyList, historySearch, historyFilterType]);

  return (
    <div className="cdl-results-page">
      {/* ====================================================================
          1. HEADER & BREADCRUMB
          ==================================================================== */}
      <div className="cdl-results-header-wrap">
        <div>
          <div className="cdl-results-breadcrumb">
            <Link to="/" className="bc-home">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              Research
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Analysis Results</span>
          </div>
          <h2 className="cdl-results-title">Analysis Results</h2>
          <p className="cdl-results-subtitle">
            Scientific deformation inspection workspace — high-density displacement vector fields, strain tensor components, 10-D signature fingerprints, and computational quality verification.
          </p>
        </div>

        {/* Header Action Toolbar */}
        <div className="cdl-results-header-actions">
          {activeRecordId && (
            <>
              <Link
                to={`/explorer/${activeRecordId}`}
                className="cdl-action-btn cdl-action-btn-cyan"
                title="Launch Deep Interactive Analysis Explorer"
              >
                🔭 Open Explorer
              </Link>
              <Link
                to="/comparison"
                state={{ primaryId: activeRecordId }}
                className="cdl-action-btn cdl-action-btn-secondary"
                title="Compare this analysis side-by-side with another session"
              >
                ⚖️ Compare
              </Link>
              {activeReport?.reportUrl ? (
                <a
                  href={activeReport.reportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cdl-action-btn cdl-action-btn-primary"
                  title="Open generated publication-grade PDF report"
                >
                  📄 Open PDF Report
                </a>
              ) : (
                <button
                  className="cdl-action-btn cdl-action-btn-primary"
                  disabled={activeReport?.loading}
                  onClick={() => handleGenerateReport(null, activeRecordId)}
                  title="Generate publication-grade PDF summary report"
                >
                  {activeReport?.loading ? (
                    <>
                      <span className="spinner"></span> Generating PDF...
                    </>
                  ) : (
                    "📄 Generate Report"
                  )}
                </button>
              )}
              <button
                className="cdl-action-btn cdl-action-btn-secondary"
                onClick={handleExportJSON}
                title="Export raw analysis JSON output for local analysis"
              >
                💾 Export Data
              </button>
            </>
          )}

          <button
            className="cdl-action-btn cdl-action-btn-secondary"
            onClick={() => setHistoryExpanded((prev) => !prev)}
            title="Toggle previous analyses archive shelf"
          >
            🗂️ History ({historyList.length})
          </button>

          <button
            className="cdl-action-btn cdl-action-btn-secondary"
            onClick={fetchHistory}
            disabled={loadingHistory}
            title="Refresh analysis records from backend"
          >
            {loadingHistory ? "..." : "🔄 Refresh"}
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMsg && (
        <div className="status-banner loading" style={{ margin: "2px 0" }}>
          {actionMsg}
        </div>
      )}

      {/* History Loading Notice */}
      {loadingHistory && (
        <div className="status-banner loading">
          <span className="spinner"></span>
          Synchronizing analysis records from backend repository...
        </div>
      )}

      {/* History Error Notice */}
      {historyError && !loadingHistory && (
        <div className="status-banner error">
          <strong>Backend Service Notice:</strong> {historyError}
        </div>
      )}

      {/* ====================================================================
          2. EMPTY STATE (When no results and no history)
          ==================================================================== */}
      {!loadingHistory && historyList.length === 0 && !displayResult && (
        <div className="cdl-empty-card">
          <div className="cdl-empty-icon">📊</div>
          <h3 className="cdl-empty-title">No analysis results available yet</h3>
          <p className="cdl-empty-text">
            Execute a single-pair differential strain analysis or a temporal cardiac sequence to inspect dense displacement vector fields, continuum strain tensor components, and generate publication-grade PDF summaries.
          </p>
          <div className="cdl-empty-actions">
            <Link to="/analysis" className="cdl-action-btn cdl-action-btn-primary">
              🔬 New Single-Pair Analysis
            </Link>
            <Link to="/temporal" className="cdl-action-btn cdl-action-btn-cyan">
              ⏱️ New Temporal Analysis
            </Link>
          </div>
        </div>
      )}

      {/* ====================================================================
          3. ACTIVE RESULT WORKSPACE (When result is available)
          ==================================================================== */}
      {displayResult && (
        <>
          {/* Metadata & Status Strip */}
          <div className="cdl-meta-banner">
            <div className="cdl-meta-chips">
              {activeRecordId && (
                <span className="cdl-meta-chip cdl-meta-chip-blue" title={activeRecordId}>
                  <strong>ID:</strong> <code>{activeRecordId.slice(0, 8)}...</code>
                  <button
                    className="cdl-copy-id-btn"
                    onClick={handleCopyId}
                    title="Copy full UUID"
                  >
                    {copiedId ? "✓ Copied" : "📋"}
                  </button>
                </span>
              )}

              <span className="cdl-meta-chip">
                <strong>Type:</strong> {isTemporal ? "⏱️ Temporal Sequence" : "🔬 Single Pair Differential"}
              </span>

              {displayRecord?.study ? (
                <span className="cdl-meta-chip cdl-meta-chip-cyan" title={displayRecord.study.title}>
                  📁 <strong>Study:</strong> {displayRecord.study.title}
                </span>
              ) : (
                <span className="cdl-meta-chip">📁 Independent Analysis</span>
              )}

              {/* Scope & ROI */}
              {displayResult?.analysis_scope && (
                <span className={`cdl-meta-chip ${displayResult.analysis_scope.mode !== "full_image" ? "cdl-meta-chip-amber" : ""}`}>
                  🎯 <strong>Scope:</strong>{" "}
                  {displayResult.analysis_scope.mode === "tracked_roi"
                    ? `Tracked ROI (${displayResult.analysis_scope.roi_type || "Geometric"})`
                    : displayResult.analysis_scope.mode === "roi"
                    ? `Fixed ROI (${displayResult.analysis_scope.roi_type || "Geometric"})`
                    : "Full Image Space"}
                  {displayResult.analysis_scope.pixel_count
                    ? ` • ${displayResult.analysis_scope.pixel_count.toLocaleString()} px`
                    : ""}
                </span>
              )}

              {/* Timestamp */}
              <span className="cdl-meta-chip">
                🕒 {formatDate(displayRecord?.timestamp || displayResult?.created_at || displayResult?.timestamp)}
              </span>
            </div>

            {/* Status Pills */}
            <div className="cdl-meta-status-wrap">
              <span className="cdl-status-pill complete">
                ✓ Analysis Complete
              </span>

              {qcScore !== undefined && (
                <span
                  className={`cdl-status-pill ${
                    qcLevel === "High" ? "complete" : qcLevel === "Moderate" ? "warning" : "error"
                  }`}
                  title={`Computational Quality Control Score: ${qcScore}/100`}
                >
                  🛡️ QC: {qcScore}/100 ({qcLevel})
                </span>
              )}

              {isCalibrated && (
                <span className="cdl-meta-chip cdl-meta-chip-purple" title={`Calibrated: ${cal?.pixel_spacing_x}x${cal?.pixel_spacing_y} ${dispUnit}/px`}>
                  📐 Calibrated ({dispUnit})
                </span>
              )}
            </div>
          </div>

          {/* Sticky Section Navigator */}
          <SectionNav />

          {/* ================================================================
              4. TOP METRIC STRIP (QUANTITATIVE KPI TILES)
              ================================================================ */}
          <div id="section-overview" className="cdl-results-metric-strip">
            {/* Mean Displacement */}
            <div className="cdl-metric-tile tile-blue">
              <div className="cdl-metric-tile-top">
                <span className="cdl-metric-tile-label">Mean Displacement</span>
                <span className="cdl-metric-tile-icon">🌊</span>
              </div>
              <div className="cdl-metric-tile-body">
                <span className="cdl-metric-tile-val">{formatNumber(meanDisp)}</span>
                <span className="cdl-metric-tile-unit">{dispUnit}</span>
              </div>
              <span className="cdl-metric-tile-context">
                {isCalibrated ? "Calibrated spatial distance" : "Euclidean magnitude (px)"}
              </span>
            </div>

            {/* Maximum Displacement */}
            <div className="cdl-metric-tile tile-indigo">
              <div className="cdl-metric-tile-top">
                <span className="cdl-metric-tile-label">Peak Displacement</span>
                <span className="cdl-metric-tile-icon">⚡</span>
              </div>
              <div className="cdl-metric-tile-body">
                <span className="cdl-metric-tile-val">{formatNumber(maxDisp)}</span>
                <span className="cdl-metric-tile-unit">{dispUnit}</span>
              </div>
              <span className="cdl-metric-tile-context">Maximum apparent regional motion</span>
            </div>

            {/* Mean Principal Strain */}
            <div className="cdl-metric-tile tile-purple">
              <div className="cdl-metric-tile-top">
                <span className="cdl-metric-tile-label">Principal Strain (Mean)</span>
                <span className="cdl-metric-tile-icon">📐</span>
              </div>
              <div className="cdl-metric-tile-body">
                <span className="cdl-metric-tile-val">{formatNumber(meanPrincipalStrain)}</span>
                <span className="cdl-metric-tile-unit">unitless</span>
              </div>
              <span className="cdl-metric-tile-context">Tensor eigenvalue mean (ε₁)</span>
            </div>

            {/* Peak Principal Strain */}
            <div className="cdl-metric-tile tile-amber">
              <div className="cdl-metric-tile-top">
                <span className="cdl-metric-tile-label">Peak Strain (Max)</span>
                <span className="cdl-metric-tile-icon">💥</span>
              </div>
              <div className="cdl-metric-tile-body">
                <span className="cdl-metric-tile-val">{formatNumber(maxPrincipalStrain)}</span>
                <span className="cdl-metric-tile-unit">unitless</span>
              </div>
              <span className="cdl-metric-tile-context">Maximum regional deformation</span>
            </div>

            {/* Motion Coherence */}
            {motionCoherence !== undefined && (
              <div className="cdl-metric-tile tile-teal">
                <div className="cdl-metric-tile-top">
                  <span className="cdl-metric-tile-label">Motion Coherence</span>
                  <span className="cdl-metric-tile-icon">🎯</span>
                </div>
                <div className="cdl-metric-tile-body">
                  <span className="cdl-metric-tile-val">{formatNumber(motionCoherence)}</span>
                  <span className="cdl-metric-tile-unit">[0-1]</span>
                </div>
                <span className="cdl-metric-tile-context">Local vector field alignment</span>
              </div>
            )}

            {/* Strain Anisotropy */}
            {anisotropy !== undefined && (
              <div className="cdl-metric-tile tile-cyan">
                <div className="cdl-metric-tile-top">
                  <span className="cdl-metric-tile-label">Anisotropy Index</span>
                  <span className="cdl-metric-tile-icon">🧭</span>
                </div>
                <div className="cdl-metric-tile-body">
                  <span className="cdl-metric-tile-val">{formatNumber(anisotropy)}</span>
                  <span className="cdl-metric-tile-unit">[0-1]</span>
                </div>
                <span className="cdl-metric-tile-context">Directional asymmetry ratio</span>
              </div>
            )}

            {/* Strain Entropy */}
            {strainEntropy !== undefined && (
              <div className="cdl-metric-tile tile-emerald">
                <div className="cdl-metric-tile-top">
                  <span className="cdl-metric-tile-label">Strain Entropy</span>
                  <span className="cdl-metric-tile-icon">📊</span>
                </div>
                <div className="cdl-metric-tile-body">
                  <span className="cdl-metric-tile-val">{formatNumber(strainEntropy)}</span>
                  <span className="cdl-metric-tile-unit">nats</span>
                </div>
                <span className="cdl-metric-tile-context">Deformation field dispersion</span>
              </div>
            )}

            {/* Computational Quality */}
            {qcScore !== undefined && (
              <div className="cdl-metric-tile tile-blue">
                <div className="cdl-metric-tile-top">
                  <span className="cdl-metric-tile-label">Quality Score</span>
                  <span className="cdl-metric-tile-icon">🛡️</span>
                </div>
                <div className="cdl-metric-tile-body">
                  <span className="cdl-metric-tile-val">{qcScore}</span>
                  <span className="cdl-metric-tile-unit">/ 100</span>
                </div>
                <span className="cdl-metric-tile-context">{qcLevel} computational fidelity</span>
              </div>
            )}
          </div>

          {/* ================================================================
              5. MAIN SCIENTIFIC VISUALIZATION WORKSPACE (CENTERPIECE)
              ================================================================ */}
          {!isTemporal && outputs && (
            <div className="cdl-vis-workspace">
              <div className="cdl-vis-header-row">
                <div className="cdl-vis-header-left">
                  <h3 className="cdl-vis-heading">
                    🔬 Scientific Deformation Workspace
                  </h3>
                  <p className="cdl-vis-subheading">
                    Multi-scale optical flow magnitude, strain tensor derivatives, and spatial mechanical projections.
                  </p>
                </div>

                {/* Tab Navigation */}
                <div className="cdl-vis-tabs">
                  <button
                    className={`cdl-vis-tab-btn ${activeVisTab === "all" ? "active" : ""}`}
                    onClick={() => setActiveVisTab("all")}
                  >
                    All Maps
                  </button>
                  <button
                    className={`cdl-vis-tab-btn ${activeVisTab === "displacement" ? "active" : ""}`}
                    onClick={() => setActiveVisTab("displacement")}
                  >
                    Displacement &amp; Motion
                  </button>
                  <button
                    className={`cdl-vis-tab-btn ${activeVisTab === "strain" ? "active" : ""}`}
                    onClick={() => setActiveVisTab("strain")}
                  >
                    Strain Tensor
                  </button>
                  <button
                    className={`cdl-vis-tab-btn ${activeVisTab === "principal" ? "active" : ""}`}
                    onClick={() => setActiveVisTab("principal")}
                  >
                    Principal Strain
                  </button>
                  {(cardiacOutputs.radial_map || cardiacOutputs.circumferential_map) && (
                    <button
                      className={`cdl-vis-tab-btn ${activeVisTab === "directional" ? "active" : ""}`}
                      onClick={() => setActiveVisTab("directional")}
                    >
                      Directional
                    </button>
                  )}
                  {advOutputs.motion_coherence_map && (
                    <button
                      className={`cdl-vis-tab-btn ${activeVisTab === "advanced" ? "active" : ""}`}
                      onClick={() => setActiveVisTab("advanced")}
                    >
                      Advanced Continuum
                    </button>
                  )}
                  {outputs.roi_overlay && (
                    <button
                      className={`cdl-vis-tab-btn ${activeVisTab === "roi" ? "active" : ""}`}
                      onClick={() => setActiveVisTab("roi")}
                    >
                      ROI Geometry
                    </button>
                  )}
                </div>
              </div>

              {/* Visualization Stage Grid */}
              <div className="cdl-vis-stage-grid">
                {/* 1. DISPLACEMENT FIELD & MOTION VECTORS */}
                {(activeVisTab === "all" || activeVisTab === "displacement") && (
                  <>
                    <ScientificVisPanel
                      title={isCalibrated ? `Displacement Field (${dispUnit})` : "Displacement Field (Pixels)"}
                      path={outputs.displacement_heatmap || displayResult?.heatmap}
                      description="Apparent optical flow Euclidean magnitude |d| = sqrt(u² + v²)"
                      metricBadge={`Mean: ${formatNumber(meanDisp)} ${dispUnit}`}
                      onExpand={handleExpandImage}
                    />

                    {outputs.motion_vector_map && (
                      <ScientificVisPanel
                        title="Motion Vector Map"
                        path={outputs.motion_vector_map}
                        description="Dense 2D displacement vectors superimposed over reference image"
                        metricBadge="Farnebäck Optical Flow"
                        onExpand={handleExpandImage}
                      />
                    )}
                  </>
                )}

                {/* 2. STRAIN TENSOR MAPS */}
                {(activeVisTab === "all" || activeVisTab === "strain") && (
                  <>
                    {outputs.exx_heatmap && (
                      <ScientificVisPanel
                        title="Normal Strain εxx"
                        path={outputs.exx_heatmap}
                        description="Horizontal normal deformation component (∂u/∂x) representing lateral shortening"
                        metricBadge="Dimensionless"
                        onExpand={handleExpandImage}
                      />
                    )}

                    {outputs.eyy_heatmap && (
                      <ScientificVisPanel
                        title="Normal Strain εyy"
                        path={outputs.eyy_heatmap}
                        description="Vertical normal deformation component (∂v/∂y) representing longitudinal motion"
                        metricBadge="Dimensionless"
                        onExpand={handleExpandImage}
                      />
                    )}

                    {outputs.exy_heatmap && (
                      <ScientificVisPanel
                        title="Shear Strain εxy"
                        path={outputs.exy_heatmap}
                        description="In-plane angular distortion 0.5 × (∂u/∂y + ∂v/∂x)"
                        metricBadge="Dimensionless"
                        onExpand={handleExpandImage}
                      />
                    )}
                  </>
                )}

                {/* 3. PRINCIPAL STRAIN & DIRECTION */}
                {(activeVisTab === "all" || activeVisTab === "principal") && (
                  <>
                    {outputs.principal_strain_heatmap && (
                      <ScientificVisPanel
                        title="Principal Strain (Major ε₁)"
                        path={outputs.principal_strain_heatmap}
                        description="Maximum eigenvalue field of continuum strain tensor"
                        metricBadge={`Mean: ${formatNumber(meanPrincipalStrain)}`}
                        onExpand={handleExpandImage}
                      />
                    )}

                    {outputs.principal_direction_map && (
                      <ScientificVisPanel
                        title="Principal Direction Field"
                        path={outputs.principal_direction_map}
                        description="Estimated eigenvectors depicting the primary orientation axis of principal strain"
                        metricBadge="Orientation Axis"
                        onExpand={handleExpandImage}
                      />
                    )}
                  </>
                )}

                {/* 4. DIRECTIONAL / CARDIAC PROJECTIONS */}
                {(activeVisTab === "all" || activeVisTab === "directional") && (
                  <>
                    {cardiacOutputs.radial_map && (
                      <ScientificVisPanel
                        title="Radial Deformation Map"
                        path={cardiacOutputs.radial_map}
                        description="Motion projection along radial axes extending outwards from ventricular centroid"
                        metricBadge="Transmural Projection"
                        onExpand={handleExpandImage}
                      />
                    )}

                    {cardiacOutputs.circumferential_map && (
                      <ScientificVisPanel
                        title="Circumferential Deformation Map"
                        path={cardiacOutputs.circumferential_map}
                        description="Motion projection along circumferential tangential axes orthogonal to radial vectors"
                        metricBadge="Tangential Projection"
                        onExpand={handleExpandImage}
                      />
                    )}
                  </>
                )}

                {/* 5. ADVANCED CONTINUUM METRICS */}
                {(activeVisTab === "all" || activeVisTab === "advanced") && (
                  <>
                    {advOutputs.motion_coherence_map && (
                      <ScientificVisPanel
                        title="Motion Coherence Map"
                        path={advOutputs.motion_coherence_map}
                        description="Local vector consistency measuring alignment between neighboring displacement vectors"
                        metricBadge="Range [0, 1]"
                        onExpand={handleExpandImage}
                      />
                    )}

                    {advOutputs.strain_gradient_map && (
                      <ScientificVisPanel
                        title="Strain Gradient Map"
                        path={advOutputs.strain_gradient_map}
                        description="Spatial rate of change of principal strain fields across regional tissue boundaries"
                        metricBadge="Spatial Gradient"
                        onExpand={handleExpandImage}
                      />
                    )}

                    {advOutputs.anisotropy_map && (
                      <ScientificVisPanel
                        title="Strain Anisotropy Map"
                        path={advOutputs.anisotropy_map}
                        description="Directional preference index (|e1 - e2| / (|e1| + |e2|)) of local deformation"
                        metricBadge="Range [0, 1]"
                        onExpand={handleExpandImage}
                      />
                    )}

                    {advOutputs.deformation_energy_map && (
                      <ScientificVisPanel
                        title="Deformation Energy Map"
                        path={advOutputs.deformation_energy_map}
                        description="Surrogate strain energy density highlighting regions of concentrated mechanical work"
                        metricBadge="Energy Density"
                        onExpand={handleExpandImage}
                      />
                    )}
                  </>
                )}

                {/* 6. ROI GEOMETRY OVERLAY */}
                {(activeVisTab === "all" || activeVisTab === "roi") && outputs.roi_overlay && (
                  <ScientificVisPanel
                    title={`ROI Boundary Overlay (${displayResult.analysis_scope?.roi_type || "Custom"})`}
                    path={outputs.roi_overlay}
                    description="Active ROI boundary contour (yellow) and tinted mask overlay on reference frame"
                    metricBadge={`${displayResult.analysis_scope?.pixel_count?.toLocaleString() || "active"} px`}
                    onExpand={handleExpandImage}
                  />
                )}
              </div>
            </div>
          )}

          {/* ================================================================
              6. ADVANCED METRICS GROUPED SUMMARY
              ================================================================ */}
          {displayResult?.advanced_metrics && (
            <div id="section-advanced" className="cdl-adv-metrics-section">
              <div className="cdl-vis-header-left">
                <h3 className="cdl-vis-heading">
                  📊 Quantitative Deformation Descriptors
                </h3>
                <p className="cdl-vis-subheading">
                  Second-order kinematic statistics, directional projections, and mathematical information entropy.
                </p>
              </div>

              <div className="cdl-adv-groups-grid">
                {/* Group 1: Directional Components */}
                {(displayResult?.cardiac_deformation?.radial || displayResult?.cardiac_deformation?.circumferential) && (
                  <div className="cdl-adv-group-card">
                    <h4 className="cdl-adv-group-title">
                      🧭 Directional Projections
                    </h4>
                    {displayResult?.cardiac_deformation?.radial && (
                      <div className="cdl-adv-metric-item">
                        <div className="cdl-adv-metric-info">
                          <span className="cdl-adv-metric-name">Radial Deformation</span>
                          <span className="cdl-adv-metric-desc">Transmural thickening / thinning</span>
                        </div>
                        <div className="cdl-adv-metric-stats">
                          <span className="cdl-adv-metric-val">{formatNumber(displayResult.cardiac_deformation.radial.mean)}</span>
                          <span className="cdl-adv-metric-range">Max: {formatNumber(displayResult.cardiac_deformation.radial.max)}</span>
                        </div>
                      </div>
                    )}
                    {displayResult?.cardiac_deformation?.circumferential && (
                      <div className="cdl-adv-metric-item">
                        <div className="cdl-adv-metric-info">
                          <span className="cdl-adv-metric-name">Circumferential Deformation</span>
                          <span className="cdl-adv-metric-desc">Tangential perimeter shortening</span>
                        </div>
                        <div className="cdl-adv-metric-stats">
                          <span className="cdl-adv-metric-val">{formatNumber(displayResult.cardiac_deformation.circumferential.mean)}</span>
                          <span className="cdl-adv-metric-range">Max: {formatNumber(displayResult.cardiac_deformation.circumferential.max)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Group 2: Kinematic Consistency */}
                <div className="cdl-adv-group-card">
                  <h4 className="cdl-adv-group-title">
                    🌊 Flow Consistency &amp; Gradient
                  </h4>
                  {motionCoherence !== undefined && (
                    <div className="cdl-adv-metric-item">
                      <div className="cdl-adv-metric-info">
                        <span className="cdl-adv-metric-name">Motion Coherence (C)</span>
                        <span className="cdl-adv-metric-desc">Neighboring vector parallelism</span>
                      </div>
                      <div className="cdl-adv-metric-stats">
                        <span className="cdl-adv-metric-val">{formatNumber(motionCoherence)}</span>
                        <span className="cdl-adv-metric-range">Range: [0, 1]</span>
                      </div>
                    </div>
                  )}
                  {displayResult?.advanced_metrics?.strain_gradient && (
                    <div className="cdl-adv-metric-item">
                      <div className="cdl-adv-metric-info">
                        <span className="cdl-adv-metric-name">Strain Gradient Magnitude</span>
                        <span className="cdl-adv-metric-desc">Spatial rate of tensor variation</span>
                      </div>
                      <div className="cdl-adv-metric-stats">
                        <span className="cdl-adv-metric-val">{formatNumber(displayResult.advanced_metrics.strain_gradient.mean)}</span>
                        <span className="cdl-adv-metric-range">Max: {formatNumber(displayResult.advanced_metrics.strain_gradient.max)}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Group 3: Anisotropy & Energy */}
                <div className="cdl-adv-group-card">
                  <h4 className="cdl-adv-group-title">
                    ⚡ Anisotropy &amp; Strain Energy
                  </h4>
                  {anisotropy !== undefined && (
                    <div className="cdl-adv-metric-item">
                      <div className="cdl-adv-metric-info">
                        <span className="cdl-adv-metric-name">Strain Anisotropy Index</span>
                        <span className="cdl-adv-metric-desc">Directional bias ratio (|e1-e2| / sum)</span>
                      </div>
                      <div className="cdl-adv-metric-stats">
                        <span className="cdl-adv-metric-val">{formatNumber(anisotropy)}</span>
                        <span className="cdl-adv-metric-range">Range: [0, 1]</span>
                      </div>
                    </div>
                  )}
                  {displayResult?.advanced_metrics?.deformation_energy && (
                    <div className="cdl-adv-metric-item">
                      <div className="cdl-adv-metric-info">
                        <span className="cdl-adv-metric-name">Deformation Energy Proxy</span>
                        <span className="cdl-adv-metric-desc">Surrogate strain energy density</span>
                      </div>
                      <div className="cdl-adv-metric-stats">
                        <span className="cdl-adv-metric-val">{formatNumber(displayResult.advanced_metrics.deformation_energy.mean)}</span>
                        <span className="cdl-adv-metric-range">Max: {formatNumber(displayResult.advanced_metrics.deformation_energy.max)}</span>
                      </div>
                    </div>
                  )}
                  {strainEntropy !== undefined && (
                    <div className="cdl-adv-metric-item">
                      <div className="cdl-adv-metric-info">
                        <span className="cdl-adv-metric-name">Strain Entropy (H)</span>
                        <span className="cdl-adv-metric-desc">Shannon entropy of strain field</span>
                      </div>
                      <div className="cdl-adv-metric-stats">
                        <span className="cdl-adv-metric-val">{formatNumber(strainEntropy)}</span>
                        <span className="cdl-adv-metric-range">Nats</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ================================================================
              7. SPATIAL CALIBRATION CARD (If calibrated)
              ================================================================ */}
          {isCalibrated && (
            <div className="cdl-calibration-card">
              <div className="cdl-calibration-details">
                <div className="cdl-cal-prop">
                  <span className="cdl-cal-prop-label">Pixel Spacing X</span>
                  <span className="cdl-cal-prop-val">{cal.pixel_spacing_x} {dispUnit}/px</span>
                </div>
                <div className="cdl-cal-prop">
                  <span className="cdl-cal-prop-label">Pixel Spacing Y</span>
                  <span className="cdl-cal-prop-val">{cal.pixel_spacing_y} {dispUnit}/px</span>
                </div>
                <div className="cdl-cal-prop">
                  <span className="cdl-cal-prop-label">Physical Displacement Mean</span>
                  <span className="cdl-cal-prop-val">{formatNumber(meanDisp)} {dispUnit}</span>
                </div>
                <div className="cdl-cal-prop">
                  <span className="cdl-cal-prop-label">Physical Displacement Peak</span>
                  <span className="cdl-cal-prop-val">{formatNumber(maxDisp)} {dispUnit}</span>
                </div>
              </div>

              <div className="cdl-cal-disclaimer">
                ℹ️ <strong>Note:</strong> Strain is dimensionless (ΔL / L₀), remaining invariant under uniform spatial scaling.
              </div>
            </div>
          )}

          {/* ================================================================
              8. WARNINGS & LIMITATIONS PANEL (If present)
              ================================================================ */}
          {warningsList.length > 0 && (
            <div className="cdl-warnings-panel">
              <div className="cdl-warnings-header">
                ⚠️ Computational Warnings &amp; Quality Notes ({warningsList.length})
              </div>
              <ul className="cdl-warnings-list">
                {warningsList.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* ================================================================
              9. REGION OF INTEREST (ROI) ANALYSIS SECTION (If active)
              ================================================================ */}
          {displayResult?.roi_metrics && (
            <div id="section-roi">
              <ROIComparisonView result={displayResult} />
            </div>
          )}

          {/* Tracked ROI Keyframe Gallery & Trajectory */}
          {displayResult?.tracking_previews && (
            <div className="results-card">
              <TrackedROIKeyframeGallery
                trackingPreviews={displayResult.tracking_previews}
                trackingPath={displayResult.tracking_path}
              />
            </div>
          )}

          {displayResult?.tracking_path && (
            <div className="results-card">
              <TrackingTrajectoryChart
                trackingPath={displayResult.tracking_path}
                trackingSummary={displayResult.tracking_summary}
              />
            </div>
          )}

          {/* ================================================================
              10. TEMPORAL DYNAMICS (If temporal analysis)
              ================================================================ */}
          {isTemporal && (
            <div id="section-motion" className="results-card">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
                <div>
                  <h4 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#0f172a" }}>
                    ⏱️ Temporal Strain Dynamics Across Cardiac Cycle
                  </h4>
                  <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#64748b" }}>
                    Frame-by-frame principal strain trajectories, dyssynchrony indices, and cyclic deformation curves.
                  </p>
                </div>
                <Link to="/temporal" className="cdl-action-btn cdl-action-btn-cyan">
                  ⏱️ Open Temporal Analysis Workspace
                </Link>
              </div>
              <TemporalChart temporalData={displayResult} />
            </div>
          )}

          {/* ================================================================
              11. QUALITY CONTROL & COMPUTATIONAL INTEGRITY
              ================================================================ */}
          <div id="section-qc">
            <QualityControlCard
              qc={displayResult?.quality_control}
              analysisId={activeRecordId}
              onQcUpdated={(newQc) => {
                if (selectedRecord) {
                  setSelectedRecord((prev) =>
                    prev ? { ...prev, result: { ...prev.result, quality_control: newQc } } : prev
                  );
                }
              }}
            />
          </div>

          {/* ================================================================
              12. CARDIAC DEFORMATION FINGERPRINT
              ================================================================ */}
          {displayResult.cardiac_deformation_fingerprint && (
            <div id="section-fingerprint" className="results-card fingerprint-wrapper-section">
              <div style={{ marginBottom: "12px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#2563eb", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  10-Dimensional Vector
                </span>
                <h4 style={{ margin: "4px 0", fontSize: "18px", fontWeight: 700, color: "#0f172a" }}>
                  Cardiac Deformation Fingerprint
                </h4>
                <p style={{ margin: 0, fontSize: "13px", color: "#64748b" }}>
                  Computational image-derived deformation signature characterizing myocardial biomechanical state.
                </p>
              </div>

              <FingerprintChart
                fingerprintData={displayResult.cardiac_deformation_fingerprint}
                fingerprint={fp}
              />
            </div>
          )}

          {/* ================================================================
              13. SCIENTIFIC INTERPRETATION & METHODOLOGY
              ================================================================ */}
          <div id="section-interpretation">
            <InterpretationPanel />
          </div>

          <div id="section-methodology">
            <MethodologySection />
          </div>

          {/* ================================================================
              14. RESEARCH DISCLAIMER
              ================================================================ */}
          <div className="cdl-disclaimer-card">
            <div className="cdl-disclaimer-icon">🛡️</div>
            <div className="cdl-disclaimer-content">
              <strong>Research Prototype:</strong> This software presents computational image-derived measurements generated by an experimental research system. The computed fields, strain tensors, and deformation signatures are intended strictly for scientific evaluation and benchmarking, and do not constitute clinical diagnoses, prognoses, or treatment recommendations.
            </div>
          </div>
        </>
      )}

      {/* ====================================================================
          15. SAVED ANALYSIS HISTORY ARCHIVE SHELF (DRAWER / INTERACTIVE TABLE)
          ==================================================================== */}
      {historyList.length > 0 && (
        <section className="cdl-history-archive-section">
          <div
            className="cdl-history-archive-header"
            onClick={() => setHistoryExpanded((prev) => !prev)}
            title="Click to expand or collapse session archive"
          >
            <div className="cdl-history-archive-title-wrap">
              <span style={{ fontSize: "18px" }}>🗂️</span>
              <h3 className="cdl-history-archive-title">Analysis History Archive</h3>
              <span className="cdl-history-archive-count">
                {historyList.length} {historyList.length === 1 ? "Session" : "Sessions"}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 500 }}>
                {historyExpanded ? "Hide Archive" : "Show All Archive Records"}
              </span>
              <span className={`cdl-history-toggle-icon ${historyExpanded ? "expanded" : ""}`}>
                ▼
              </span>
            </div>
          </div>

          {historyExpanded && (
            <div className="cdl-history-archive-body">
              {/* Search & Filter Toolbar */}
              <div className="cdl-history-toolbar">
                <input
                  type="text"
                  className="cdl-history-search-input"
                  placeholder="🔍 Search ID, study or type..."
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                />

                <div className="cdl-history-filter-btns">
                  <button
                    className={`cdl-history-filter-btn ${historyFilterType === "all" ? "active" : ""}`}
                    onClick={() => setHistoryFilterType("all")}
                  >
                    All ({historyList.length})
                  </button>
                  <button
                    className={`cdl-history-filter-btn ${historyFilterType === "single_pair" ? "active" : ""}`}
                    onClick={() => setHistoryFilterType("single_pair")}
                  >
                    🔬 Single-Pair
                  </button>
                  <button
                    className={`cdl-history-filter-btn ${historyFilterType === "temporal" ? "active" : ""}`}
                    onClick={() => setHistoryFilterType("temporal")}
                  >
                    ⏱️ Temporal
                  </button>
                  <button
                    className="cdl-table-action-btn btn-delete"
                    onClick={handleClearAllHistory}
                    title="Clear all stored history from backend"
                    style={{ marginLeft: "8px" }}
                  >
                    🗑️ Clear All
                  </button>
                </div>
              </div>

              {/* Table */}
              <div className="cdl-history-table-wrap">
                <table className="cdl-history-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Scope</th>
                      <th>Analysis ID</th>
                      <th>Study</th>
                      <th>Timestamp</th>
                      <th>Mean Disp</th>
                      <th>Peak Strain</th>
                      <th>Fingerprint</th>
                      <th>QC Score</th>
                      <th>Report</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHistory.map((item) => {
                      const isSelected = activeRecordId === item.id;
                      const isTemp = item.type === "temporal";
                      const s = item.summary || {};
                      const rState = reportState[item.id] || {};

                      return (
                        <tr
                          key={item.id}
                          className={isSelected ? "active-row" : ""}
                          onClick={() => handleSelectRecord(item.id)}
                          title="Click to load this analysis in workspace"
                        >
                          <td>
                            <span
                              className={`history-type-badge ${
                                isTemp ? "badge-temporal" : "badge-single"
                              }`}
                            >
                              {isTemp ? "⏱️ Temporal" : "🔬 Single Pair"}
                            </span>
                          </td>
                          <td>
                            {s.roi?.enabled ? (
                              <span className="badge badge-warning" title={`${s.roi.pixel_count || "ROI"} px`}>
                                ROI ({s.roi.type || "Custom"})
                              </span>
                            ) : (
                              <span className="badge badge-secondary">Full Image</span>
                            )}
                          </td>
                          <td>
                            <code style={{ fontSize: "12px", color: "#2563eb", fontWeight: 700 }}>
                              {item.id.slice(0, 8)}...
                            </code>
                          </td>
                          <td>
                            {item.study ? (
                              <span className="study-tag" title={item.study.title}>
                                📁 {item.study.title}
                              </span>
                            ) : (
                              <span className="no-study-tag">Independent</span>
                            )}
                          </td>
                          <td>{formatDate(item.timestamp)}</td>
                          <td>
                            {s.mean_displacement !== null && s.mean_displacement !== undefined
                              ? `${formatNumber(s.mean_displacement)} px`
                              : "N/A"}
                          </td>
                          <td>
                            {s.mean_principal_strain !== null && s.mean_principal_strain !== undefined
                              ? formatNumber(s.mean_principal_strain)
                              : "N/A"}
                          </td>
                          <td>
                            {s.has_fingerprint ? (
                              <span className="tag-available">✓ 10-D</span>
                            ) : (
                              <span className="tag-unavailable">N/A</span>
                            )}
                          </td>
                          <td>
                            {s.quality_control ? (
                              <span
                                className={`qc-table-pill ${s.quality_control.level?.toLowerCase()}`}
                                title={`Quality: ${s.quality_control.score}/100`}
                              >
                                {s.quality_control.score} ({s.quality_control.level})
                              </span>
                            ) : (
                              <span className="tag-unavailable">N/A</span>
                            )}
                          </td>
                          <td onClick={(e) => e.stopPropagation()}>
                            {rState.reportUrl ? (
                              <a
                                href={rState.reportUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="cdl-table-action-btn"
                                title="Open generated PDF report in new tab"
                              >
                                📄 Open PDF
                              </a>
                            ) : (
                              <button
                                className="cdl-table-action-btn"
                                disabled={rState.loading}
                                onClick={(e) => handleGenerateReport(e, item.id)}
                                title="Generate publication-grade PDF report"
                              >
                                {rState.loading ? "..." : "📄 PDF"}
                              </button>
                            )}
                          </td>
                          <td onClick={(e) => e.stopPropagation()}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <Link
                                to={`/explorer/${item.id}`}
                                className="cdl-table-action-btn"
                                title="Open interactive analysis explorer"
                                style={{ color: "#0284c7", borderColor: "#0284c7" }}
                              >
                                🔭 Explorer
                              </Link>
                              <Link
                                to={`/annotations/${item.id}`}
                                className="cdl-table-action-btn"
                                title="Annotate landmarks and contours"
                              >
                                ✏️ Annotate
                              </Link>
                              <button
                                className="cdl-table-action-btn btn-delete"
                                onClick={(e) => handleDeleteRecord(e, item.id)}
                                title="Delete this session record"
                              >
                                ✕ Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Reusable Fullscreen Image Viewer Modal */}
      <ImageViewerModal
        isOpen={modalState.isOpen}
        imageSrc={modalState.imageSrc}
        title={modalState.title}
        description={modalState.description}
        onClose={handleCloseModal}
      />
    </div>
  );
}
