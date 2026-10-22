import { useState, useEffect, useMemo } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  getLongitudinalStudySummary,
  getStudyStatistics,
  getStudies,
  generateLongitudinalReport,
  getReportDownloadUrl,
  getOutputUrl,
} from "../services/api";
import "./LongitudinalAnalysis.css";

function formatMetric(val, decimals = 4) {
  if (val === null || val === undefined) return "—";
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
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(isoStr);
  }
}

function formatShortDate(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  } catch {
    return String(isoStr).slice(0, 10);
  }
}

export default function LongitudinalAnalysis() {
  const { studyId } = useParams();
  const navigate = useNavigate();

  const [studies, setStudies] = useState([]);
  const currentStudyId = studyId || "";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected session index for timeline inspection
  const [selectedSessionIndex, setSelectedSessionIndex] = useState(0);

  // Filter tabs for kinematic trajectories
  const [activeTab, setActiveTab] = useState("all");

  // PDF report export state
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(null);
  const [pdfError, setPdfError] = useState(null);
  const [statsPreview, setStatsPreview] = useState(null);

  // Load all studies for study switcher dropdown
  useEffect(() => {
    getStudies()
      .then((list) => {
        setStudies(list || []);
        if (!studyId && list && list.length > 0) {
          const withAnalyses = list.find((s) => s.analysis_ids && s.analysis_ids.length > 0);
          const chosen = withAnalyses ? withAnalyses.id : list[0].id;
          navigate(`/longitudinal/${chosen}`, { replace: true });
        }
      })
      .catch(() => {});
  }, [studyId, navigate]);

  // Fetch longitudinal data whenever studyId changes
  useEffect(() => {
    if (!studyId) return;
    setLoading(true);
    setError(null);
    setPdfSuccess(null);
    setPdfError(null);

    getLongitudinalStudySummary(studyId)
      .then((res) => {
        setData(res);
        if (res && res.timeline && res.timeline.length > 0) {
          setSelectedSessionIndex(res.timeline.length - 1);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load longitudinal study analysis.");
      })
      .finally(() => {
        setLoading(false);
      });

    // Also fetch statistics preview
    getStudyStatistics(studyId)
      .then((sData) => {
        setStatsPreview(sData);
      })
      .catch(() => {
        setStatsPreview(null);
      });
  }, [studyId]);

  const handleStudyChange = (e) => {
    const nextId = e.target.value;
    if (nextId) {
      navigate(`/longitudinal/${nextId}`);
    }
  };

  const handleGeneratePdf = async () => {
    if (!studyId) return;
    setPdfLoading(true);
    setPdfError(null);
    setPdfSuccess(null);

    try {
      const res = await generateLongitudinalReport(studyId);
      const url = getReportDownloadUrl(res.report_filename);
      setPdfSuccess({
        filename: res.report_filename,
        url: url,
      });
    } catch (err) {
      setPdfError(err.message || "Failed to generate longitudinal report PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  // Build Recharts data series from timeline
  const chartData = useMemo(() => {
    if (!data?.timeline) return [];
    return data.timeline.map((item, idx) => {
      const m = item.metrics || {};
      return {
        name: `S${idx + 1}`,
        sessionIndex: idx + 1,
        timestamp: item.timestamp,
        dateShort: formatShortDate(item.timestamp),
        dateFull: formatDate(item.timestamp),
        type: item.type === "temporal" ? "Temporal Sequence" : "Single Pair",
        mean_displacement: m.mean_displacement !== undefined ? m.mean_displacement : null,
        max_displacement: m.max_displacement !== undefined ? m.max_displacement : null,
        mean_strain: m.mean_strain !== undefined ? m.mean_strain : null,
        mean_principal_strain: m.mean_principal_strain !== undefined ? m.mean_principal_strain : null,
        anisotropy_index: m.anisotropy_index !== undefined ? m.anisotropy_index : null,
        motion_coherence: m.motion_coherence !== undefined ? m.motion_coherence : null,
        quality_score: m.quality_score !== undefined ? m.quality_score : null,
      };
    });
  }, [data]);

  const getTrendBadge = (direction) => {
    if (!direction || direction === "insufficient_data") {
      return <span className="cdl-long-trend-pill insufficient">Insufficient Data</span>;
    }
    if (direction === "increasing") {
      return <span className="cdl-long-trend-pill inc">▲ Increasing</span>;
    }
    if (direction === "decreasing") {
      return <span className="cdl-long-trend-pill dec">▼ Decreasing</span>;
    }
    return <span className="cdl-long-trend-pill stable">■ Stable</span>;
  };

  if (loading) {
    return (
      <div className="cdl-longitudinal-page">
        <div style={{ textAlign: "center", padding: "64px 20px" }}>
          <span className="cdl-long-spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
          <h3 style={{ marginTop: 16, color: "#475569" }}>Loading Longitudinal Study Trajectory...</h3>
          <p style={{ color: "#94a3b8", fontSize: 13 }}>Synthesizing multi-session deformation kinematic vectors.</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="cdl-longitudinal-page">
        <div className="cdl-long-banner cdl-long-banner-error" style={{ margin: "40px auto", maxWidth: 640 }}>
          <div>
            <h4 style={{ margin: "0 0 6px 0", fontSize: 16, fontWeight: 700 }}>Unable to Load Longitudinal Analysis</h4>
            <p style={{ margin: 0 }}>{error || "Study record or longitudinal timeline history unavailable."}</p>
          </div>
          <Link to="/studies" className="cdl-long-btn-secondary" style={{ whiteSpace: "nowrap" }}>
            &larr; Back to Studies
          </Link>
        </div>
      </div>
    );
  }

  const {
    study_title,
    subject_code,
    description,
    analysis_count = 0,
    first_analysis_date,
    latest_analysis_date,
    timeline = [],
    trends = {},
    first_vs_latest = {},
    quality_summary = {},
    calibration_consistency = {},
    roi_consistency = {},
    warnings = [],
    info = [],
  } = data;

  const activeSession = timeline[selectedSessionIndex] || timeline[timeline.length - 1] || null;

  const renderTrendChartCard = (metricKey, title, unit, colorHex, strokeWidth = 2.5) => {
    const trendInfo = trends[metricKey] || {};
    const nObs = trendInfo.observation_count || 0;
    const direction = trendInfo.trend_direction;

    return (
      <div className="cdl-long-chart-card" key={metricKey}>
        <div className="cdl-long-chart-header">
          <div>
            <h4 className="cdl-long-chart-title">{title}</h4>
            <span className="cdl-long-chart-unit">{unit ? `Physical Units: ${unit}` : "Dimensionless Ratio / Index"}</span>
          </div>
          <div>{getTrendBadge(direction)}</div>
        </div>

        {nObs < 2 ? (
          <div className="cdl-long-chart-insufficient">
            <span style={{ fontSize: 24 }}>📉</span>
            <p>At least 2 session observations required to compute trajectory gradient.</p>
            <span>Available data: {nObs} valid session(s)</span>
          </div>
        ) : (
          <div className="cdl-long-chart-body">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 12, right: 20, left: -14, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" opacity={0.6} />
                <XAxis
                  dataKey="dateShort"
                  tick={{ fontSize: 10, fill: "#64748b" }}
                  stroke="#cbd5e1"
                />
                <YAxis
                  domain={["auto", "auto"]}
                  tick={{ fontSize: 10, fill: "#64748b" }}
                  stroke="#cbd5e1"
                  tickFormatter={(val) => (typeof val === "number" ? val.toFixed(2) : val)}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const p = payload[0];
                      const d = p.payload;
                      return (
                        <div className="cdl-long-tooltip">
                          <div className="cdl-long-tooltip-title">Session #{d.sessionIndex} ({d.type})</div>
                          <div className="cdl-long-tooltip-date">{d.dateFull}</div>
                          <div className="cdl-long-tooltip-val" style={{ color: colorHex }}>
                            {title}: {formatMetric(p.value)} {unit}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey={metricKey}
                  stroke={colorHex}
                  strokeWidth={strokeWidth}
                  dot={{ r: 4, stroke: colorHex, strokeWidth: 2, fill: "#ffffff" }}
                  activeDot={{ r: 6, fill: colorHex }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="cdl-long-chart-footer">
          <span>First: <strong>{formatMetric(trendInfo.first_value)}</strong></span>
          <span>Latest: <strong>{formatMetric(trendInfo.latest_value)}</strong></span>
          <span>
            Δ: <strong>{formatMetric(trendInfo.absolute_change)}</strong>
            {trendInfo.percentage_change !== null && trendInfo.percentage_change !== undefined && (
              <span style={{ color: trendInfo.percentage_change > 0 ? "#dc2626" : "#059669", marginLeft: 4 }}>
                ({trendInfo.percentage_change > 0 ? "+" : ""}{trendInfo.percentage_change}%)
              </span>
            )}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="cdl-longitudinal-page">
      {/* 1. Page Header & Breadcrumb */}
      <div className="cdl-long-header-wrap">
        <div className="cdl-long-title-area">
          <div className="cdl-long-breadcrumb">
            <Link to="/studies" className="bc-link">
              📁 Studies
            </Link>
            <span className="bc-sep">/</span>
            <Link to={`/studies/${studyId}`} className="bc-link">
              {study_title || "Study Workspace"}
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Longitudinal Trajectory</span>
          </div>

          <div className="cdl-long-pill-row">
            <span className="cdl-long-subject-pill">
              🔬 {subject_code ? `Subject: ${subject_code}` : "Cohort / Unassigned"}
            </span>
            <span className="cdl-long-study-pill">
              {analysis_count} Recorded {analysis_count === 1 ? "Session" : "Sessions"}
            </span>
          </div>

          <h1 className="cdl-long-title">Longitudinal Deformation Trajectory</h1>
          <p className="cdl-long-subtitle">
            {description ||
              "Multi-session tracking of biomechanical tissue strain, displacement drift, and computational stability over time."}
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="cdl-long-header-actions">
          {studies.length > 1 && (
            <div className="cdl-long-switcher-box">
              <label htmlFor="study-switcher-select" className="cdl-long-switcher-label">
                Study:
              </label>
              <select
                id="study-switcher-select"
                value={currentStudyId}
                onChange={handleStudyChange}
                className="cdl-long-select"
              >
                {studies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} ({s.analysis_ids?.length || 0})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            className="cdl-long-btn-primary"
            onClick={handleGeneratePdf}
            disabled={pdfLoading || analysis_count === 0}
            title="Generate comprehensive longitudinal PDF research report"
          >
            {pdfLoading ? (
              <>
                <span className="cdl-long-spinner" /> Generating Report...
              </>
            ) : (
              <>📄 Export Longitudinal PDF</>
            )}
          </button>

          <Link to={`/statistics/${studyId}`} className="cdl-long-btn-secondary" title="View statistical distribution & regression models">
            📐 Advanced Statistics
          </Link>

          <Link to={`/studies/${studyId}`} className="cdl-long-btn-secondary" title="Open parent study management workspace">
            📁 Study Workspace
          </Link>
        </div>
      </div>

      {/* PDF Export Notification Banners */}
      {pdfSuccess && (
        <div className="cdl-long-banner cdl-long-banner-success">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span>✅</span>
            <div>
              <strong>Longitudinal Research Report generated successfully.</strong>
              <div style={{ fontSize: 12, opacity: 0.9 }}>File: {pdfSuccess.filename}</div>
            </div>
          </div>
          <a
            href={pdfSuccess.url}
            target="_blank"
            rel="noopener noreferrer"
            className="cdl-long-download-link"
          >
            📥 Download / Inspect PDF
          </a>
        </div>
      )}

      {pdfError && (
        <div className="cdl-long-banner cdl-long-banner-error">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span>⚠️</span>
            <span>{pdfError}</span>
          </div>
        </div>
      )}

      {/* Non-Clinical Research Disclaimer */}
      <div className="cdl-long-disclaimer-card">
        <span className="cdl-long-disclaimer-badge">Research Prototype</span>
        <p className="cdl-long-disclaimer-text">
          Longitudinal analysis measures mathematical variations in image-derived deformation fields across discrete recording sessions.
          This software is an investigational computational tool and does <strong>NOT</strong> provide diagnostic interpretations, clinical prognosis, or medical disease monitoring.
        </p>
      </div>

      {analysis_count === 0 ? (
        <div className="cdl-long-empty-card">
          <div className="cdl-long-empty-icon">📊</div>
          <h3 className="cdl-long-empty-title">No Longitudinal Analyses Recorded</h3>
          <p className="cdl-long-empty-desc">
            To construct a longitudinal deformation trajectory, link two or more completed analyses (single image pairs or temporal sequences) to this study.
          </p>
          <div className="cdl-long-empty-actions">
            <Link to="/analysis" className="cdl-long-btn-primary">
              🔬 Run Single Pair Analysis
            </Link>
            <Link to="/temporal" className="cdl-long-btn-secondary">
              ⏱️ Run Temporal Sequence
            </Link>
            <Link to={`/studies/${studyId}`} className="cdl-long-btn-secondary">
              📁 Manage Study Analyses
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* 2. Top Summary KPI Cards */}
          <div className="cdl-long-kpi-grid">
            <div className="cdl-long-kpi-card">
              <div className="cdl-long-kpi-header">
                <span>Recorded Sessions</span>
                <span className="cdl-long-kpi-icon">📋</span>
              </div>
              <div className="cdl-long-kpi-val">{analysis_count}</div>
              <div className="cdl-long-kpi-sub">
                <span>Timeline sequence depth</span>
              </div>
            </div>

            <div className="cdl-long-kpi-card">
              <div className="cdl-long-kpi-header">
                <span>Baseline Session</span>
                <span className="cdl-long-kpi-icon">📅</span>
              </div>
              <div className="cdl-long-kpi-val" style={{ fontSize: 18 }}>
                {formatDate(first_analysis_date)}
              </div>
              <div className="cdl-long-kpi-sub">
                <span>Session #1 timestamp</span>
              </div>
            </div>

            <div className="cdl-long-kpi-card">
              <div className="cdl-long-kpi-header">
                <span>Latest Session</span>
                <span className="cdl-long-kpi-icon">⏱️</span>
              </div>
              <div className="cdl-long-kpi-val" style={{ fontSize: 18 }}>
                {formatDate(latest_analysis_date)}
              </div>
              <div className="cdl-long-kpi-sub">
                <span>Terminal observation point</span>
              </div>
            </div>

            <div className="cdl-long-kpi-card">
              <div className="cdl-long-kpi-header">
                <span>Displacement Shift</span>
                <span className="cdl-long-kpi-icon">↔️</span>
              </div>
              <div className="cdl-long-kpi-val">
                {trends.mean_displacement?.absolute_change !== undefined
                  ? `${formatMetric(trends.mean_displacement.absolute_change, 3)} px`
                  : "—"}
              </div>
              <div className="cdl-long-kpi-sub">
                {trends.mean_displacement?.percentage_change !== null &&
                trends.mean_displacement?.percentage_change !== undefined ? (
                  <span
                    className={`cdl-long-trend-pill ${
                      trends.mean_displacement.percentage_change > 0
                        ? "inc"
                        : trends.mean_displacement.percentage_change < 0
                        ? "dec"
                        : "stable"
                    }`}
                  >
                    {trends.mean_displacement.percentage_change > 0 ? "+" : ""}
                    {trends.mean_displacement.percentage_change}%
                  </span>
                ) : (
                  <span>Baseline relative delta</span>
                )}
              </div>
            </div>

            <div className="cdl-long-kpi-card">
              <div className="cdl-long-kpi-header">
                <span>Normal Strain Shift</span>
                <span className="cdl-long-kpi-icon">📈</span>
              </div>
              <div className="cdl-long-kpi-val">
                {trends.mean_strain?.absolute_change !== undefined
                  ? formatMetric(trends.mean_strain.absolute_change, 4)
                  : "—"}
              </div>
              <div className="cdl-long-kpi-sub">
                {trends.mean_strain?.percentage_change !== null &&
                trends.mean_strain?.percentage_change !== undefined ? (
                  <span
                    className={`cdl-long-trend-pill ${
                      trends.mean_strain.percentage_change > 0
                        ? "inc"
                        : trends.mean_strain.percentage_change < 0
                        ? "dec"
                        : "stable"
                    }`}
                  >
                    {trends.mean_strain.percentage_change > 0 ? "+" : ""}
                    {trends.mean_strain.percentage_change}%
                  </span>
                ) : (
                  <span>Baseline relative delta</span>
                )}
              </div>
            </div>

            <div className="cdl-long-kpi-card">
              <div className="cdl-long-kpi-header">
                <span>Mean Data Quality</span>
                <span className="cdl-long-kpi-icon">🛡️</span>
              </div>
              <div className="cdl-long-kpi-val">
                {quality_summary.average_score !== null && quality_summary.average_score !== undefined
                  ? `${quality_summary.average_score}/100`
                  : "Unassessed"}
              </div>
              <div className="cdl-long-kpi-sub">
                <span className="cdl-long-tier-chip high">H: {quality_summary.high_count || 0}</span>
                <span className="cdl-long-tier-chip mod">M: {quality_summary.moderate_count || 0}</span>
                <span className="cdl-long-tier-chip low">L: {quality_summary.low_count || 0}</span>
              </div>
            </div>
          </div>

          {/* 3. Interactive Chronological Session Timeline */}
          <section className="cdl-long-timeline-section">
            <div className="cdl-long-section-header">
              <div className="cdl-long-section-title-wrap">
                <h3 className="cdl-long-section-title">Chronological Session Timeline</h3>
                <span className="cdl-long-badge cdl-long-badge-blue">{analysis_count} Checkpoints</span>
              </div>
              <span style={{ fontSize: 12, color: "#64748b" }}>
                Click any session node below to inspect parameters and deep-link to the Explorer workstation.
              </span>
            </div>

            {/* Horizontal Timeline Strip */}
            <div className="cdl-long-timeline-strip">
              {timeline.map((session, idx) => {
                const isSelected = selectedSessionIndex === idx;
                const isTemp = session.type === "temporal";
                const qc = session.metrics?.quality_score;
                return (
                  <button
                    key={session.analysis_id || idx}
                    type="button"
                    className={`cdl-long-timeline-node ${isSelected ? "active" : ""}`}
                    onClick={() => setSelectedSessionIndex(idx)}
                  >
                    <span className="cdl-long-node-index">SESSION #{idx + 1}</span>
                    <span className="cdl-long-node-date">{formatShortDate(session.timestamp)}</span>
                    <span className={`cdl-long-node-pill ${isTemp ? "temp" : "single"}`}>
                      {isTemp ? "Temporal" : "Pair"}
                    </span>
                    {qc !== null && qc !== undefined && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: qc >= 80 ? "#059669" : qc >= 60 ? "#d97706" : "#dc2626" }}>
                        QC: {qc}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Active Session Inspector Card */}
            {activeSession && (
              <div className="cdl-long-inspector-card">
                <div className="cdl-long-inspector-top">
                  <div className="cdl-long-inspector-id-block">
                    <span className="cdl-long-badge cdl-long-badge-purple">
                      Active Inspector &bull; Session #{selectedSessionIndex + 1}
                    </span>
                    <span className="cdl-long-inspector-title">
                      {activeSession.type === "temporal" ? "Temporal Image Sequence" : "Single Pair Analysis"}
                    </span>
                    <code className="cdl-long-uuid-pill">
                      ID: {activeSession.analysis_id ? activeSession.analysis_id.slice(0, 12) + "..." : "N/A"}
                    </code>
                    <span style={{ fontSize: 12, color: "#64748b" }}>
                      Recorded: {formatDate(activeSession.timestamp)}
                    </span>
                  </div>

                  <div className="cdl-long-inspector-actions">
                    {activeSession.analysis_id && (
                      <Link
                        to={`/explorer/${activeSession.analysis_id}`}
                        className="cdl-long-btn-sm cdl-long-btn-sm-primary"
                        title="Open interactive spatial deformation explorer workstation"
                      >
                        🔭 Open Explorer
                      </Link>
                    )}
                    <Link
                      to={`/studies/${studyId}`}
                      className="cdl-long-btn-sm cdl-long-btn-sm-secondary"
                    >
                      📁 View Study File
                    </Link>
                  </div>
                </div>

                <div className="cdl-long-inspector-metrics-grid">
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Mean Displacement</span>
                    <span className="stat-val">{formatMetric(activeSession.metrics?.mean_displacement)} px</span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Max Displacement</span>
                    <span className="stat-val">{formatMetric(activeSession.metrics?.max_displacement)} px</span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Mean Normal Strain</span>
                    <span className="stat-val">{formatMetric(activeSession.metrics?.mean_strain)}</span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Principal Strain</span>
                    <span className="stat-val">{formatMetric(activeSession.metrics?.mean_principal_strain)}</span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Motion Coherence</span>
                    <span className="stat-val">{formatMetric(activeSession.metrics?.motion_coherence)}</span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Anisotropy Index</span>
                    <span className="stat-val">{formatMetric(activeSession.metrics?.anisotropy_index)}</span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Quality Score</span>
                    <span className="stat-val">
                      {activeSession.metrics?.quality_score !== null && activeSession.metrics?.quality_score !== undefined
                        ? `${activeSession.metrics.quality_score}/100`
                        : "Unassessed"}
                    </span>
                  </div>
                  <div className="cdl-long-inspector-stat">
                    <span className="stat-label">Calibration & ROI</span>
                    <span className="stat-val" style={{ fontSize: 12 }}>
                      {activeSession.calibration ? "Calibrated" : "Pixels"} &bull;{" "}
                      {activeSession.roi ? "Masked ROI" : "Full Frame"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* 4. First vs. Latest Comparative Analysis */}
          {first_vs_latest?.available && (
            <section className="cdl-long-fvl-section">
              <div className="cdl-long-section-header">
                <div className="cdl-long-section-title-wrap">
                  <h3 className="cdl-long-section-title">Baseline vs. Latest Comparative Analysis</h3>
                  <span className="cdl-long-badge cdl-long-badge-purple">Quantitative Variance</span>
                </div>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  Comparing Session #1 ({formatShortDate(first_vs_latest.first_session?.timestamp)}) with Terminal Session #{analysis_count} ({formatShortDate(first_vs_latest.latest_session?.timestamp)})
                </span>
              </div>

              <div className="cdl-long-fvl-table-box">
                <table className="cdl-long-table">
                  <thead>
                    <tr>
                      <th>Biomechanical Metric</th>
                      <th>First (Baseline)</th>
                      <th>Latest Session</th>
                      <th>Absolute Delta (Δ)</th>
                      <th>Relative Variance</th>
                      <th>Trend Direction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(first_vs_latest.metrics || {}).map(([key, item]) => {
                      const u = item.unit ? ` ${item.unit}` : "";
                      return (
                        <tr key={key}>
                          <td className="cell-metric-label">
                            {item.label}
                          </td>
                          <td>
                            {formatMetric(item.first_value)}
                            {item.first_value !== null ? u : ""}
                          </td>
                          <td>
                            {formatMetric(item.latest_value)}
                            {item.latest_value !== null ? u : ""}
                          </td>
                          <td className="cell-delta">
                            {formatMetric(item.absolute_change)}
                            {item.absolute_change !== null ? u : ""}
                          </td>
                          <td>
                            {item.percentage_change !== null && item.percentage_change !== undefined ? (
                              <span
                                className={`cdl-long-pct-badge ${
                                  item.percentage_change > 0
                                    ? "pos"
                                    : item.percentage_change < 0
                                    ? "neg"
                                    : "zero"
                                }`}
                              >
                                {item.percentage_change > 0 ? "+" : ""}
                                {item.percentage_change}%
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>{getTrendBadge(item.trend)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Side-by-Side Visual Spatial Maps if heatmaps exist */}
              {(first_vs_latest.first_session?.outputs?.displacement_heatmap ||
                first_vs_latest.latest_session?.outputs?.displacement_heatmap) && (
                <div className="cdl-long-fvl-maps-grid">
                  <div className="cdl-long-map-card">
                    <div className="cdl-long-map-header">
                      <span className="cdl-long-map-title">Baseline Session #1 — Spatial Field</span>
                      <span className="cdl-long-map-timestamp">
                        {formatDate(first_vs_latest.first_session?.timestamp)}
                      </span>
                    </div>
                    <div className="cdl-long-map-canvas">
                      {first_vs_latest.first_session?.outputs?.displacement_heatmap ? (
                        <img
                          src={getOutputUrl(first_vs_latest.first_session.outputs.displacement_heatmap)}
                          alt="Baseline Displacement Heatmap"
                          loading="lazy"
                        />
                      ) : (
                        <div className="cdl-long-map-canvas-fallback">
                          <span>🌐</span>
                          <span>No baseline displacement heatmap rendered</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="cdl-long-map-card">
                    <div className="cdl-long-map-header">
                      <span className="cdl-long-map-title">Terminal Session #{analysis_count} — Spatial Field</span>
                      <span className="cdl-long-map-timestamp">
                        {formatDate(first_vs_latest.latest_session?.timestamp)}
                      </span>
                    </div>
                    <div className="cdl-long-map-canvas">
                      {first_vs_latest.latest_session?.outputs?.displacement_heatmap ? (
                        <img
                          src={getOutputUrl(first_vs_latest.latest_session.outputs.displacement_heatmap)}
                          alt="Terminal Displacement Heatmap"
                          loading="lazy"
                        />
                      ) : (
                        <div className="cdl-long-map-canvas-fallback">
                          <span>🌐</span>
                          <span>No terminal displacement heatmap rendered</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* 5. Longitudinal Kinematic Trajectory Trend Cards */}
          <section className="cdl-long-trends-section">
            <div className="cdl-long-section-header">
              <div className="cdl-long-section-title-wrap">
                <h3 className="cdl-long-section-title">Kinematic Trajectory Curves</h3>
                <span className="cdl-long-badge cdl-long-badge-emerald">Time Series</span>
              </div>

              {/* Filter Tabs */}
              <div className="cdl-long-filter-tabs">
                <button
                  type="button"
                  className={`cdl-long-tab-btn ${activeTab === "all" ? "active" : ""}`}
                  onClick={() => setActiveTab("all")}
                >
                  All Metrics ({Object.keys(trends).length})
                </button>
                <button
                  type="button"
                  className={`cdl-long-tab-btn ${activeTab === "displacement" ? "active" : ""}`}
                  onClick={() => setActiveTab("displacement")}
                >
                  Displacement Kinematics
                </button>
                <button
                  type="button"
                  className={`cdl-long-tab-btn ${activeTab === "strain" ? "active" : ""}`}
                  onClick={() => setActiveTab("strain")}
                >
                  Strain & Principal
                </button>
                <button
                  type="button"
                  className={`cdl-long-tab-btn ${activeTab === "advanced" ? "active" : ""}`}
                  onClick={() => setActiveTab("advanced")}
                >
                  Biomechanical Indices
                </button>
                <button
                  type="button"
                  className={`cdl-long-tab-btn ${activeTab === "quality" ? "active" : ""}`}
                  onClick={() => setActiveTab("quality")}
                >
                  Data Quality (QC)
                </button>
              </div>
            </div>

            <div className="cdl-long-charts-grid">
              {(activeTab === "all" || activeTab === "displacement") && (
                <>
                  {renderTrendChartCard("mean_displacement", "Mean Displacement", "px", "#2563eb")}
                  {renderTrendChartCard("max_displacement", "Max Displacement", "px", "#0284c7")}
                </>
              )}
              {(activeTab === "all" || activeTab === "strain") && (
                <>
                  {renderTrendChartCard("mean_strain", "Mean Normal Strain", "", "#0891b2")}
                  {renderTrendChartCard("mean_principal_strain", "Mean Principal Strain", "", "#10b981")}
                </>
              )}
              {(activeTab === "all" || activeTab === "advanced") && (
                <>
                  {renderTrendChartCard("anisotropy_index", "Anisotropy Index", "", "#8b5cf6")}
                  {renderTrendChartCard("motion_coherence", "Motion Coherence", "", "#f59e0b")}
                </>
              )}
              {(activeTab === "all" || activeTab === "quality") && (
                <>
                  {renderTrendChartCard("quality_score", "Quality Control Score", "/100", "#ec4899")}
                </>
              )}
            </div>
          </section>

          {/* 6. Computational Consistency & Validation Layer */}
          <div className="cdl-long-consistency-grid">
            {/* Quality Summary Card */}
            <div className="cdl-long-consistency-card">
              <div className="cdl-long-card-top-row">
                <h4 className="cdl-long-card-top-title">Quality Control Distribution</h4>
                <span className="cdl-long-badge cdl-long-badge-blue">Validation Layer</span>
              </div>
              <div className="cdl-long-qc-metrics-row">
                <div className="cdl-long-qc-stat-item">
                  <span className="cdl-long-qc-stat-label">Average Score</span>
                  <span className="cdl-long-qc-stat-num">
                    {quality_summary.average_score !== null && quality_summary.average_score !== undefined
                      ? `${quality_summary.average_score}`
                      : "—"}
                  </span>
                </div>
                <div className="cdl-long-qc-stat-item">
                  <span className="cdl-long-qc-stat-label">Min / Max Range</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "#334155" }}>
                    {quality_summary.min_score ?? "—"} / {quality_summary.max_score ?? "—"}
                  </span>
                </div>
                <div className="cdl-long-qc-stat-item">
                  <span className="cdl-long-qc-stat-label">Tier Breakdown</span>
                  <div className="cdl-long-qc-tiers-row">
                    <span className="cdl-long-tier-chip high">H: {quality_summary.high_count || 0}</span>
                    <span className="cdl-long-tier-chip mod">M: {quality_summary.moderate_count || 0}</span>
                    <span className="cdl-long-tier-chip low">L: {quality_summary.low_count || 0}</span>
                  </div>
                </div>
              </div>
              {quality_summary.unassessed_count > 0 && (
                <span className="cdl-long-consistency-sub" style={{ color: "#d97706" }}>
                  ⚠️ {quality_summary.unassessed_count} session(s) pending automated quality evaluation.
                </span>
              )}
            </div>

            {/* Spatial Calibration Consistency */}
            <div className="cdl-long-consistency-card">
              <div className="cdl-long-card-top-row">
                <h4 className="cdl-long-card-top-title">Spatial Calibration Consistency</h4>
                <span
                  className={`cdl-long-badge ${
                    calibration_consistency.status === "consistent"
                      ? "cdl-long-badge-emerald"
                      : calibration_consistency.status === "mixed"
                      ? "cdl-long-badge-purple"
                      : "cdl-long-badge-slate"
                  }`}
                >
                  {calibration_consistency.status?.toUpperCase() || "UNCALIBRATED"}
                </span>
              </div>
              <p className="cdl-long-consistency-desc">{calibration_consistency.details || "No calibration metadata available."}</p>
              <div className="cdl-long-consistency-sub">
                {calibration_consistency.status === "uncalibrated"
                  ? "All displacement calculations are evaluated in pixel coordinates."
                  : `${calibration_consistency.calibrated_count || 0} of ${calibration_consistency.total_count || 0} sessions calibrated to physical units.`}
              </div>
            </div>

            {/* ROI Consistency */}
            <div className="cdl-long-consistency-card">
              <div className="cdl-long-card-top-row">
                <h4 className="cdl-long-card-top-title">Region of Interest (ROI) Scope</h4>
                <span
                  className={`cdl-long-badge ${
                    roi_consistency.status === "consistent"
                      ? "cdl-long-badge-emerald"
                      : roi_consistency.status === "mixed"
                      ? "cdl-long-badge-purple"
                      : "cdl-long-badge-slate"
                  }`}
                >
                  {roi_consistency.status?.toUpperCase() || "FULL-FRAME"}
                </span>
              </div>
              <p className="cdl-long-consistency-desc">{roi_consistency.details || "No ROI segmentation metadata recorded."}</p>
              <div className="cdl-long-consistency-sub">
                {roi_consistency.roi_count === 0
                  ? "Full-frame deformation evaluated across all sessions."
                  : `${roi_consistency.roi_count || 0} of ${roi_consistency.total_count || 0} sessions utilized anatomical ROI masks.`}
              </div>
            </div>
          </div>

          {/* 7. Study Warnings & Information Notices */}
          {(warnings.length > 0 || info.length > 0) && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {warnings.map((w, i) => (
                <div key={i} className="cdl-long-banner cdl-long-banner-warning">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span>⚠️</span>
                    <span>{w}</span>
                  </div>
                </div>
              ))}
              {info.map((inf, i) => (
                <div key={i} className="cdl-long-banner cdl-long-banner-info">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span>ℹ️</span>
                    <span>{inf}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 8. Advanced Statistics Preview Banner */}
          {statsPreview && (
            <div className="cdl-long-stats-preview-card">
              <div className="cdl-long-stats-preview-top">
                <div>
                  <span className="cdl-long-badge cdl-long-badge-purple" style={{ marginBottom: 6 }}>
                    Research Analytics
                  </span>
                  <h3 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>
                    Study Statistical Analytics Preview
                  </h3>
                  <span style={{ fontSize: 12, color: "#93c5fd" }}>
                    Descriptive moments, outlier bounds, and correlation vectors for this study.
                  </span>
                </div>
                <Link to={`/statistics/${studyId}`} className="cdl-long-btn-primary">
                  Open Statistical Workspace &rarr;
                </Link>
              </div>

              <div className="cdl-long-stats-metrics-grid">
                <div className="cdl-long-stats-tile">
                  <span className="tile-label">Displacement Mean</span>
                  <span className="tile-val">
                    {formatMetric(statsPreview?.descriptive_statistics?.mean_displacement?.mean)} px
                  </span>
                </div>
                <div className="cdl-long-stats-tile">
                  <span className="tile-label">Strain Mean</span>
                  <span className="tile-val">
                    {formatMetric(statsPreview?.descriptive_statistics?.mean_strain?.mean)}
                  </span>
                </div>
                <div className="cdl-long-stats-tile">
                  <span className="tile-label">Displacement Std Dev</span>
                  <span className="tile-val">
                    {formatMetric(statsPreview?.descriptive_statistics?.mean_displacement?.std)}
                  </span>
                </div>
                <div className="cdl-long-stats-tile">
                  <span className="tile-label">Computational Outliers</span>
                  <span className="tile-val" style={{ color: statsPreview?.total_outliers_count > 0 ? "#fbbf24" : "#ffffff" }}>
                    {statsPreview?.total_outliers_count ?? 0}
                  </span>
                </div>
                <div className="cdl-long-stats-tile">
                  <span className="tile-label">Top Correlation Vector</span>
                  <span className="tile-val" style={{ fontSize: 12 }}>
                    {statsPreview?.correlations && statsPreview.correlations.length > 0
                      ? `${statsPreview.correlations[0].label_x} vs ${statsPreview.correlations[0].label_y} (r=${statsPreview.correlations[0].correlation})`
                      : "Insufficient Data"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 9. Full Analysis Session Timeline Data Table */}
          <section className="cdl-long-table-section">
            <div className="cdl-long-section-header">
              <div className="cdl-long-section-title-wrap">
                <h3 className="cdl-long-section-title">Session Audit Record ({analysis_count})</h3>
                <span className="cdl-long-badge cdl-long-badge-slate">Complete Log</span>
              </div>
            </div>

            <div className="cdl-long-fvl-table-box">
              <table className="cdl-long-table">
                <thead>
                  <tr>
                    <th>Session #</th>
                    <th>Date / Timestamp</th>
                    <th>Type</th>
                    <th>Mean Disp</th>
                    <th>Mean Strain</th>
                    <th>Principal Strain</th>
                    <th>Motion Coherence</th>
                    <th>QC Score</th>
                    <th style={{ textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.map((item, idx) => {
                    const m = item.metrics || {};
                    const isTemp = item.type === "temporal";
                    const qc = m.quality_score;
                    const isSelected = selectedSessionIndex === idx;

                    return (
                      <tr
                        key={item.analysis_id || idx}
                        className={isSelected ? "cdl-long-row-active" : ""}
                        onClick={() => setSelectedSessionIndex(idx)}
                        style={{ cursor: "pointer" }}
                      >
                        <td style={{ fontWeight: 800, color: "#2563eb" }}>
                          #{idx + 1}
                        </td>
                        <td>
                          <div style={{ fontWeight: 600 }}>{formatDate(item.timestamp)}</div>
                          <code className="cdl-long-uuid-pill" style={{ fontSize: 10 }}>
                            {(item.analysis_id || "").slice(0, 8)}
                          </code>
                        </td>
                        <td>
                          <span className={`cdl-long-node-pill ${isTemp ? "temp" : "single"}`}>
                            {isTemp ? "Temporal Sequence" : "Single Pair"}
                          </span>
                        </td>
                        <td style={{ fontFamily: "monospace" }}>{formatMetric(m.mean_displacement)} px</td>
                        <td style={{ fontFamily: "monospace" }}>{formatMetric(m.mean_strain)}</td>
                        <td style={{ fontFamily: "monospace" }}>{formatMetric(m.mean_principal_strain)}</td>
                        <td style={{ fontFamily: "monospace" }}>{formatMetric(m.motion_coherence)}</td>
                        <td>
                          {qc !== null && qc !== undefined ? (
                            <span
                              className="cdl-long-badge"
                              style={{
                                background: qc >= 80 ? "#dcfce7" : qc >= 60 ? "#fef3c7" : "#fee2e2",
                                color: qc >= 80 ? "#15803d" : qc >= 60 ? "#b45309" : "#b91c1c",
                              }}
                            >
                              {qc} ({item.quality_level || "Assessed"})
                            </span>
                          ) : (
                            <span className="cdl-long-badge cdl-long-badge-slate">Unassessed</span>
                          )}
                        </td>
                        <td style={{ textAlign: "right" }} onClick={(e) => e.stopPropagation()}>
                          <div style={{ display: "inline-flex", gap: 6 }}>
                            <Link
                              to={`/explorer/${item.analysis_id}`}
                              className="cdl-long-btn-sm cdl-long-btn-sm-primary"
                              title="Explore interactive deformation fields"
                            >
                              🔭 Explore
                            </Link>
                            <Link
                              to={`/studies/${studyId}`}
                              className="cdl-long-btn-sm cdl-long-btn-sm-secondary"
                              title="Inspect study workspace"
                            >
                              📁 Workspace
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
