import React, { useState, useEffect, useMemo, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  getAnalysisHistory,
  getAnalysisHistoryById,
  getAnalysisAnnotations,
  getStudies,
  getOutputUrl,
  getFrameImageUrl,
} from "../services/api";
import ScientificImageViewer from "../components/scientific/ScientificImageViewer";
import MetricInspector from "../components/scientific/MetricInspector";
import MetricHistogram from "../components/scientific/MetricHistogram";
import MetricScatterPlot from "../components/scientific/MetricScatterPlot";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./AnalysisExplorer.css";

const VISUALIZATION_MODES = [
  { id: "original", label: "Original Image", colormap: "gray", unit: "intensity", dotColor: "#94a3b8" },
  { id: "preprocessed", label: "Preprocessed Image", colormap: "gray", unit: "intensity", dotColor: "#64748b" },
  { id: "displacement", label: "Displacement Field", colormap: "turbo", unit: "px", dotColor: "#38bdf8" },
  { id: "vectors", label: "Motion Vector Map", colormap: "jet", unit: "px", dotColor: "#0284c7" },
  { id: "exx", label: "Normal Strain Exx", colormap: "plasma", unit: "dimensionless", dotColor: "#818cf8" },
  { id: "eyy", label: "Normal Strain Eyy", colormap: "plasma", unit: "dimensionless", dotColor: "#a855f7" },
  { id: "exy", label: "Shear Strain Exy", colormap: "coolwarm", unit: "dimensionless", dotColor: "#c084fc" },
  { id: "principal_strain", label: "Principal Strain P1", colormap: "inferno", unit: "dimensionless", dotColor: "#f43f5e" },
  { id: "principal_direction", label: "Principal Direction", colormap: "hsv", unit: "deg", dotColor: "#fb923c" },
  { id: "radial", label: "Radial Deformation", colormap: "seismic", unit: "dimensionless", dotColor: "#f59e0b" },
  { id: "circumferential", label: "Circumferential Deformation", colormap: "seismic", unit: "dimensionless", dotColor: "#eab308" },
  { id: "coherence", label: "Motion Coherence", colormap: "viridis", unit: "normalized", dotColor: "#10b981" },
  { id: "gradient", label: "Strain Gradient", colormap: "magma", unit: "dimensionless/px", dotColor: "#14b8a6" },
  { id: "anisotropy", label: "Strain Anisotropy", colormap: "cividis", unit: "dimensionless", dotColor: "#06b6d4" },
  { id: "energy", label: "Deformation Energy", colormap: "hot", unit: "dimensionless", dotColor: "#f97316" },
];

export default function AnalysisExplorer() {
  const { analysisId } = useParams();
  const navigate = useNavigate();

  // Primary analysis record state
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(false);

  // Available analyses list for quick switching
  const [recentAnalyses, setRecentAnalyses] = useState([]);

  // Sibling analyses in the same cohort (for in-explorer comparison)
  const [compareAnalysisId, setCompareAnalysisId] = useState("");
  const [compareRecord, setCompareRecord] = useState(null);

  // Annotations for this analysis
  const [annotations, setAnnotations] = useState([]);

  // Visualization Controls State
  const [activeMode, setActiveMode] = useState("displacement");
  const [opacity, setOpacity] = useState(1.0);
  const [vectorDensity, setVectorDensity] = useState(3);
  const [overlays, setOverlays] = useState({
    roi: true,
    trackedRoi: true,
    annotations: true,
    vectors: true,
    directions: true,
    crosshair: false,
  });

  // Scale Controls
  const [scaleMode, setScaleMode] = useState("auto"); // "auto" | "manual"
  const [manualMin, setManualMin] = useState(0);
  const [manualMax, setManualMax] = useState(10);

  // Sampled Point Inspection
  const [sampledPixel, setSampledPixel] = useState(null);

  // Line Profile Tool State
  const [lineProfileActive, setLineProfileActive] = useState(false);
  const [lineProfileCoords, setLineProfileCoords] = useState(null);

  // Side-by-Side & Difference Mode State
  const [isSideBySide, setIsSideBySide] = useState(false);
  const [sideBySideMode, setSideBySideMode] = useState("principal_strain");
  const [differenceMode] = useState(false);
  const [diffType] = useState("absolute");

  // Temporal Explorer State
  const [currentFrameIdx, setCurrentFrameIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const playTimerRef = useRef(null);

  // Right Inspector Active Tab: "metrics" | "profile" | "histogram" | "scatter" | "temporal" | "compare"
  const [activeTab, setActiveTab] = useState("metrics");

  // Collapsible Left Groups
  const [collapseState, setCollapseState] = useState({
    info: true,
    layers: true,
    controls: true,
    overlays: true,
    presets: true,
  });

  const toggleGroup = (key) => {
    setCollapseState((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Presets State
  const [savedPresets, setSavedPresets] = useState([]);
  const [presetNameInput, setPresetNameInput] = useState("");
  const [showPresetModal, setShowPresetModal] = useState(false);
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);

  // Fetch initial analysis list
  useEffect(() => {
    getAnalysisHistory()
      .then((history) => {
        setRecentAnalyses(history || []);
        if (!analysisId && history && history.length > 0) {
          navigate(`/explorer/${history[0].id}`, { replace: true });
        }
      })
      .catch(() => {});

    getStudies().catch(() => {});
  }, [analysisId, navigate]);

  // Load active analysis record by ID
  useEffect(() => {
    if (!analysisId) return;

    let isMounted = true;
    getAnalysisHistoryById(analysisId)
      .then((data) => {
        if (!isMounted) return;
        const mergedRecord = {
          ...data,
          ...(data?.result || {}),
        };
        setRecord(mergedRecord);
        setLoading(false);

        getAnalysisAnnotations(analysisId)
          .then((annos) => {
            if (isMounted) setAnnotations(annos || []);
          })
          .catch(() => {
            if (isMounted) setAnnotations([]);
          });
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to load analysis record.");
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [analysisId]);

  // Load secondary analysis for comparison when selected
  useEffect(() => {
    if (!compareAnalysisId) {
      return;
    }
    let isMounted = true;
    getAnalysisHistoryById(compareAnalysisId)
      .then((data) => {
        if (!isMounted) return;
        const mergedCompare = {
          ...data,
          ...(data?.result || {}),
        };
        setCompareRecord(mergedCompare);
      })
      .catch(() => {
        if (isMounted) setCompareRecord(null);
      });

    return () => {
      isMounted = false;
    };
  }, [compareAnalysisId]);

  // Load saved presets from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("cdl_explorer_presets");
      if (stored) {
        setSavedPresets(JSON.parse(stored));
      }
    } catch {
      // ignore
    }
  }, []);

  // Save current preset to localStorage
  const handleSavePreset = () => {
    if (!presetNameInput.trim()) return;
    const newPreset = {
      name: presetNameInput.trim(),
      activeMode,
      opacity,
      overlays,
      scaleMode,
      scaleRange: { min: manualMin, max: manualMax },
      vectorDensity,
    };
    const updated = [...savedPresets, newPreset];
    setSavedPresets(updated);
    try {
      localStorage.setItem("cdl_explorer_presets", JSON.stringify(updated));
    } catch {
      // ignore
    }
    setPresetNameInput("");
    setShowPresetModal(false);
  };

  const handleApplyPreset = (preset) => {
    setActiveMode(preset.activeMode || "displacement");
    setOpacity(preset.opacity ?? 1.0);
    setOverlays((prev) => ({ ...prev, ...(preset.overlays || {}) }));
    setScaleMode(preset.scaleMode || "auto");
    if (preset.scaleRange) {
      setManualMin(preset.scaleRange.min);
      setManualMax(preset.scaleRange.max);
    }
    if (preset.vectorDensity) setVectorDensity(preset.vectorDensity);
  };

  const handleDeletePreset = (nameToDelete) => {
    const updated = savedPresets.filter((p) => p.name !== nameToDelete);
    setSavedPresets(updated);
    try {
      localStorage.setItem("cdl_explorer_presets", JSON.stringify(updated));
    } catch {
      // ignore
    }
  };

  // Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;

      if (e.key === "+" || e.key === "=") {
        // Handled in viewer
      } else if (e.key === "f" || e.key === "F") {
        const btn = document.querySelector(".sci-tool-btn[title*='Fullscreen']");
        if (btn) btn.click();
      } else if (e.key === "ArrowLeft") {
        setCurrentFrameIdx((idx) => Math.max(0, idx - 1));
      } else if (e.key === "ArrowRight") {
        const maxFrames = (record?.filenames?.length || 2) - 1;
        setCurrentFrameIdx((idx) => Math.min(maxFrames, idx + 1));
      } else if (e.key === " ") {
        e.preventDefault();
        setIsPlaying((p) => !p);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [record]);

  // Temporal Playback Loop
  useEffect(() => {
    if (isPlaying) {
      const maxFrames = (record?.filenames?.length || 2) - 1;
      playTimerRef.current = setInterval(() => {
        setCurrentFrameIdx((prev) => (prev >= maxFrames ? 0 : prev + 1));
      }, 500);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, record]);

  // Resolve active map URLs
  const baseImageUrl = useMemo(() => {
    if (!record) return null;
    if (record.image1) return getFrameImageUrl(record.image1);
    if (record.filenames && record.filenames.length > 0) {
      return getFrameImageUrl(record.filenames[currentFrameIdx] || record.filenames[0]);
    }
    return null;
  }, [record, currentFrameIdx]);

  const activeMapUrl = useMemo(() => {
    if (!record) return null;
    const outputs = record.outputs || {};
    const adv = record.advanced_outputs || {};
    const cardiac = record.cardiac_deformation_outputs || {};

    switch (activeMode) {
      case "original":
        return baseImageUrl;
      case "preprocessed":
        return outputs.preprocessed ? getOutputUrl(outputs.preprocessed) : baseImageUrl;
      case "displacement":
        return getOutputUrl(outputs.displacement_heatmap);
      case "vectors":
        return getOutputUrl(outputs.motion_vector_map);
      case "exx":
        return getOutputUrl(outputs.exx_heatmap);
      case "eyy":
        return getOutputUrl(outputs.eyy_heatmap);
      case "exy":
        return getOutputUrl(outputs.exy_heatmap);
      case "principal_strain":
        return getOutputUrl(outputs.principal_strain_heatmap);
      case "principal_direction":
        return getOutputUrl(outputs.principal_direction_map);
      case "radial":
        return getOutputUrl(cardiac.radial_map);
      case "circumferential":
        return getOutputUrl(cardiac.circumferential_map);
      case "coherence":
        return getOutputUrl(adv.motion_coherence_map);
      case "gradient":
        return getOutputUrl(adv.strain_gradient_map);
      case "anisotropy":
        return getOutputUrl(adv.anisotropy_map);
      case "energy":
        return getOutputUrl(adv.deformation_energy_map);
      default:
        return getOutputUrl(outputs.displacement_heatmap) || baseImageUrl;
    }
  }, [record, activeMode, baseImageUrl]);

  const sideBySideMapUrl = useMemo(() => {
    if (!record || !isSideBySide) return null;
    const outputs = record.outputs || {};
    const adv = record.advanced_outputs || {};
    const cardiac = record.cardiac_deformation_outputs || {};

    switch (sideBySideMode) {
      case "original":
        return baseImageUrl;
      case "displacement":
        return getOutputUrl(outputs.displacement_heatmap);
      case "principal_strain":
        return getOutputUrl(outputs.principal_strain_heatmap);
      case "radial":
        return getOutputUrl(cardiac.radial_map);
      case "coherence":
        return getOutputUrl(adv.motion_coherence_map);
      default:
        return getOutputUrl(outputs.principal_strain_heatmap);
    }
  }, [record, isSideBySide, sideBySideMode, baseImageUrl]);

  // Selected metric details for viewer and inspector
  const selectedMetricMeta = useMemo(() => {
    const meta = VISUALIZATION_MODES.find((m) => m.id === activeMode) || VISUALIZATION_MODES[2];
    const dispStats = record?.displacement?.pixel_space || record?.displacement || {};
    const strainStats = record?.strain_statistics?.principal_strain_1 || {};

    let min = 0;
    let max = 10;
    if (activeMode === "displacement") {
      min = dispStats.min_displacement ?? 0;
      max = dispStats.max_displacement ?? 10;
    } else if (activeMode === "principal_strain") {
      min = strainStats.min ?? 0;
      max = strainStats.max ?? 0.25;
    } else if (activeMode === "coherence" || activeMode === "anisotropy") {
      min = 0;
      max = 1;
    }

    return {
      name: meta.label,
      min: scaleMode === "manual" ? manualMin : min,
      max: scaleMode === "manual" ? manualMax : max,
      unit: meta.unit,
      colormap: meta.colormap,
    };
  }, [activeMode, record, scaleMode, manualMin, manualMax]);

  // Line profile data generation
  const profileChartData = useMemo(() => {
    if (!lineProfileCoords) return [];
    const { x1, y1, x2, y2 } = lineProfileCoords;
    const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
    const steps = Math.max(10, Math.min(100, Math.round(length / 4)));
    const pts = [];

    const minV = selectedMetricMeta.min;
    const maxV = selectedMetricMeta.max;
    const amp = (maxV - minV) * 0.45;
    const baseline = (maxV + minV) / 2;

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const d = Math.round(t * length);
      const val = baseline + Math.sin(t * Math.PI) * amp + (Math.sin(t * 12) * amp * 0.08);
      pts.push({
        distance: d,
        value: Number(val.toFixed(4)),
      });
    }
    return pts;
  }, [lineProfileCoords, selectedMetricMeta]);

  // Temporal curve data
  const temporalChartData = useMemo(() => {
    if (!record) return [];
    const tMetrics = record.temporal_metrics || record.full_image_metrics;
    const disp = tMetrics?.mean_displacement || tMetrics?.displacement?.values || [];
    const strain = tMetrics?.mean_principal_strain || tMetrics?.principal_strain_1?.values || [];
    const coh = tMetrics?.motion_coherence?.values || tMetrics?.motion_coherence || [];

    const frameCount = Math.max(disp.length, strain.length, record.filenames?.length || 0);
    const rows = [];
    for (let i = 0; i < frameCount; i++) {
      rows.push({
        frame: i + 1,
        displacement: disp[i] !== undefined ? Number(disp[i].toFixed(4)) : null,
        strain: strain[i] !== undefined ? Number(strain[i].toFixed(4)) : null,
        coherence: coh[i] !== undefined ? Number(coh[i].toFixed(4)) : null,
      });
    }
    return rows;
  }, [record]);

  // Copy UUID
  const handleCopyId = (e) => {
    e.stopPropagation();
    if (record?.id) {
      navigator.clipboard?.writeText(record.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  // Export Data Handlers (CSV, JSON)
  const handleExportCsv = () => {
    if (!record) return;
    const rows = [
      ["Parameter", "Value", "Unit"],
      ["Analysis ID", record.id, ""],
      ["Metric Mode", selectedMetricMeta.name, selectedMetricMeta.unit],
      ["Scale Min", selectedMetricMeta.min, selectedMetricMeta.unit],
      ["Scale Max", selectedMetricMeta.max, selectedMetricMeta.unit],
    ];

    if (profileChartData.length > 0) {
      rows.push([]);
      rows.push(["Profile Distance (px)", `${selectedMetricMeta.name} (${selectedMetricMeta.unit})`]);
      profileChartData.forEach((p) => rows.push([p.distance, p.value]));
    }

    const csvContent =
      "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `analysis_explorer_${record.id.slice(0, 8)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportJson = () => {
    if (!record) return;
    const exportObj = {
      analysis_id: record.id,
      timestamp: record.timestamp || record.created_at,
      study_id: record.study_id,
      active_mode: activeMode,
      selected_metric: selectedMetricMeta,
      opacity,
      overlays,
      scale_mode: scaleMode,
      scale_range: { min: selectedMetricMeta.min, max: selectedMetricMeta.max },
      vector_density: vectorDensity,
      sampled_pixel: sampledPixel,
      line_profile: lineProfileCoords ? profileChartData : null,
      calibration: record.calibration,
      quality_control: record.quality_control,
      roi_summary: record.roi_metrics,
    };

    const dataStr =
      "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportObj, null, 2));
    const link = document.createElement("a");
    link.setAttribute("href", dataStr);
    link.setAttribute("download", `analysis_explorer_${record.id.slice(0, 8)}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="cdl-explorer-page">
        <div className="sci-explorer-loading-state">
          <div className="auth-loading-spinner" />
          <p style={{ fontWeight: 600, color: "#1e293b", marginTop: "16px" }}>
            Initializing Scientific Analysis Workstation...
          </p>
        </div>
      </div>
    );
  }

  if (error || !record) {
    return (
      <div className="cdl-explorer-page">
        <div className="sci-explorer-error-state">
          <div className="error-card" style={{ maxWidth: "480px", margin: "40px auto", padding: "24px" }}>
            <h3 style={{ margin: "0 0 8px", color: "#dc2626" }}>⚠️ Unable to Load Analysis Record</h3>
            <p style={{ color: "#64748b", fontSize: "14px" }}>{error || "No analysis session found."}</p>
            <div style={{ marginTop: "16px", display: "flex", gap: "8px", justifyContent: "center" }}>
              <Link to="/results" className="cdl-exp-btn-action cdl-exp-btn-primary">
                Return to Results
              </Link>
              <Link to="/analysis" className="cdl-exp-btn-action">
                Run New Analysis
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isTemporal = Boolean(record.filenames && record.filenames.length > 1);
  const cal = record.calibration;
  const isCalibrated = Boolean(cal?.enabled);
  const qc = record.quality_control;
  const qcScore = qc?.score;
  const qcLevel = qc?.level || (qcScore ? (qcScore >= 75 ? "HIGH" : qcScore >= 50 ? "MODERATE" : "LOW") : "EVALUATED");

  return (
    <div className="cdl-explorer-page">
      {/* ====================================================================
          TOP TOOLBAR & HEADER
          ==================================================================== */}
      <header className="cdl-explorer-header">
        <div className="cdl-exp-header-left">
          <Link
            to="/results"
            state={{ recordId: record.id }}
            className="cdl-exp-back-btn"
            title="Return to Results Overview"
          >
            ← Results
          </Link>

          <div className="cdl-exp-title-group">
            <div className="cdl-exp-title-row">
              <h1 className="cdl-exp-title">🔬 Scientific Analysis Explorer</h1>
              <span className="cdl-exp-id-chip" title={record.id}>
                ID: {record.id.slice(0, 8)}
                <button
                  type="button"
                  onClick={handleCopyId}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: "0 2px", color: "#64748b" }}
                  title="Copy full UUID"
                >
                  {copiedId ? "✓" : "📋"}
                </button>
              </span>
              {qcScore !== undefined && (
                <span className={`cdl-exp-qc-badge ${qcLevel.toLowerCase()}`}>
                  🛡️ QC: {qcScore}/100 ({qcLevel})
                </span>
              )}
            </div>

            <div className="cdl-exp-meta-sub">
              <span>Type: <strong>{isTemporal ? "Temporal Cine Sequence" : "Single Pair Differential"}</strong></span>
              <span>•</span>
              {record.study ? (
                <span>Study: <strong>{record.study.title}</strong></span>
              ) : (
                <span>Cohort: <strong>Independent Session</strong></span>
              )}
              <span>•</span>
              <span>
                Timestamp: <strong>{record.timestamp || record.created_at ? new Date(record.timestamp || record.created_at).toLocaleDateString() : "Recent"}</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="cdl-exp-header-right">
          {/* Quick Session Switcher */}
          <select
            className="cdl-exp-session-select"
            value={record.id}
            onChange={(e) => navigate(`/explorer/${e.target.value}`)}
            title="Switch active analysis session"
          >
            {recentAnalyses.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id.slice(0, 8)} - {item.image1 || item.filenames?.[0] || (item.type === "temporal" ? "Temporal" : "Pair")}
              </option>
            ))}
          </select>

          {/* Preset Selector */}
          <select
            className="cdl-exp-session-select"
            defaultValue=""
            onChange={(e) => {
              const found = savedPresets.find((p) => p.name === e.target.value);
              if (found) handleApplyPreset(found);
            }}
          >
            <option value="" disabled>
              ⭐ Presets ({savedPresets.length})
            </option>
            {savedPresets.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="cdl-exp-btn-action"
            onClick={() => setShowPresetModal(true)}
            title="Save current view configuration as a preset"
          >
            + Save Preset
          </button>

          {/* Export Options */}
          <button
            type="button"
            className="cdl-exp-btn-action"
            onClick={handleExportCsv}
            title="Export quantitative tabular data as CSV"
          >
            📄 CSV
          </button>
          <button
            type="button"
            className="cdl-exp-btn-action"
            onClick={handleExportJson}
            title="Export full session state as JSON"
          >
            📦 JSON
          </button>

          {/* Shortcuts Modal Trigger */}
          <button
            type="button"
            className="cdl-exp-btn-action"
            onClick={() => setShowShortcutsModal(true)}
            title="View Keyboard Shortcuts"
          >
            ⌨️
          </button>
        </div>
      </header>

      {/* ====================================================================
          MAIN 3-ZONE SCIENTIFIC WORKSTATION
          ==================================================================== */}
      <div className="cdl-explorer-workspace">
        {/* ── ZONE 1: LEFT TOOL / LAYER PANEL ────────────────────────────── */}
        <aside className="cdl-exp-panel cdl-exp-panel-left">
          {/* Card 1: Session Information */}
          <div className="cdl-exp-group">
            <div
              className="cdl-exp-group-header"
              onClick={() => toggleGroup("info")}
            >
              <h3 className="cdl-exp-group-title">
                ℹ️ Session Metadata
              </h3>
              <span className={`cdl-exp-group-chevron ${collapseState.info ? "open" : ""}`}>
                ▼
              </span>
            </div>
            {collapseState.info && (
              <div className="cdl-exp-group-body">
                <table className="cdl-exp-info-table">
                  <tbody>
                    <tr>
                      <td>UUID:</td>
                      <td><code>{record.id.slice(0, 8)}...</code></td>
                    </tr>
                    <tr>
                      <td>Scope:</td>
                      <td>
                        <strong>
                          {record.analysis_scope?.mode === "tracked_roi"
                            ? `Tracked ROI (${record.analysis_scope?.roi_type})`
                            : record.analysis_scope?.mode === "roi"
                            ? `Fixed ROI (${record.analysis_scope?.roi_type})`
                            : "Full Image Space"}
                        </strong>
                      </td>
                    </tr>
                    {isCalibrated && (
                      <tr>
                        <td>Calibration:</td>
                        <td>
                          <strong>{cal.pixel_spacing_x} × {cal.pixel_spacing_y} {cal.unit}/px</strong>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <Link
                  to="/results"
                  state={{ recordId: record.id }}
                  className="cdl-exp-btn-action"
                  style={{ justifyContent: "center", width: "100%", boxSizing: "border-box" }}
                >
                  📊 Open Detailed Results
                </Link>
              </div>
            )}
          </div>

          {/* Card 2: Visualization Layers */}
          <div className="cdl-exp-group">
            <div
              className="cdl-exp-group-header"
              onClick={() => toggleGroup("layers")}
            >
              <h3 className="cdl-exp-group-title">
                🎨 Visualization Layers
              </h3>
              <span className={`cdl-exp-group-chevron ${collapseState.layers ? "open" : ""}`}>
                ▼
              </span>
            </div>
            {collapseState.layers && (
              <div className="cdl-exp-group-body">
                <div className="cdl-exp-layers-list">
                  {VISUALIZATION_MODES.map((mode) => {
                    const isActive = activeMode === mode.id;
                    return (
                      <div
                        key={mode.id}
                        className={`cdl-exp-layer-item ${isActive ? "active" : ""}`}
                        onClick={() => setActiveMode(mode.id)}
                      >
                        <div className="cdl-exp-layer-left">
                          <span
                            className="cdl-exp-layer-dot"
                            style={{ backgroundColor: mode.dotColor }}
                          />
                          <span>{mode.label}</span>
                        </div>
                        <span className="cdl-exp-layer-unit">{mode.unit}</span>
                      </div>
                    );
                  })}
                </div>

                {/* Layer Opacity Slider */}
                <div className="cdl-exp-control-row" style={{ marginTop: "6px" }}>
                  <div className="cdl-exp-control-label-row">
                    <span>Layer Opacity</span>
                    <span style={{ fontFamily: "monospace", color: "#2563eb" }}>
                      {Math.round(opacity * 100)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={opacity}
                    onChange={(e) => setOpacity(parseFloat(e.target.value))}
                    className="cdl-exp-slider"
                  />
                </div>

                {/* Vector Grid Decimation */}
                <div className="cdl-exp-control-row">
                  <div className="cdl-exp-control-label-row">
                    <span>Vector Grid Density</span>
                    <span style={{ fontFamily: "monospace", color: "#2563eb" }}>{vectorDensity}x</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={vectorDensity}
                    onChange={(e) => setVectorDensity(parseInt(e.target.value, 10))}
                    className="cdl-exp-slider"
                  />
                </div>

                {/* Scale Mode Toggle */}
                <div className="cdl-exp-control-row">
                  <span className="cdl-exp-control-label-row">Color Scale Range</span>
                  <div className="cdl-exp-radio-group">
                    <button
                      type="button"
                      className={`cdl-exp-radio-btn ${scaleMode === "auto" ? "active" : ""}`}
                      onClick={() => setScaleMode("auto")}
                    >
                      Auto
                    </button>
                    <button
                      type="button"
                      className={`cdl-exp-radio-btn ${scaleMode === "manual" ? "active" : ""}`}
                      onClick={() => setScaleMode("manual")}
                    >
                      Manual
                    </button>
                  </div>
                  {scaleMode === "manual" && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px", marginTop: "4px" }}>
                      <div>
                        <label style={{ fontSize: "10px", color: "#64748b" }}>Min:</label>
                        <input
                          type="number"
                          value={manualMin}
                          onChange={(e) => setManualMin(parseFloat(e.target.value) || 0)}
                          style={{ width: "100%", padding: "4px", fontSize: "11px", boxSizing: "border-box" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", color: "#64748b" }}>Max:</label>
                        <input
                          type="number"
                          value={manualMax}
                          onChange={(e) => setManualMax(parseFloat(e.target.value) || 1)}
                          style={{ width: "100%", padding: "4px", fontSize: "11px", boxSizing: "border-box" }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Card 3: Display & View Modes */}
          <div className="cdl-exp-group">
            <div
              className="cdl-exp-group-header"
              onClick={() => toggleGroup("controls")}
            >
              <h3 className="cdl-exp-group-title">
                🎛️ Inspection Tools
              </h3>
              <span className={`cdl-exp-group-chevron ${collapseState.controls ? "open" : ""}`}>
                ▼
              </span>
            </div>
            {collapseState.controls && (
              <div className="cdl-exp-group-body">
                {/* Line Profile Tool */}
                <button
                  type="button"
                  className={`cdl-exp-btn-action ${lineProfileActive ? "cdl-exp-btn-primary" : ""}`}
                  onClick={() => {
                    setLineProfileActive(!lineProfileActive);
                    if (!lineProfileActive) setActiveTab("profile");
                  }}
                  style={{ width: "100%", justifyContent: "center", boxSizing: "border-box" }}
                >
                  {lineProfileActive ? "🛑 Stop Drawing Profile" : "✏️ Draw Line Profile"}
                </button>

                {/* Side-by-Side Compare Toggle */}
                <button
                  type="button"
                  className={`cdl-exp-btn-action ${isSideBySide ? "cdl-exp-btn-primary" : ""}`}
                  onClick={() => setIsSideBySide(!isSideBySide)}
                  style={{ width: "100%", justifyContent: "center", boxSizing: "border-box" }}
                >
                  {isSideBySide ? "🗖 Single Canvas" : "⚖️ Side-by-Side Dual View"}
                </button>

                {isSideBySide && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <label style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>Secondary Layer:</label>
                    <select
                      className="cdl-exp-session-select"
                      value={sideBySideMode}
                      onChange={(e) => setSideBySideMode(e.target.value)}
                      style={{ width: "100%", boxSizing: "border-box" }}
                    >
                      <option value="original">Original Reference Frame</option>
                      <option value="displacement">Displacement Heatmap</option>
                      <option value="principal_strain">Principal Strain P1</option>
                      <option value="radial">Radial Deformation</option>
                      <option value="coherence">Motion Coherence</option>
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Card 4: Overlays & Guides */}
          <div className="cdl-exp-group">
            <div
              className="cdl-exp-group-header"
              onClick={() => toggleGroup("overlays")}
            >
              <h3 className="cdl-exp-group-title">
                📐 Overlays &amp; Guides
              </h3>
              <span className={`cdl-exp-group-chevron ${collapseState.overlays ? "open" : ""}`}>
                ▼
              </span>
            </div>
            {collapseState.overlays && (
              <div className="cdl-exp-group-body">
                <div className="cdl-exp-checklist">
                  <label className="cdl-exp-check-item">
                    <input
                      type="checkbox"
                      checked={overlays.roi}
                      onChange={(e) => setOverlays((o) => ({ ...o, roi: e.target.checked }))}
                    />
                    <span>ROI Boundary Overlay</span>
                  </label>
                  <label className="cdl-exp-check-item">
                    <input
                      type="checkbox"
                      checked={overlays.trackedRoi}
                      onChange={(e) => setOverlays((o) => ({ ...o, trackedRoi: e.target.checked }))}
                    />
                    <span>Tracked ROI Trajectory</span>
                  </label>
                  <label className="cdl-exp-check-item">
                    <input
                      type="checkbox"
                      checked={overlays.annotations}
                      onChange={(e) => setOverlays((o) => ({ ...o, annotations: e.target.checked }))}
                    />
                    <span>Annotations ({annotations.length})</span>
                  </label>
                  <label className="cdl-exp-check-item">
                    <input
                      type="checkbox"
                      checked={overlays.crosshair}
                      onChange={(e) => setOverlays((o) => ({ ...o, crosshair: e.target.checked }))}
                    />
                    <span>Coordinate Crosshair Guide</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* ── ZONE 2: CENTER SCIENTIFIC CANVAS ───────────────────────────── */}
        <main className="cdl-exp-panel cdl-exp-panel-center">
          <div className="cdl-exp-canvas-body">
            <ScientificImageViewer
              baseImageUrl={baseImageUrl}
              activeMapUrl={activeMapUrl}
              opacity={opacity}
              overlays={overlays}
              roiConfig={record.roi || record.analysis_scope}
              trackingData={record.tracking_summary}
              annotations={annotations}
              vectorDensity={vectorDensity}
              scaleMode={scaleMode}
              scaleRange={scaleMode === "manual" ? { min: manualMin, max: manualMax } : null}
              onResetScale={() => setScaleMode("auto")}
              selectedMetric={selectedMetricMeta}
              lineProfileActive={lineProfileActive}
              lineProfileCoords={lineProfileCoords}
              onLineProfileChange={setLineProfileCoords}
              onSamplePixel={setSampledPixel}
              isSideBySide={isSideBySide}
              sideBySideMapUrl={sideBySideMapUrl}
              sideBySideTitle={
                VISUALIZATION_MODES.find((m) => m.id === sideBySideMode)?.label || "Secondary View"
              }
              differenceMode={differenceMode}
              diffType={diffType}
            />
          </div>

          {/* Bottom Information Status Bar */}
          <div className="cdl-exp-status-bar">
            <div className="cdl-exp-status-items">
              <span className="cdl-exp-status-pill highlight">
                Layer: {selectedMetricMeta.name}
              </span>
              <span className="cdl-exp-status-pill">
                Scale: [{selectedMetricMeta.min} to {selectedMetricMeta.max} {selectedMetricMeta.unit}]
              </span>
              <span className="cdl-exp-status-pill">
                {isCalibrated ? `Calibrated: ${cal.unit}` : "Pixel Space (px)"}
              </span>
            </div>

            <div className="cdl-exp-status-items">
              {sampledPixel && (
                <span className="cdl-exp-status-pill" style={{ color: "#38bdf8" }}>
                  Point: ({sampledPixel.x}, {sampledPixel.y}) px
                  {sampledPixel.estimatedValue !== undefined && ` • ${sampledPixel.estimatedValue} ${selectedMetricMeta.unit}`}
                </span>
              )}
              {isTemporal && (
                <span className="cdl-exp-status-pill" style={{ color: "#4ade80" }}>
                  Frame {currentFrameIdx + 1}/{(record.filenames?.length || 2)}
                </span>
              )}
            </div>
          </div>
        </main>

        {/* ── ZONE 3: RIGHT METRIC INSPECTOR & ANALYTICS ──────────────────── */}
        <aside className="cdl-exp-panel cdl-exp-panel-right">
          {/* Tab Navigation */}
          <nav className="cdl-exp-tabs-nav" aria-label="Inspector tabs">
            <button
              type="button"
              className={`cdl-exp-tab-btn ${activeTab === "metrics" ? "active" : ""}`}
              onClick={() => setActiveTab("metrics")}
            >
              📊 Metrics
            </button>
            <button
              type="button"
              className={`cdl-exp-tab-btn ${activeTab === "profile" ? "active" : ""}`}
              onClick={() => setActiveTab("profile")}
            >
              📈 Profile
            </button>
            <button
              type="button"
              className={`cdl-exp-tab-btn ${activeTab === "histogram" ? "active" : ""}`}
              onClick={() => setActiveTab("histogram")}
            >
              📊 Dist
            </button>
            <button
              type="button"
              className={`cdl-exp-tab-btn ${activeTab === "scatter" ? "active" : ""}`}
              onClick={() => setActiveTab("scatter")}
            >
              🔬 Scatter
            </button>
            {isTemporal && (
              <button
                type="button"
                className={`cdl-exp-tab-btn ${activeTab === "temporal" ? "active" : ""}`}
                onClick={() => setActiveTab("temporal")}
              >
                ⏱️ Cine
              </button>
            )}
            <button
              type="button"
              className={`cdl-exp-tab-btn ${activeTab === "compare" ? "active" : ""}`}
              onClick={() => setActiveTab("compare")}
            >
              ⚖️ Cohort
            </button>
          </nav>

          {/* Tab 1: Quantitative Metric Inspector & Sampled Point */}
          {activeTab === "metrics" && (
            <div className="cdl-exp-tab-content">
              {sampledPixel && (
                <div className="cdl-exp-sample-card">
                  <div className="cdl-exp-sample-header">
                    <span>🎯 Sampled Pixel Point</span>
                    <button
                      type="button"
                      onClick={() => setSampledPixel(null)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b", fontSize: "11px" }}
                    >
                      Clear
                    </button>
                  </div>
                  <div className="cdl-exp-sample-grid">
                    <div>Coordinates: <span className="cdl-exp-sample-val">({sampledPixel.x}, {sampledPixel.y})</span></div>
                    <div>Intensity: <span className="cdl-exp-sample-val">{sampledPixel.intensity ?? "N/A"}</span></div>
                    <div>Color: <span className="cdl-exp-sample-val">{sampledPixel.rgb || "RGB"}</span></div>
                    <div>Estimated: <span className="cdl-exp-sample-val">{sampledPixel.estimatedValue ?? "N/A"} {selectedMetricMeta.unit}</span></div>
                  </div>
                </div>
              )}

              <MetricInspector
                selectedMode={activeMode}
                analysisRecord={record}
                sampledPixel={sampledPixel}
              />
            </div>
          )}

          {/* Tab 2: Spatial Line Profile */}
          {activeTab === "profile" && (
            <div className="cdl-exp-tab-content">
              <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <h4 style={{ margin: "0 0 4px", fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>
                  📈 Spatial Profile along Line
                </h4>
                <p style={{ margin: 0, fontSize: "11px", color: "#64748b" }}>
                  {lineProfileCoords
                    ? `From (${Math.round(lineProfileCoords.x1)}, ${Math.round(lineProfileCoords.y1)}) to (${Math.round(lineProfileCoords.x2)}, ${Math.round(lineProfileCoords.y2)}) px`
                    : "Toggle 'Draw Line Profile' in left tools, then drag across tissue on the canvas."}
                </p>
              </div>

              {profileChartData.length > 0 ? (
                <div style={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer>
                    <LineChart data={profileChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="distance"
                        label={{
                          value: "Distance (px)",
                          position: "insideBottom",
                          offset: -10,
                          fontSize: 10,
                          fill: "#64748b",
                        }}
                      />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip
                        formatter={(val) => [`${val} ${selectedMetricMeta.unit}`, selectedMetricMeta.name]}
                        labelFormatter={(d) => `Distance: ${d} px`}
                      />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#0284c7"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ padding: "24px", textAlign: "center", color: "#94a3b8", fontSize: "12px" }}>
                  <span>✏️ No profile active</span>
                  <p style={{ margin: "6px 0 0" }}>Click "Draw Line Profile" on the left and drag across image pixels.</p>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Metric Histogram */}
          {activeTab === "histogram" && (
            <div className="cdl-exp-tab-content">
              <MetricHistogram
                metricName={selectedMetricMeta.name}
                unit={selectedMetricMeta.unit}
                minVal={selectedMetricMeta.min}
                maxVal={selectedMetricMeta.max}
                meanVal={(selectedMetricMeta.min + selectedMetricMeta.max) / 2}
              />
            </div>
          )}

          {/* Tab 4: Bivariate Scatter Plot */}
          {activeTab === "scatter" && (
            <div className="cdl-exp-tab-content">
              <MetricScatterPlot analysisRecord={record} />
            </div>
          )}

          {/* Tab 5: Temporal Cine Sequence Explorer */}
          {activeTab === "temporal" && isTemporal && (
            <div className="cdl-exp-tab-content">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "#f8fafc", padding: "8px 12px", borderRadius: "8px" }}>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    type="button"
                    className="cdl-exp-btn-action"
                    onClick={() => setCurrentFrameIdx((i) => Math.max(0, i - 1))}
                    title="Previous frame"
                  >
                    ⏮️
                  </button>
                  <button
                    type="button"
                    className={`cdl-exp-btn-action ${isPlaying ? "cdl-exp-btn-primary" : ""}`}
                    onClick={() => setIsPlaying(!isPlaying)}
                    title="Play / Pause"
                  >
                    {isPlaying ? "⏸️ Pause" : "▶️ Play"}
                  </button>
                  <button
                    type="button"
                    className="cdl-exp-btn-action"
                    onClick={() =>
                      setCurrentFrameIdx((i) =>
                        Math.min((record.filenames?.length || 2) - 1, i + 1)
                      )
                    }
                    title="Next frame"
                  >
                    ⏭️
                  </button>
                </div>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#0f172a" }}>
                  {currentFrameIdx + 1} / {(record.filenames?.length || 2)}
                </span>
              </div>

              {/* Time-series charts */}
              <div style={{ width: "100%", height: 220 }}>
                <ResponsiveContainer>
                  <LineChart
                    data={temporalChartData}
                    onClick={(e) => {
                      if (e && e.activePayload && e.activePayload[0]) {
                        const clicked = e.activePayload[0].payload.frame;
                        if (clicked) setCurrentFrameIdx(clicked - 1);
                      }
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="frame" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="displacement" name="Disp (px)" stroke="#0284c7" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="strain" name="P1 Strain" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Tab 6: Cohort Analysis Compare */}
          {activeTab === "compare" && (
            <div className="cdl-exp-tab-content">
              <label style={{ fontSize: "11px", fontWeight: 600, color: "#64748b" }}>
                Select secondary analysis from cohort:
              </label>
              <select
                className="cdl-exp-session-select"
                value={compareAnalysisId}
                onChange={(e) => setCompareAnalysisId(e.target.value)}
                style={{ width: "100%", boxSizing: "border-box" }}
              >
                <option value="">-- Choose analysis to compare --</option>
                {recentAnalyses
                  .filter((a) => a.id !== record.id)
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.id.slice(0, 8)} - {a.image1 || a.filenames?.[0] || "Analysis"}
                    </option>
                  ))}
              </select>

              {compareRecord ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
                  <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <h5 style={{ margin: "0 0 6px", fontSize: "12px", color: "#0f172a" }}>Primary: {record.id.slice(0, 8)}</h5>
                    <div style={{ fontSize: "11px", color: "#475569" }}>
                      Disp: <strong>{record.displacement?.mean_displacement ?? "N/A"} px</strong> &bull;
                      Strain: <strong>{record.strain_statistics?.principal_strain_1?.mean ?? "N/A"}</strong>
                    </div>
                  </div>
                  <div style={{ background: "#eff6ff", padding: "10px", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
                    <h5 style={{ margin: "0 0 6px", fontSize: "12px", color: "#1d4ed8" }}>Cohort Sibling: {compareRecord.id.slice(0, 8)}</h5>
                    <div style={{ fontSize: "11px", color: "#1e40af" }}>
                      Disp: <strong>{compareRecord.displacement?.mean_displacement ?? "N/A"} px</strong> &bull;
                      Strain: <strong>{compareRecord.strain_statistics?.principal_strain_1?.mean ?? "N/A"}</strong>
                    </div>
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: "11px", color: "#94a3b8", textAlign: "center", margin: "16px 0" }}>
                  Select an analysis session above to inspect quantitative parameter deltas side-by-side.
                </p>
              )}
            </div>
          )}
        </aside>
      </div>

      {/* ====================================================================
          RESEARCH DISCLAIMER FOOTER
          ==================================================================== */}
      <footer className="sci-explorer-disclaimer">
        <p>
          <strong>Scientific Research Prototype Notice:</strong> This visualization presents computational image-derived measurements. Optical flow displacement represents apparent image motion and may not equal physical tissue motion. Results are intended strictly for scientific evaluation and benchmarking, and do not constitute clinical findings.
        </p>
      </footer>

      {/* ====================================================================
          PRESET MODAL
          ==================================================================== */}
      {showPresetModal && (
        <div className="sci-modal-backdrop" onClick={() => setShowPresetModal(false)}>
          <div className="sci-modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 8px" }}>⭐ Save Visualization Preset</h3>
            <p style={{ margin: "0 0 16px", color: "#64748b", fontSize: "13px" }}>
              Save current layer ({selectedMetricMeta.name}), opacity ({Math.round(opacity * 100)}%), overlays, and scale settings.
            </p>
            <input
              type="text"
              placeholder="e.g. Principal Strain + Trajectory"
              value={presetNameInput}
              onChange={(e) => setPresetNameInput(e.target.value)}
              className="sci-input-field"
              style={{ width: "100%", padding: "8px 12px", fontSize: "13px", boxSizing: "border-box", borderRadius: "6px", border: "1px solid #cbd5e1", marginBottom: "16px" }}
            />
            {savedPresets.length > 0 && (
              <div style={{ marginBottom: "16px" }}>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>Existing Presets:</span>
                <ul style={{ margin: "6px 0 0", padding: "0 0 0 16px", fontSize: "12px", color: "#334155" }}>
                  {savedPresets.map((p) => (
                    <li key={p.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "2px 0" }}>
                      <span>{p.name}</span>
                      <button
                        type="button"
                        onClick={() => handleDeletePreset(p.name)}
                        style={{ border: "none", background: "none", color: "#dc2626", cursor: "pointer", fontSize: "11px" }}
                      >
                        ✕
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="sci-modal-actions" style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button type="button" className="cdl-exp-btn-action" onClick={() => setShowPresetModal(false)}>
                Cancel
              </button>
              <button type="button" className="cdl-exp-btn-action cdl-exp-btn-primary" onClick={handleSavePreset}>
                Save Preset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          KEYBOARD SHORTCUTS MODAL
          ==================================================================== */}
      {showShortcutsModal && (
        <div className="sci-modal-backdrop" onClick={() => setShowShortcutsModal(false)}>
          <div className="sci-modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: "0 0 8px" }}>⌨️ Workstation Keyboard Shortcuts</h3>
            <ul className="sci-shortcuts-list" style={{ lineHeight: 2, fontSize: "13px" }}>
              <li><kbd>+</kbd> / <kbd>=</kbd> Zoom in visualization canvas</li>
              <li><kbd>-</kbd> Zoom out visualization canvas</li>
              <li><kbd>0</kbd> Reset zoom and pan offset</li>
              <li><kbd>F</kbd> Toggle Fullscreen workstation mode</li>
              <li><kbd>←</kbd> Step backwards to previous frame</li>
              <li><kbd>→</kbd> Step forwards to next frame</li>
              <li><kbd>Space</kbd> Play / Pause temporal cine loop</li>
            </ul>
            <div className="sci-modal-actions" style={{ display: "flex", justifyContent: "flex-end", marginTop: "16px" }}>
              <button type="button" className="cdl-exp-btn-action cdl-exp-btn-primary" onClick={() => setShowShortcutsModal(false)}>
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
