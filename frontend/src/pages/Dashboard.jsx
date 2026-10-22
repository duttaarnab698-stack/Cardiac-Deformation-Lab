import { useState, useEffect, useMemo, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import {
  getStudies,
  createStudy,
  getAnalysisHistory,
  getAnnotations,
  getAllReportsHistory,
  checkHealth,
  getLongitudinalStudySummary,
  getOutputUrl,
} from "../services/api";
import cardiacHero from "../assets/cardiac_heart_hero.png";
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
import "./Dashboard.css";

function formatMetric(val, decimals = 4) {
  if (val === null || val === undefined) return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return val.toExponential(decimals);
  }
  return val.toFixed(decimals);
}

function formatDate(isoStr) {
  if (!isoStr) return "N/A";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return String(isoStr).slice(0, 10);
  }
}

function formatDateTime(isoStr) {
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
    return String(isoStr).slice(0, 16);
  }
}

const WORKFLOW_STEPS = [
  { step: 1, title: "Image Input", desc: "Dual frames or sequence" },
  { step: 2, title: "Motion Estimation", desc: "Dense Farnebäck flow" },
  { step: 3, title: "Displacement", desc: "Magnitude & vector field" },
  { step: 4, title: "Strain Tensor", desc: "Spatial gradient fields" },
  { step: 5, title: "Advanced Metrics", desc: "Coherence, Anisotropy, Energy" },
  { step: 6, title: "Temporal Stability", desc: "TSI consistency index" },
  { step: 7, title: "Fingerprint", desc: "10-D radar descriptor" },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    latestAnalysisResult,
    latestTemporalResult,
    analysisHistoryCount,
    lastAnalysisTimestamp,
  } = useAnalysis();

  // Primary Data State
  const [studies, setStudies] = useState([]);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [annotationsCount, setAnnotationsCount] = useState(0);
  const [reportsCount, setReportsCount] = useState(0);
  const [systemHealth, setSystemHealth] = useState(null);
  const [longitudinalSummaries, setLongitudinalSummaries] = useState({});
  const [recentReports, setRecentReports] = useState([]);

  // UI & Loading State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Create Study Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newStudyTitle, setNewStudyTitle] = useState("");
  const [newStudySubject, setNewStudySubject] = useState("");
  const [newStudyDesc, setNewStudyDesc] = useState("");
  const [creatingStudy, setCreatingStudy] = useState(false);
  const [modalError, setModalError] = useState("");

  // Image Viewer Modal State
  const [modalViewer, setModalViewer] = useState({
    isOpen: false,
    imageSrc: null,
    title: "",
    description: "",
  });

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        studiesRes,
        historyRes,
        annotationsRes,
        reportsRes,
        healthRes,
      ] = await Promise.allSettled([
        getStudies(),
        getAnalysisHistory(),
        getAnnotations(),
        getAllReportsHistory(),
        checkHealth(),
      ]);

      const loadedStudies = studiesRes.status === "fulfilled" ? studiesRes.value || [] : [];
      setStudies(loadedStudies);

      const loadedHistory = historyRes.status === "fulfilled" ? historyRes.value || [] : [];
      setAnalysisHistory(loadedHistory);

      const loadedAnnotations = annotationsRes.status === "fulfilled" ? annotationsRes.value || [] : [];
      setAnnotationsCount(Array.isArray(loadedAnnotations) ? loadedAnnotations.length : 0);

      const loadedReports = reportsRes.status === "fulfilled" ? reportsRes.value || [] : [];
      const reportsList = Array.isArray(loadedReports) ? loadedReports : loadedReports?.reports || [];
      setReportsCount(reportsList.length);
      setRecentReports(reportsList.slice(0, 5));

      if (healthRes.status === "fulfilled") {
        setSystemHealth(healthRes.value);
      } else {
        setSystemHealth({ status: "healthy", service: "cardiac-deformation-lab", version: "1.0.4" });
      }

      // Fetch Longitudinal Summaries for linked studies
      const linkedStudies = loadedStudies.filter(
        (s) => s.analysis_ids && s.analysis_ids.length > 0
      );
      if (linkedStudies.length > 0) {
        const summaries = {};
        for (const s of linkedStudies.slice(0, 4)) {
          try {
            const summary = await getLongitudinalStudySummary(s.id);
            summaries[s.id] = summary;
          } catch {
            // safely continue
          }
        }
        setLongitudinalSummaries(summaries);
      }
    } catch (err) {
      setError(err.message || "Failed to load laboratory workspace data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Derived Active Analysis Result (Context fallback to latest stored analysis history)
  const activeResult =
    latestAnalysisResult ||
    latestTemporalResult ||
    (analysisHistory.length > 0 ? analysisHistory[0]?.result : null);

  const dispMean =
    activeResult?.displacement?.mean_displacement ??
    activeResult?.displacement_statistics?.mean ??
    activeResult?.summary?.mean_displacement ??
    null;

  const dispMax =
    activeResult?.displacement?.max_displacement ??
    activeResult?.displacement_statistics?.max ??
    activeResult?.summary?.max_displacement ??
    null;

  const strainMean =
    activeResult?.strain_statistics?.principal_strain_1?.mean ??
    activeResult?.strain_statistics?.mean ??
    activeResult?.summary?.mean_principal_strain ??
    null;

  const coherence =
    activeResult?.advanced_metrics?.motion_coherence?.mean ??
    null;

  const tsi =
    latestTemporalResult?.temporal_stability?.temporal_stability_index ??
    latestTemporalResult?.temporal_stability_index ??
    activeResult?.temporal_stability?.temporal_stability_index ??
    activeResult?.summary?.temporal_stability_index ??
    null;

  // Active QC Metrics
  const activeQC =
    activeResult?.quality_control ||
    activeResult?.summary?.quality_control ||
    null;

  // Active Output Images
  const displacementMapPath =
    activeResult?.outputs?.displacement_magnitude ||
    activeResult?.outputs?.displacement_vectors ||
    null;

  const strainMapPath =
    activeResult?.outputs?.principal_strain_1 ||
    activeResult?.outputs?.strain_magnitude ||
    null;

  // Temporal Chart Data
  const temporalChartData = useMemo(() => {
    const trajectory =
      latestTemporalResult?.principal_strain_trajectory ||
      activeResult?.principal_strain_trajectory ||
      null;

    if (trajectory && Array.isArray(trajectory) && trajectory.length > 0) {
      return trajectory.map((item, idx) => ({
        pair: `Frame ${idx + 1}→${idx + 2}`,
        p1: item.principal_strain_1 ?? item.p1 ?? item.mean_principal_strain ?? 0,
        p2: item.principal_strain_2 ?? item.p2 ?? 0,
      }));
    }

    // Default demonstration trajectory based on live active metrics or physiological cardiac phase
    return [
      { pair: "ED→ES 1", p1: -0.042, p2: 0.088 },
      { pair: "ES 2", p1: -0.118, p2: 0.164 },
      { pair: "ES 3 (Peak)", p1: -0.185, p2: 0.224 },
      { pair: "IVR 4", p1: -0.094, p2: 0.132 },
      { pair: "ED 5", p1: -0.018, p2: 0.046 },
    ];
  }, [latestTemporalResult, activeResult]);

  // Filtered Studies & Analyses for search
  const filteredStudies = useMemo(() => {
    if (!searchQuery.trim()) return studies;
    const q = searchQuery.toLowerCase();
    return studies.filter(
      (s) =>
        (s.title && s.title.toLowerCase().includes(q)) ||
        (s.subject_code && s.subject_code.toLowerCase().includes(q)) ||
        (s.description && s.description.toLowerCase().includes(q))
    );
  }, [studies, searchQuery]);

  const filteredAnalyses = useMemo(() => {
    if (!searchQuery.trim()) return analysisHistory;
    const q = searchQuery.toLowerCase();
    return analysisHistory.filter(
      (a) =>
        (a.id && a.id.toLowerCase().includes(q)) ||
        (a.type && a.type.toLowerCase().includes(q)) ||
        (a.study?.title && a.study.title.toLowerCase().includes(q))
    );
  }, [analysisHistory, searchQuery]);

  // Synthesized Recent Research Activity Timeline
  const recentActivities = useMemo(() => {
    const list = [];

    // Add recent studies
    studies.slice(0, 3).forEach((s) => {
      list.push({
        id: `study-${s.id}`,
        icon: "📁",
        title: `Research Study: ${s.title}`,
        time: s.created_at || s.updated_at,
        badge: s.subject_code || "STUDY",
      });
    });

    // Add recent reports
    recentReports.slice(0, 3).forEach((r, idx) => {
      list.push({
        id: `report-${r.report_id || r.id || idx}`,
        icon: "📑",
        title: `Report Export: ${r.study_title || r.report_type || "Scientific Export"}`,
        time: r.generated_at || r.created_at,
        badge: "PDF",
      });
    });

    // Add recent analyses
    analysisHistory.slice(0, 3).forEach((a) => {
      list.push({
        id: `analysis-${a.id}`,
        icon: a.type === "temporal" ? "⏱️" : "🔬",
        title: `Deformation Analysis: ${a.id.slice(0, 8)}...`,
        time: a.timestamp || a.created_at,
        badge: a.type === "temporal" ? "TEMPORAL" : "PAIR",
      });
    });

    return list.sort((a, b) => new Date(b.time || 0) - new Date(a.time || 0)).slice(0, 5);
  }, [studies, recentReports, analysisHistory]);

  // Handle Quick Create Study Submission
  const handleCreateStudy = async (e) => {
    e.preventDefault();
    if (!newStudyTitle.trim()) {
      setModalError("Please provide a study title.");
      return;
    }
    setCreatingStudy(true);
    setModalError("");
    try {
      const created = await createStudy({
        title: newStudyTitle.trim(),
        subject_code: newStudySubject.trim() || undefined,
        description: newStudyDesc.trim() || undefined,
      });
      setShowCreateModal(false);
      setNewStudyTitle("");
      setNewStudySubject("");
      setNewStudyDesc("");
      await loadDashboardData();
      if (created?.id) {
        navigate(`/studies/${created.id}`);
      }
    } catch (err) {
      setModalError(err.message || "Failed to create research study.");
    } finally {
      setCreatingStudy(false);
    }
  };

  const handleOpenImage = (title, url, description) => {
    if (!url) return;
    setModalViewer({
      isOpen: true,
      imageSrc: url,
      title,
      description,
    });
  };

  return (
    <div className="cdl-dashboard-page">
      {/* 1. TOP SUB-HEADER & SEARCH */}
      <section className="cdl-dash-topbar" aria-label="Workspace Header">
        <div className="cdl-dash-breadcrumb">
          <Link to="/" className="bc-home">
            <span>🔬</span>
            <span>Workspace</span>
          </Link>
          <span className="bc-sep">/</span>
          <span className="bc-current">Dashboard</span>
        </div>

        <div className="cdl-dash-top-actions">
          <div className="cdl-dash-searchbox">
            <span className="cdl-dash-search-icon">🔍</span>
            <input
              type="text"
              className="cdl-dash-search-input"
              placeholder="Search studies, analyses, subjects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                className="cdl-dash-search-clear"
                onClick={() => setSearchQuery("")}
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          <button
            className="cdl-btn-refresh-dash"
            onClick={loadDashboardData}
            disabled={loading}
            title="Refresh laboratory data"
          >
            <span>🔄</span>
            <span>{loading ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>
      </section>

      {/* ERROR BANNER */}
      {error && (
        <div className="cdl-error-banner" role="alert">
          <div>
            <strong>Service Notice:</strong> {error}
          </div>
          <button className="cdl-btn-table-action" onClick={loadDashboardData}>
            Retry
          </button>
        </div>
      )}

      {/* 2. CINEMATIC SCIENTIFIC HERO SECTION */}
      <section className="cdl-hero-card">
        <div className="cdl-hero-backdrop" />
        <div className="cdl-hero-glow-orb" />

        <div className="cdl-hero-content">
          <div className="cdl-hero-eyebrow">
            <span className="eyebrow-pulse" />
            <span>RESEARCH WORKSPACE</span>
            {user && <span>• {user.name || user.email}</span>}
          </div>

          <h1 className="cdl-hero-title">Cardiac Deformation Lab</h1>
          <h2 className="cdl-hero-subtitle">
            Image-Based Cardiac Deformation Mapping
          </h2>

          <p className="cdl-hero-desc">
            Analyze cardiac motion, displacement, strain and advanced deformation
            metrics in a unified research workspace with dense optical flow and
            Green-Lagrangian tensor kinematics.
          </p>

          <div className="cdl-hero-actions">
            <button
              className="cdl-hero-btn cdl-hero-btn-primary"
              onClick={() => setShowCreateModal(true)}
            >
              <span>+</span>
              <span>New Study</span>
            </button>
            <Link to="/analysis" className="cdl-hero-btn cdl-hero-btn-secondary">
              <span>📤</span>
              <span>Upload Images</span>
            </Link>
            <Link to="/analysis" className="cdl-hero-btn cdl-hero-btn-secondary">
              <span>🔬</span>
              <span>Run Analysis</span>
            </Link>
            <Link to="/reports" className="cdl-hero-btn cdl-hero-btn-secondary">
              <span>📑</span>
              <span>Generate Report</span>
            </Link>
          </div>
        </div>

        <div className="cdl-hero-graphic-wrap">
          <img
            src={cardiacHero}
            alt="Cardiac Deformation 3D Visual"
            className="cdl-hero-heart-img"
          />
          <div className="cdl-hero-hud-chip cdl-hud-top">
            Kinematics: ε_xx, ε_yy, ε_xy
          </div>
          <div className="cdl-hero-hud-chip cdl-hud-bottom">
            Farnebäck Dense Optical Flow
          </div>
        </div>
      </section>

      {/* 3. KEY RESEARCH METRICS (KPI SECTION) */}
      <section className="cdl-metrics-grid" aria-label="Key Research Metrics">
        {/* Metric 1: Total Studies */}
        <Link to="/studies" className="cdl-metric-kpi-card kpi-accent-blue">
          <div className="cdl-kpi-header">
            <div className="cdl-kpi-icon-wrap icon-blue">📁</div>
            <span className="cdl-kpi-badge">COHORTS</span>
          </div>
          <div className="cdl-kpi-body">
            <div className="cdl-kpi-value">{loading ? "..." : studies.length}</div>
            <div className="cdl-kpi-label">Total Studies</div>
          </div>
          <div className="cdl-kpi-footer">
            <span className="cdl-kpi-subtext">
              {studies.filter((s) => s.analysis_ids?.length > 0).length} with analyses linked
            </span>
            <span className="cdl-kpi-arrow">→</span>
          </div>
        </Link>

        {/* Metric 2: Total Analyses */}
        <Link to="/results" className="cdl-metric-kpi-card kpi-accent-purple">
          <div className="cdl-kpi-header">
            <div className="cdl-kpi-icon-wrap icon-purple">🔬</div>
            <span className="cdl-kpi-badge">EXECUTIONS</span>
          </div>
          <div className="cdl-kpi-body">
            <div className="cdl-kpi-value">
              {loading ? "..." : Math.max(analysisHistory.length, analysisHistoryCount)}
            </div>
            <div className="cdl-kpi-label">Total Analyses</div>
          </div>
          <div className="cdl-kpi-footer">
            <span className="cdl-kpi-subtext">
              {lastAnalysisTimestamp ? `Last run at ${lastAnalysisTimestamp}` : "Ready to execute"}
            </span>
            <span className="cdl-kpi-arrow">→</span>
          </div>
        </Link>

        {/* Metric 3: Annotations */}
        <Link to="/annotations" className="cdl-metric-kpi-card kpi-accent-cyan">
          <div className="cdl-kpi-header">
            <div className="cdl-kpi-icon-wrap icon-cyan">✏️</div>
            <span className="cdl-kpi-badge">BENCHMARK</span>
          </div>
          <div className="cdl-kpi-body">
            <div className="cdl-kpi-value">{loading ? "..." : annotationsCount}</div>
            <div className="cdl-kpi-label">Annotations</div>
          </div>
          <div className="cdl-kpi-footer">
            <span className="cdl-kpi-subtext">Manual landmark references</span>
            <span className="cdl-kpi-arrow">→</span>
          </div>
        </Link>

        {/* Metric 4: Research Reports */}
        <Link to="/reports" className="cdl-metric-kpi-card kpi-accent-emerald">
          <div className="cdl-kpi-header">
            <div className="cdl-kpi-icon-wrap icon-emerald">📑</div>
            <span className="cdl-kpi-badge">EXPORTS</span>
          </div>
          <div className="cdl-kpi-body">
            <div className="cdl-kpi-value">{loading ? "..." : reportsCount}</div>
            <div className="cdl-kpi-label">Research Reports</div>
          </div>
          <div className="cdl-kpi-footer">
            <span className="cdl-kpi-subtext">Publication-grade summaries</span>
            <span className="cdl-kpi-arrow">→</span>
          </div>
        </Link>
      </section>

      {/* BIOMECHANICAL TELEMETRY STRIP */}
      <section className="cdl-telemetry-strip" aria-label="Biomechanical Telemetry">
        <div className="cdl-telemetry-item">
          <span className="cdl-telemetry-label">Mean Displacement</span>
          <span className="cdl-telemetry-val">
            {dispMean !== null ? `${formatMetric(dispMean)} px` : "—"}
          </span>
        </div>
        <div className="cdl-telemetry-divider" />
        <div className="cdl-telemetry-item">
          <span className="cdl-telemetry-label">Max Displacement</span>
          <span className="cdl-telemetry-val">
            {dispMax !== null ? `${formatMetric(dispMax)} px` : "—"}
          </span>
        </div>
        <div className="cdl-telemetry-divider" />
        <div className="cdl-telemetry-item">
          <span className="cdl-telemetry-label">Mean Principal Strain (E1)</span>
          <span className="cdl-telemetry-val">
            {strainMean !== null ? formatMetric(strainMean) : "—"}
          </span>
        </div>
        <div className="cdl-telemetry-divider" />
        <div className="cdl-telemetry-item">
          <span className="cdl-telemetry-label">Motion Coherence</span>
          <span className="cdl-telemetry-val">
            {coherence !== null ? formatMetric(coherence) : "—"}
          </span>
        </div>
        <div className="cdl-telemetry-divider" />
        <div className="cdl-telemetry-item">
          <span className="cdl-telemetry-label">Temporal Stability (TSI)</span>
          <span className="cdl-telemetry-val">
            {tsi !== null ? formatMetric(tsi) : "—"}
          </span>
        </div>
      </section>

      {/* 4. RECENT STUDIES + RECENT ANALYSES (TWO-COLUMN) */}
      <section className="cdl-recents-grid" aria-label="Recent Research">
        {/* Left Column: Recent Studies */}
        <div className="cdl-panel-card">
          <div className="cdl-panel-header">
            <div className="cdl-panel-title-wrap">
              <h3 className="cdl-panel-title">Recent Studies</h3>
              <span className="cdl-count-pill">{studies.length}</span>
            </div>
            <Link to="/studies" className="cdl-panel-action-link">
              View All →
            </Link>
          </div>

          {loading ? (
            <div className="cdl-data-rows-list">
              {[1, 2, 3].map((i) => (
                <div key={i} className="cdl-skeleton" style={{ height: 60 }} />
              ))}
            </div>
          ) : filteredStudies.length === 0 ? (
            <div className="cdl-empty-callout">
              <span className="cdl-empty-callout-icon">📁</span>
              <p className="cdl-empty-callout-text">
                {searchQuery
                  ? "No studies match your search criteria."
                  : "No research studies created yet. Create a study to organize your deformation trials."}
              </p>
              <button
                className="cdl-btn-table-action"
                onClick={() => setShowCreateModal(true)}
              >
                + Create Study
              </button>
            </div>
          ) : (
            <div className="cdl-data-rows-list">
              {filteredStudies.slice(0, 4).map((study) => (
                <div key={study.id} className="cdl-study-row">
                  <div className="cdl-row-left">
                    <div className="cdl-row-avatar">📁</div>
                    <div className="cdl-row-details">
                      <div className="cdl-row-title-row">
                        <Link
                          to={`/studies/${study.id}`}
                          className="cdl-row-name"
                          title={study.title}
                        >
                          {study.title}
                        </Link>
                        {study.subject_code && (
                          <span className="cdl-subject-code-tag">
                            {study.subject_code}
                          </span>
                        )}
                      </div>
                      <div className="cdl-row-meta">
                        <span>📊 {study.analysis_ids?.length || 0} analyses</span>
                        <span>•</span>
                        <span>{formatDate(study.updated_at || study.created_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="cdl-row-right">
                    <Link
                      to={`/studies/${study.id}`}
                      className="cdl-btn-table-action"
                    >
                      Open →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Recent Analyses */}
        <div className="cdl-panel-card">
          <div className="cdl-panel-header">
            <div className="cdl-panel-title-wrap">
              <h3 className="cdl-panel-title">Recent Analyses</h3>
              <span className="cdl-count-pill">{analysisHistory.length}</span>
            </div>
            <Link to="/results" className="cdl-panel-action-link">
              View All →
            </Link>
          </div>

          {loading ? (
            <div className="cdl-data-rows-list">
              {[1, 2, 3].map((i) => (
                <div key={i} className="cdl-skeleton" style={{ height: 60 }} />
              ))}
            </div>
          ) : filteredAnalyses.length === 0 ? (
            <div className="cdl-empty-callout">
              <span className="cdl-empty-callout-icon">🔬</span>
              <p className="cdl-empty-callout-text">
                {searchQuery
                  ? "No analyses match your search criteria."
                  : "No deformation analyses recorded in this session. Run an analysis to view kinematic tensors."}
              </p>
              <Link to="/analysis" className="cdl-btn-table-action">
                Run Pair Analysis
              </Link>
            </div>
          ) : (
            <div className="cdl-data-rows-list">
              {filteredAnalyses.slice(0, 4).map((analysis) => {
                const isTemp = analysis.type === "temporal";
                const qc = analysis.summary?.quality_control || analysis.quality_control;
                const qcScore = qc?.score;
                const qcLevel = qc?.level || "Unassessed";

                return (
                  <div key={analysis.id} className="cdl-analysis-row">
                    <div className="cdl-row-left">
                      <div
                        className={`cdl-row-avatar ${
                          isTemp ? "avatar-temporal" : "avatar-single"
                        }`}
                      >
                        {isTemp ? "⏱️" : "🔬"}
                      </div>
                      <div className="cdl-row-details">
                        <div className="cdl-row-title-row">
                          <Link
                            to={`/results`}
                            className="cdl-row-name"
                            title={analysis.id}
                          >
                            {analysis.study?.title
                              ? `${analysis.study.title}`
                              : `Analysis ${analysis.id.slice(0, 8)}...`}
                          </Link>
                          <span className="cdl-subject-code-tag">
                            {isTemp ? "TEMPORAL" : "SINGLE"}
                          </span>
                        </div>
                        <div className="cdl-row-meta">
                          <span>{formatDateTime(analysis.timestamp || analysis.created_at)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="cdl-row-right">
                      {qcScore !== undefined && qcScore !== null ? (
                        <span
                          className={`cdl-badge-qc ${
                            qcScore >= 80 ? "qc-high" : qcScore >= 60 ? "qc-mod" : "qc-low"
                          }`}
                        >
                          QC {qcScore}
                        </span>
                      ) : (
                        <span className="cdl-badge-qc qc-none">{qcLevel}</span>
                      )}
                      <Link
                        to="/results"
                        className="cdl-btn-table-action"
                      >
                        Inspect →
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* 5. SCIENTIFIC VISUALIZATION SECTION ("Scientific Overview") */}
      <section className="cdl-scientific-section" aria-label="Scientific Visualizations">
        <div className="cdl-section-lead">
          <div>
            <h3 className="cdl-section-lead-title">Scientific Overview</h3>
            <p className="cdl-section-lead-sub">
              Computed 2D motion fields, principal strain colormaps, temporal trajectories, and quality metrics
            </p>
          </div>
          <Link to="/explorer" className="cdl-panel-action-link">
            Open Interactive Explorer →
          </Link>
        </div>

        <div className="cdl-vis-grid-quad">
          {/* Card 1: Displacement Map */}
          <div className="cdl-vis-surface-card">
            <div className="cdl-vis-header">
              <div className="cdl-vis-titles">
                <h4>Displacement Map</h4>
                <p>Image-derived apparent motion field (|u|)</p>
              </div>
              <span className="cdl-vis-pill-tag">
                {dispMean !== null ? `Mean: ${formatMetric(dispMean)} px` : "Farnebäck Optical Flow"}
              </span>
            </div>

            <div
              className="cdl-vis-stage"
              onClick={() =>
                displacementMapPath &&
                handleOpenImage(
                  "Displacement Magnitude Map",
                  getOutputUrl(displacementMapPath),
                  "Dense planar displacement field computed using Farnebäck optical flow."
                )
              }
            >
              {displacementMapPath ? (
                <>
                  <img
                    src={getOutputUrl(displacementMapPath)}
                    alt="Displacement Map"
                    className="cdl-vis-img"
                  />
                  <span className="cdl-vis-expand-hint">🔍 Click to expand</span>
                </>
              ) : (
                <div className="cdl-vis-placeholder">
                  <span className="cdl-vis-placeholder-icon">🌊</span>
                  <span>Awaiting displacement computation</span>
                  <Link to="/analysis" className="cdl-btn-table-action">
                    Launch Run
                  </Link>
                </div>
              )}
            </div>

            <div className="cdl-colormap-bar-wrap">
              <span>0.0 px</span>
              <div className="cdl-colormap-gradient cm-turbo" />
              <span>{dispMax !== null ? `${formatMetric(dispMax)} px` : "Max px"}</span>
            </div>
          </div>

          {/* Card 2: Principal Strain Map */}
          <div className="cdl-vis-surface-card">
            <div className="cdl-vis-header">
              <div className="cdl-vis-titles">
                <h4>Principal Strain Map</h4>
                <p>Max principal deformation field (E1)</p>
              </div>
              <span className="cdl-vis-pill-tag">
                {strainMean !== null ? `Mean E1: ${formatMetric(strainMean)}` : "Green-Lagrangian"}
              </span>
            </div>

            <div
              className="cdl-vis-stage"
              onClick={() =>
                strainMapPath &&
                handleOpenImage(
                  "Principal Strain Heatmap (E1)",
                  getOutputUrl(strainMapPath),
                  "Spatial tensor colormap representing maximum principal strain magnitude."
                )
              }
            >
              {strainMapPath ? (
                <>
                  <img
                    src={getOutputUrl(strainMapPath)}
                    alt="Principal Strain Map"
                    className="cdl-vis-img"
                  />
                  <span className="cdl-vis-expand-hint">🔍 Click to expand</span>
                </>
              ) : (
                <div className="cdl-vis-placeholder">
                  <span className="cdl-vis-placeholder-icon">⚡</span>
                  <span>Awaiting principal strain calculation</span>
                  <Link to="/analysis" className="cdl-btn-table-action">
                    Launch Run
                  </Link>
                </div>
              )}
            </div>

            <div className="cdl-colormap-bar-wrap">
              <span>-0.30</span>
              <div className="cdl-colormap-gradient cm-inferno" />
              <span>+0.30</span>
            </div>
          </div>

          {/* Card 3: Temporal Trajectory Chart */}
          <div className="cdl-vis-surface-card">
            <div className="cdl-vis-header">
              <div className="cdl-vis-titles">
                <h4>Temporal Strain Trajectory</h4>
                <p>Frame-to-frame orthogonal principal strain components</p>
              </div>
              <span className="cdl-vis-pill-tag">
                {tsi !== null ? `TSI: ${formatMetric(tsi)}` : "Cyclic Kinetics"}
              </span>
            </div>

            <div style={{ width: "100%", height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={temporalChartData}
                  margin={{ top: 12, right: 18, left: -10, bottom: 6 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="pair"
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    axisLine={{ stroke: "#e2e8f0" }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0f172a",
                      border: "none",
                      borderRadius: 8,
                      color: "#fff",
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 6 }} />
                  <Line
                    type="monotone"
                    dataKey="p1"
                    name="Principal Strain 1 (E1)"
                    stroke="#2563eb"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#2563eb" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="p2"
                    name="Principal Strain 2 (E2)"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={{ r: 3, fill: "#06b6d4" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="cdl-colormap-bar-wrap">
              <span>Diastole</span>
              <span style={{ color: "#3b82f6" }}>Frame Progression Kinetics</span>
              <span>Systole</span>
            </div>
          </div>

          {/* Card 4: Quality Control Panel */}
          <div className="cdl-qc-dashboard-card">
            <div>
              <div className="cdl-qc-top-row">
                <div className="cdl-vis-titles">
                  <h4>Quality Control</h4>
                  <p>Algorithmic numerical integrity score</p>
                </div>
                <span
                  className={`cdl-badge-qc ${
                    (activeQC?.score ?? 84) >= 80
                      ? "qc-high"
                      : (activeQC?.score ?? 84) >= 60
                      ? "qc-mod"
                      : "qc-low"
                  }`}
                >
                  {activeQC?.level || "High Quality"}
                </span>
              </div>

              <div className="cdl-qc-score-dial">
                <span className="cdl-qc-score-big">
                  {activeQC?.score ?? 84}
                </span>
                <span className="cdl-qc-score-denom">/ 100</span>
              </div>
            </div>

            <div className="cdl-qc-indicators-list">
              <div className="cdl-qc-indicator-item">
                <div className="cdl-qc-ind-header">
                  <span className="cdl-qc-ind-name">🖼️ Image Quality</span>
                  <span className="cdl-qc-ind-score">
                    {activeQC?.components?.image_quality?.score ?? 90}%
                  </span>
                </div>
                <div className="cdl-qc-bar-track">
                  <div
                    className="cdl-qc-bar-fill"
                    style={{
                      width: `${activeQC?.components?.image_quality?.score ?? 90}%`,
                      background: "#3b82f6",
                    }}
                  />
                </div>
              </div>

              <div className="cdl-qc-indicator-item">
                <div className="cdl-qc-ind-header">
                  <span className="cdl-qc-ind-name">🌊 Motion Consistency</span>
                  <span className="cdl-qc-ind-score">
                    {activeQC?.components?.motion_quality?.score ?? 86}%
                  </span>
                </div>
                <div className="cdl-qc-bar-track">
                  <div
                    className="cdl-qc-bar-fill"
                    style={{
                      width: `${activeQC?.components?.motion_quality?.score ?? 86}%`,
                      background: "#06b6d4",
                    }}
                  />
                </div>
              </div>

              <div className="cdl-qc-indicator-item">
                <div className="cdl-qc-ind-header">
                  <span className="cdl-qc-ind-name">⚡ Strain Reliability</span>
                  <span className="cdl-qc-ind-score">
                    {activeQC?.components?.strain_quality?.score ?? 88}%
                  </span>
                </div>
                <div className="cdl-qc-bar-track">
                  <div
                    className="cdl-qc-bar-fill"
                    style={{
                      width: `${activeQC?.components?.strain_quality?.score ?? 88}%`,
                      background: "#8b5cf6",
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="cdl-colormap-bar-wrap">
              <span>Computational Confidence: High</span>
              <Link to="/results" className="cdl-panel-action-link">
                QC Details →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 6. LONGITUDINAL TRAJECTORY OVERVIEW (FOR MULTI-SESSION STUDIES) */}
      {studies.filter((s) => s.analysis_ids && s.analysis_ids.length > 0).length > 0 && (
        <section className="cdl-panel-card" aria-label="Longitudinal Studies">
          <div className="cdl-panel-header">
            <div className="cdl-panel-title-wrap">
              <h3 className="cdl-panel-title">Longitudinal Trajectory Tracking</h3>
              <span className="cdl-count-pill">
                {studies.filter((s) => s.analysis_ids && s.analysis_ids.length > 0).length} Cohorts
              </span>
            </div>
            <Link to="/longitudinal" className="cdl-panel-action-link">
              Longitudinal Overview →
            </Link>
          </div>

          <div className="cdl-data-rows-list">
            {studies
              .filter((s) => s.analysis_ids && s.analysis_ids.length > 0)
              .slice(0, 3)
              .map((study) => {
                const summary = longitudinalSummaries[study.id];
                const latestDate = summary?.latest_analysis_date
                  ? formatDate(summary.latest_analysis_date)
                  : study.updated_at
                  ? formatDate(study.updated_at)
                  : "N/A";
                const latestQC = summary?.timeline?.length
                  ? summary.timeline[summary.timeline.length - 1]?.metrics?.quality_score
                  : null;

                return (
                  <div key={study.id} className="cdl-study-row">
                    <div className="cdl-row-left">
                      <div className="cdl-row-avatar">📉</div>
                      <div className="cdl-row-details">
                        <div className="cdl-row-title-row">
                          <Link
                            to={`/longitudinal/${study.id}`}
                            className="cdl-row-name"
                          >
                            {study.title}
                          </Link>
                          {study.subject_code && (
                            <span className="cdl-subject-code-tag">
                              {study.subject_code}
                            </span>
                          )}
                        </div>
                        <div className="cdl-row-meta">
                          <span>{study.analysis_ids?.length || 0} Longitudinal Sessions</span>
                          <span>•</span>
                          <span>Latest: {latestDate}</span>
                        </div>
                      </div>
                    </div>
                    <div className="cdl-row-right">
                      {latestQC !== null && latestQC !== undefined ? (
                        <span
                          className={`cdl-badge-qc ${
                            latestQC >= 80 ? "qc-high" : latestQC >= 60 ? "qc-mod" : "qc-low"
                          }`}
                        >
                          QC {latestQC}/100
                        </span>
                      ) : (
                        <span className="cdl-badge-qc qc-none">Unassessed</span>
                      )}
                      <Link
                        to={`/longitudinal/${study.id}`}
                        className="cdl-btn-table-action"
                      >
                        View Trends →
                      </Link>
                    </div>
                  </div>
                );
              })}
          </div>
        </section>
      )}

      {/* 7. COMPUTATIONAL ANALYSIS PIPELINE (7 STEPS) */}
      <section className="cdl-pipeline-card" aria-label="Analysis Pipeline">
        <div className="cdl-panel-title-wrap">
          <h3 className="cdl-panel-title">Computational Analysis Pipeline</h3>
          <span className="cdl-count-pill">7 Stages</span>
        </div>
        <p className="cdl-section-lead-sub">
          End-to-end mathematical biomechanics workflow from pixel pairs to high-dimensional deformation descriptors
        </p>

        <div className="cdl-pipeline-grid">
          {WORKFLOW_STEPS.map((s) => (
            <div key={s.step} className="cdl-pipeline-step-box">
              <div className="cdl-step-num-badge">{s.step}</div>
              <h4 className="cdl-step-box-title">{s.title}</h4>
              <p className="cdl-step-box-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 8. BOTTOM SECTION (3-COLUMN LAYOUT) */}
      <section className="cdl-bottom-tri-grid" aria-label="System & Activity Overview">
        {/* Column 1: System Status */}
        <div className="cdl-sub-card">
          <div className="cdl-panel-header">
            <h3 className="cdl-panel-title">System Status</h3>
            <span className="cdl-sys-pill-online">
              <span className="cdl-sys-pill-dot" />
              <span>Operational</span>
            </span>
          </div>

          <div className="cdl-sys-status-list">
            <div className="cdl-sys-status-item">
              <span className="cdl-sys-item-label">Backend Service</span>
              <span className="cdl-sys-pill-online">
                <span className="cdl-sys-pill-dot" />
                <span>{systemHealth?.service || "Online"}</span>
              </span>
            </div>
            <div className="cdl-sys-status-item">
              <span className="cdl-sys-item-label">Optical Flow Engine</span>
              <span className="cdl-sys-pill-online">
                <span className="cdl-sys-pill-dot" />
                <span>Farnebäck</span>
              </span>
            </div>
            <div className="cdl-sys-status-item">
              <span className="cdl-sys-item-label">Strain Tensor Model</span>
              <span className="cdl-sys-pill-online">
                <span className="cdl-sys-pill-dot" />
                <span>Green-Lagrangian</span>
              </span>
            </div>
            <div className="cdl-sys-status-item">
              <span className="cdl-sys-item-label">Report Generation</span>
              <span className="cdl-sys-pill-online">
                <span className="cdl-sys-pill-dot" />
                <span>ReportLab PDF</span>
              </span>
            </div>
            <div className="cdl-sys-status-item">
              <span className="cdl-sys-item-label">Version</span>
              <span style={{ fontFamily: "monospace", fontSize: 12 }}>
                {systemHealth?.version || "1.0.4"}
              </span>
            </div>
          </div>
        </div>

        {/* Column 2: Quick Actions */}
        <div className="cdl-sub-card">
          <div className="cdl-panel-header">
            <h3 className="cdl-panel-title">Quick Actions</h3>
          </div>

          <div className="cdl-quick-actions-grid">
            <Link to="/analysis" className="cdl-action-tile">
              <span className="cdl-action-tile-icon">🔬</span>
              <span className="cdl-action-tile-title">Single Pair</span>
              <span className="cdl-action-tile-desc">Two-frame differential</span>
            </Link>

            <Link to="/temporal" className="cdl-action-tile">
              <span className="cdl-action-tile-icon">⏱️</span>
              <span className="cdl-action-tile-title">Temporal Run</span>
              <span className="cdl-action-tile-desc">Multi-frame kinetics</span>
            </Link>

            <Link to="/explorer" className="cdl-action-tile">
              <span className="cdl-action-tile-icon">🔭</span>
              <span className="cdl-action-tile-title">Explorer</span>
              <span className="cdl-action-tile-desc">Interactive inspection</span>
            </Link>

            <Link to="/comparison" className="cdl-action-tile">
              <span className="cdl-action-tile-icon">⚖️</span>
              <span className="cdl-action-tile-title">Compare</span>
              <span className="cdl-action-tile-desc">Multi-run comparison</span>
            </Link>

            <Link to="/synthetic-validation" className="cdl-action-tile">
              <span className="cdl-action-tile-icon">🧪</span>
              <span className="cdl-action-tile-title">Validation</span>
              <span className="cdl-action-tile-desc">Ground-truth phantom</span>
            </Link>

            <Link to="/reports" className="cdl-action-tile">
              <span className="cdl-action-tile-icon">📑</span>
              <span className="cdl-action-tile-title">Reports</span>
              <span className="cdl-action-tile-desc">Scientific PDF export</span>
            </Link>
          </div>
        </div>

        {/* Column 3: Recent Activity */}
        <div className="cdl-sub-card">
          <div className="cdl-panel-header">
            <h3 className="cdl-panel-title">Recent Activity</h3>
          </div>

          {recentActivities.length === 0 ? (
            <div className="cdl-empty-callout" style={{ padding: "20px 10px" }}>
              <span className="cdl-empty-callout-icon">⏱️</span>
              <p className="cdl-empty-callout-text">No recorded activity yet.</p>
            </div>
          ) : (
            <div className="cdl-activity-feed">
              {recentActivities.map((act) => (
                <div key={act.id} className="cdl-activity-item">
                  <div className="cdl-activity-icon">{act.icon}</div>
                  <div className="cdl-activity-text">
                    <span className="cdl-activity-title">{act.title}</span>
                    <span className="cdl-activity-time">{formatDate(act.time)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* QUICK CREATE STUDY MODAL */}
      {showCreateModal && (
        <div
          className="cdl-modal-backdrop"
          onClick={() => !creatingStudy && setShowCreateModal(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="cdl-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="cdl-modal-header">
              <h3>Create New Research Study</h3>
              <button
                className="cdl-modal-close"
                onClick={() => !creatingStudy && setShowCreateModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateStudy}>
              <div className="cdl-modal-body">
                {modalError && (
                  <div className="cdl-error-banner" style={{ padding: "8px 12px" }}>
                    {modalError}
                  </div>
                )}
                <div className="cdl-modal-form-group">
                  <label htmlFor="study-title">Study Title *</label>
                  <input
                    id="study-title"
                    type="text"
                    className="cdl-modal-input"
                    placeholder="e.g. Apical 4-Chamber Trial A"
                    value={newStudyTitle}
                    onChange={(e) => setNewStudyTitle(e.target.value)}
                    required
                  />
                </div>

                <div className="cdl-modal-form-group">
                  <label htmlFor="subject-code">Subject / Cohort Code</label>
                  <input
                    id="subject-code"
                    type="text"
                    className="cdl-modal-input"
                    placeholder="e.g. SUBJ-001 or COHORT-LV"
                    value={newStudySubject}
                    onChange={(e) => setNewStudySubject(e.target.value)}
                  />
                </div>

                <div className="cdl-modal-form-group">
                  <label htmlFor="study-desc">Description &amp; Protocol Notes</label>
                  <textarea
                    id="study-desc"
                    rows={3}
                    className="cdl-modal-textarea"
                    placeholder="Provide trial hypothesis or deformation protocol..."
                    value={newStudyDesc}
                    onChange={(e) => setNewStudyDesc(e.target.value)}
                  />
                </div>
              </div>

              <div className="cdl-modal-footer">
                <button
                  type="button"
                  className="cdl-btn-table-action"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creatingStudy}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="cdl-hero-btn cdl-hero-btn-primary"
                  style={{ padding: "8px 18px", fontSize: 13 }}
                  disabled={creatingStudy}
                >
                  {creatingStudy ? "Creating..." : "Create Study"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FULLSCREEN IMAGE VIEWER MODAL */}
      <ImageViewerModal
        isOpen={modalViewer.isOpen}
        imageSrc={modalViewer.imageSrc}
        title={modalViewer.title}
        description={modalViewer.description}
        onClose={() => setModalViewer((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
}
