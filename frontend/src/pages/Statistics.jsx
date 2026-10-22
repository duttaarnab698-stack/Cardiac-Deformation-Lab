import { useState, useEffect, useMemo } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  LineChart,
  Line,
} from "recharts";
import {
  getStudyStatistics,
  getStudies,
  generateStatisticsReport,
  getReportDownloadUrl,
} from "../services/api";
import "./Statistics.css";

function formatNumber(val, decimals = 4) {
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

function getCorrelationColor(r) {
  if (r === null || r === undefined) return "transparent";
  if (r >= 0.7) return "rgba(14, 165, 233, 0.55)"; // Strong positive sky
  if (r >= 0.3) return "rgba(14, 165, 233, 0.32)"; // Moderate positive
  if (r > 0.05) return "rgba(14, 165, 233, 0.15)"; // Weak positive
  if (r <= -0.7) return "rgba(168, 85, 247, 0.55)"; // Strong negative purple
  if (r <= -0.3) return "rgba(168, 85, 247, 0.32)"; // Moderate negative
  if (r < -0.05) return "rgba(168, 85, 247, 0.15)"; // Weak negative
  return "rgba(148, 163, 184, 0.12)"; // Near zero
}

export default function Statistics() {
  const { studyId } = useParams();
  const navigate = useNavigate();

  const [studies, setStudies] = useState([]);
  const currentStudyId = studyId || "";
  const [scope, setScope] = useState("full_image");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Active section tab
  const [activeSectionTab, setActiveSectionTab] = useState("all");

  // Filter & search state for descriptive statistics table
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Selected metric for distribution view
  const [selectedMetricKey, setSelectedMetricKey] = useState("");

  // PDF export state
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(null);
  const [pdfError, setPdfError] = useState(null);

  // Hovered correlation cell for interactive heatmap
  const [hoveredCell, setHoveredCell] = useState(null);

  // Load studies list
  useEffect(() => {
    getStudies()
      .then((list) => {
        setStudies(list || []);
        if (!studyId && list && list.length > 0) {
          const withAnalyses = list.find((s) => s.analysis_ids && s.analysis_ids.length > 0);
          const chosen = withAnalyses ? withAnalyses.id : list[0].id;
          navigate(`/statistics/${chosen}`, { replace: true });
        }
      })
      .catch(() => {});
  }, [studyId, navigate]);

  // Fetch statistics data
  useEffect(() => {
    if (!studyId) return;
    setLoading(true);
    setError(null);
    setPdfSuccess(null);
    setPdfError(null);

    getStudyStatistics(studyId, scope)
      .then((res) => {
        setData(res);
        if (res?.descriptive_statistics) {
          const keys = Object.keys(res.descriptive_statistics);
          if (keys.length > 0) {
            setSelectedMetricKey((prev) => (prev && keys.includes(prev) ? prev : keys[0]));
          }
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load study statistics.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [studyId, scope]);

  const handleStudyChange = (e) => {
    const nextId = e.target.value;
    if (nextId) {
      navigate(`/statistics/${nextId}`);
    }
  };

  const handleGeneratePdf = async () => {
    if (!studyId) return;
    setPdfLoading(true);
    setPdfError(null);
    setPdfSuccess(null);

    try {
      const res = await generateStatisticsReport(studyId, scope);
      const url = getReportDownloadUrl(res.report_filename);
      setPdfSuccess({
        filename: res.report_filename,
        url: url,
      });
    } catch (err) {
      setPdfError(err.message || "Failed to generate statistics PDF report.");
    } finally {
      setPdfLoading(false);
    }
  };

  const getTrendBadge = (direction) => {
    if (!direction || direction === "insufficient_data") {
      return <span className="cdl-stats-pct-tag zero">Insufficient Data</span>;
    }
    if (direction === "increasing") {
      return <span className="cdl-stats-pct-tag pos">▲ Increasing</span>;
    }
    if (direction === "decreasing") {
      return <span className="cdl-stats-pct-tag neg">▼ Decreasing</span>;
    }
    return <span className="cdl-stats-pct-tag zero">■ Stable</span>;
  };

  // Filtered descriptive statistics list
  const filteredMetrics = useMemo(() => {
    if (!data?.descriptive_statistics) return [];
    return Object.entries(data.descriptive_statistics).filter(([key, item]) => {
      const matchesCategory =
        categoryFilter === "all" || item.category === categoryFilter;
      const matchesSearch =
        !searchQuery ||
        (item.label || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        key.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [data, categoryFilter, searchQuery]);

  // Distribution chart data for the currently selected metric
  const selectedMetric = useMemo(() => {
    if (!data?.descriptive_statistics || !selectedMetricKey) return null;
    return data.descriptive_statistics[selectedMetricKey] || null;
  }, [data, selectedMetricKey]);

  const distributionBarData = useMemo(() => {
    if (!selectedMetric) return [];
    const { min, p25, median, mean, p75, max } = selectedMetric;
    return [
      { name: "Min", value: min, color: "#38bdf8" },
      { name: "Q1 (P25)", value: p25, color: "#0ea5e9" },
      { name: "Median", value: median, color: "#2563eb" },
      { name: "Mean", value: mean, color: "#6366f1" },
      { name: "Q3 (P75)", value: p75, color: "#8b5cf6" },
      { name: "Max", value: max, color: "#a855f7" },
    ].filter((d) => d.value !== null && d.value !== undefined);
  }, [selectedMetric]);

  // Normal approximation density curve over [min, max]
  const distributionCurveData = useMemo(() => {
    if (!selectedMetric || selectedMetric.std === null || selectedMetric.std <= 0) return [];
    const { mean, std, min, max } = selectedMetric;
    if (min === null || max === null || min === max) return [];

    const points = [];
    const start = Math.min(min, mean - 2.5 * std);
    const end = Math.max(max, mean + 2.5 * std);
    const steps = 24;
    const stepSize = (end - start) / steps;

    for (let i = 0; i <= steps; i++) {
      const x = start + i * stepSize;
      const z = (x - mean) / std;
      const density = (1 / (std * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * z * z);
      points.push({
        x: formatNumber(x, 2),
        density: density,
      });
    }
    return points;
  }, [selectedMetric]);

  if (loading) {
    return (
      <div className="cdl-stats-page">
        <div style={{ textAlign: "center", padding: "64px 20px" }}>
          <span className="cdl-stats-spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
          <h3 style={{ marginTop: 16, color: "#475569" }}>Computing Advanced Statistical Analytics...</h3>
          <p style={{ color: "#94a3b8", fontSize: 13 }}>
            Synthesizing parametric moments, Pearson correlation matrices, and 1.5×IQR boundary limits.
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="cdl-stats-page">
        <div className="cdl-stats-banner cdl-stats-banner-error" style={{ margin: "40px auto", maxWidth: 640 }}>
          <div>
            <h4 style={{ margin: "0 0 6px 0", fontSize: 16, fontWeight: 700 }}>Unable to Load Statistical Analytics</h4>
            <p style={{ margin: 0 }}>{error || "Study not found or historical statistical records unavailable."}</p>
          </div>
          <Link to="/studies" className="cdl-stats-btn-secondary" style={{ whiteSpace: "nowrap" }}>
            &larr; Back to Studies
          </Link>
        </div>
      </div>
    );
  }

  const {
    study_title,
    subject_code,
    analysis_count = 0,
    analysis_scope,
    roi_available,
    descriptive_statistics = {},
    change_statistics = {},
    correlations = [],
    correlation_matrix = {},
    outliers = {},
    total_outliers_count = 0,
    quality_summary = {},
    calibration_consistency = {},
    roi_consistency = {},
    warnings = [],
    info = [],
  } = data;

  // Flatten outliers
  const allOutliers = [];
  Object.entries(outliers).forEach(([, oList]) => {
    if (Array.isArray(oList)) {
      oList.forEach((o) => allOutliers.push(o));
    }
  });

  const matrixMetrics = correlation_matrix.metrics || [];
  const matrixValues = correlation_matrix.values || {};

  return (
    <div className="cdl-stats-page">
      {/* 1. Page Header & Breadcrumbs */}
      <div className="cdl-stats-header-wrap">
        <div className="cdl-stats-title-area">
          <div className="cdl-stats-breadcrumb">
            <Link to="/studies" className="bc-link">
              📁 Studies
            </Link>
            <span className="bc-sep">/</span>
            <Link to={`/studies/${studyId}`} className="bc-link">
              {study_title || "Study Workspace"}
            </Link>
            <span className="bc-sep">/</span>
            <Link to={`/longitudinal/${studyId}`} className="bc-link">
              Longitudinal
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Statistics Lab</span>
          </div>

          <div className="cdl-stats-pill-row">
            <span className="cdl-stats-subject-pill">
              🔬 {subject_code ? `Subject: ${subject_code}` : "Research Cohort"}
            </span>
            <span className={`cdl-stats-scope-pill ${analysis_scope === "roi" ? "roi" : "full"}`}>
              {analysis_scope === "roi" ? "Region of Interest (ROI) Analysis" : "Full Image Deformation"}
            </span>
            <span className="cdl-stats-badge cdl-stats-badge-slate">
              {analysis_count} Sessions
            </span>
          </div>

          <h1 className="cdl-stats-title">Statistical Analysis &amp; Research Analytics</h1>
          <p className="cdl-stats-subtitle">
            Quantitative parametric evaluation, inter-metric Pearson correlations, temporal change variance, and 1.5×IQR computational outlier detection.
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="cdl-stats-header-actions">
          {studies.length > 1 && (
            <div className="cdl-stats-switcher-box">
              <label htmlFor="stats-study-select" className="cdl-stats-switcher-label">
                Study:
              </label>
              <select
                id="stats-study-select"
                value={currentStudyId}
                onChange={handleStudyChange}
                className="cdl-stats-select"
              >
                {studies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title} ({s.analysis_ids?.length || 0})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Scope Toggle if ROI exists */}
          {roi_available && (
            <div className="cdl-stats-scope-toggle">
              <button
                type="button"
                className={`cdl-stats-scope-btn ${scope === "full_image" ? "active" : ""}`}
                onClick={() => setScope("full_image")}
              >
                Full Image
              </button>
              <button
                type="button"
                className={`cdl-stats-scope-btn ${scope === "roi" ? "active" : ""}`}
                onClick={() => setScope("roi")}
              >
                ROI Masked
              </button>
            </div>
          )}

          <button
            type="button"
            className="cdl-stats-btn-primary"
            onClick={handleGeneratePdf}
            disabled={pdfLoading || analysis_count === 0}
            title="Generate comprehensive statistics research PDF report"
          >
            {pdfLoading ? (
              <>
                <span className="cdl-stats-spinner" /> Generating...
              </>
            ) : (
              <>📄 Export Statistics PDF</>
            )}
          </button>

          <Link to={`/longitudinal/${studyId}`} className="cdl-stats-btn-secondary" title="View longitudinal trajectory curves">
            📉 Trajectories
          </Link>

          <Link to={`/studies/${studyId}`} className="cdl-stats-btn-secondary" title="Open parent study workspace">
            📁 Workspace
          </Link>
        </div>
      </div>

      {/* PDF Export Notification Banners */}
      {pdfSuccess && (
        <div className="cdl-stats-banner cdl-stats-banner-success">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span>✅</span>
            <div>
              <strong>Statistical Research Report generated successfully.</strong>
              <div style={{ fontSize: 12, opacity: 0.9 }}>File: {pdfSuccess.filename}</div>
            </div>
          </div>
          <a
            href={pdfSuccess.url}
            target="_blank"
            rel="noopener noreferrer"
            className="cdl-stats-download-link"
          >
            📥 Download / View PDF
          </a>
        </div>
      )}

      {pdfError && (
        <div className="cdl-stats-banner cdl-stats-banner-error">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span>⚠️</span>
            <span>{pdfError}</span>
          </div>
        </div>
      )}

      {/* Research Prototype Disclaimer */}
      <div className="cdl-stats-disclaimer-card">
        <span className="cdl-stats-disclaimer-badge">Statistical Notice</span>
        <p className="cdl-stats-disclaimer-text">
          These statistics summarize computational image-derived measurements and should <strong>NOT</strong> be interpreted as clinical findings.
          Evaluations denote mathematical kinematics across discrete analysis sessions and do not imply clinical progression, disease staging, recovery, or therapeutic efficacy.
        </p>
      </div>

      {analysis_count === 0 ? (
        <div className="cdl-stats-empty-card">
          <div className="cdl-stats-empty-icon">📐</div>
          <h3 className="cdl-stats-empty-title">No Analyses Available for Statistical Modeling</h3>
          <p className="cdl-stats-empty-desc">
            Statistical modeling requires at least one completed deformation analysis linked to this study cohort.
          </p>
          <div className="cdl-stats-empty-actions">
            <Link to="/analysis" className="cdl-stats-btn-primary">
              🔬 Run Single Pair Analysis
            </Link>
            <Link to="/temporal" className="cdl-stats-btn-secondary">
              ⏱️ Run Temporal Sequence
            </Link>
            <Link to={`/studies/${studyId}`} className="cdl-stats-btn-secondary">
              📁 Manage Study
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* 2. Top Summary KPI Cards */}
          <div className="cdl-stats-kpi-grid">
            <div className="cdl-stats-kpi-card">
              <div className="cdl-stats-kpi-header">
                <span>Cohort Analyses</span>
                <span className="cdl-stats-kpi-icon">📋</span>
              </div>
              <div className="cdl-stats-kpi-val">{analysis_count}</div>
              <div className="cdl-stats-kpi-sub">
                <span>Sample size (N sessions)</span>
              </div>
            </div>

            <div className="cdl-stats-kpi-card">
              <div className="cdl-stats-kpi-header">
                <span>Standardized Dimensions</span>
                <span className="cdl-stats-kpi-icon">📐</span>
              </div>
              <div className="cdl-stats-kpi-val">{Object.keys(descriptive_statistics).length}</div>
              <div className="cdl-stats-kpi-sub">
                <span>Parametric &amp; non-parametric</span>
              </div>
            </div>

            <div className="cdl-stats-kpi-card">
              <div className="cdl-stats-kpi-header">
                <span>Computational Outliers</span>
                <span className="cdl-stats-kpi-icon">⚠️</span>
              </div>
              <div className="cdl-stats-kpi-val" style={{ color: total_outliers_count > 0 ? "#d97706" : "#059669" }}>
                {total_outliers_count}
              </div>
              <div className="cdl-stats-kpi-sub">
                <span>1.5×IQR boundary rule</span>
              </div>
            </div>

            <div className="cdl-stats-kpi-card">
              <div className="cdl-stats-kpi-header">
                <span>Average Data Quality</span>
                <span className="cdl-stats-kpi-icon">🛡️</span>
              </div>
              <div className="cdl-stats-kpi-val">
                {quality_summary.average_score !== null && quality_summary.average_score !== undefined
                  ? `${quality_summary.average_score}/100`
                  : "Unassessed"}
              </div>
              <div className="cdl-stats-kpi-sub">
                <span className="cdl-stats-tier-chip high">H: {quality_summary.high_count || 0}</span>
                <span className="cdl-stats-tier-chip mod">M: {quality_summary.moderate_count || 0}</span>
                <span className="cdl-stats-tier-chip low">L: {quality_summary.low_count || 0}</span>
              </div>
            </div>

            <div className="cdl-stats-kpi-card">
              <div className="cdl-stats-kpi-header">
                <span>Analysis Scope</span>
                <span className="cdl-stats-kpi-icon">🎯</span>
              </div>
              <div className="cdl-stats-kpi-val" style={{ fontSize: 18 }}>
                {analysis_scope === "roi" ? "ROI Masked" : "Full Frame"}
              </div>
              <div className="cdl-stats-kpi-sub">
                <span>{roi_available ? "ROI masks available" : "Global kinematics only"}</span>
              </div>
            </div>
          </div>

          {/* 3. Internal Navigation / Tabs Strip */}
          <nav className="cdl-stats-nav-strip">
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "all" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("all")}
            >
              All Sections
            </button>
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "descriptive" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("descriptive")}
            >
              Descriptive Stats <span className="cdl-stats-nav-count">{Object.keys(descriptive_statistics).length}</span>
            </button>
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "distributions" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("distributions")}
            >
              Metric Distributions
            </button>
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "correlations" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("correlations")}
            >
              Correlations Matrix <span className="cdl-stats-nav-count">{matrixMetrics.length}×{matrixMetrics.length}</span>
            </button>
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "outliers" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("outliers")}
            >
              Outliers <span className="cdl-stats-nav-count">{total_outliers_count}</span>
            </button>
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "changes" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("changes")}
            >
              Session Changes <span className="cdl-stats-nav-count">{Object.keys(change_statistics).length}</span>
            </button>
            <button
              type="button"
              className={`cdl-stats-nav-btn ${activeSectionTab === "context" ? "active" : ""}`}
              onClick={() => setActiveSectionTab("context")}
            >
              Data Context &amp; QC
            </button>
          </nav>

          {/* 4. Univariate Descriptive Statistics Section */}
          {(activeSectionTab === "all" || activeSectionTab === "descriptive") && (
            <section className="cdl-stats-section">
              <div className="cdl-stats-section-header">
                <div className="cdl-stats-section-title-wrap">
                  <h3 className="cdl-stats-section-title">Univariate Descriptive Statistics</h3>
                  <span className="cdl-stats-badge cdl-stats-badge-blue">Parametric &amp; Non-Parametric</span>
                </div>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  Comprehensive central tendency and dispersion moments across all valid session observations.
                </span>
              </div>

              {/* Filtering and Search Toolbar */}
              <div className="cdl-stats-filter-bar">
                <div className="cdl-stats-chips-row">
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginRight: 4 }}>Filter:</span>
                  {["all", "motion", "strain", "advanced", "temporal", "quality"].map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      className={`cdl-stats-chip ${categoryFilter === cat ? "active" : ""}`}
                      onClick={() => setCategoryFilter(cat)}
                    >
                      {cat === "all"
                        ? "All Categories"
                        : cat.charAt(0).toUpperCase() + cat.slice(1)}
                    </button>
                  ))}
                </div>

                <input
                  type="text"
                  placeholder="Search metrics..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="cdl-stats-search-input"
                />
              </div>

              <div className="cdl-stats-table-box">
                <table className="cdl-stats-table">
                  <thead>
                    <tr>
                      <th>Metric Dimension</th>
                      <th>Category</th>
                      <th>N</th>
                      <th>Mean</th>
                      <th>Median</th>
                      <th>Std Dev (σ)</th>
                      <th>Min</th>
                      <th>Max</th>
                      <th>Q1 (P25)</th>
                      <th>Q3 (P75)</th>
                      <th>IQR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMetrics.map(([key, item]) => {
                      const u = item.unit ? ` ${item.unit}` : "";
                      return (
                        <tr key={key}>
                          <td>
                            <div className="cdl-stats-cell-metric">
                              <span className="cdl-stats-cell-label">{item.label}</span>
                              {item.unit && <span className="cdl-stats-cell-unit">{item.unit}</span>}
                            </div>
                          </td>
                          <td>
                            <span className="cdl-stats-badge cdl-stats-badge-slate" style={{ fontSize: 10 }}>
                              {item.category || "General"}
                            </span>
                          </td>
                          <td className="cdl-stats-num">{item.count}</td>
                          <td className="cdl-stats-num">
                            <strong>{formatNumber(item.mean)}</strong>
                            {item.mean !== null ? u : ""}
                          </td>
                          <td className="cdl-stats-num">
                            {formatNumber(item.median)}
                            {item.median !== null ? u : ""}
                          </td>
                          <td className="cdl-stats-num">{formatNumber(item.std)}</td>
                          <td className="cdl-stats-num">{formatNumber(item.min)}</td>
                          <td className="cdl-stats-num">{formatNumber(item.max)}</td>
                          <td className="cdl-stats-num">{formatNumber(item.p25)}</td>
                          <td className="cdl-stats-num">{formatNumber(item.p75)}</td>
                          <td className="cdl-stats-num">{formatNumber(item.iqr)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* 5. Metric Distribution Analysis (Box Plot / Quantile Visualization) */}
          {(activeSectionTab === "all" || activeSectionTab === "distributions") && (
            <section className="cdl-stats-section">
              <div className="cdl-stats-section-header">
                <div className="cdl-stats-section-title-wrap">
                  <h3 className="cdl-stats-section-title">Metric Distribution &amp; Quantile Analysis</h3>
                  <span className="cdl-stats-badge cdl-stats-badge-purple">Dispersion Profile</span>
                </div>
                <div className="cdl-stats-dist-select-box">
                  <label htmlFor="metric-distribution-select" style={{ fontSize: 12, fontWeight: 600, color: "#64748b" }}>
                    Select Metric:
                  </label>
                  <select
                    id="metric-distribution-select"
                    value={selectedMetricKey}
                    onChange={(e) => setSelectedMetricKey(e.target.value)}
                    className="cdl-stats-dist-select"
                  >
                    {Object.entries(descriptive_statistics).map(([key, item]) => (
                      <option key={key} value={key}>
                        {item.label} {item.unit ? `(${item.unit})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {selectedMetric && (
                <div className="cdl-stats-dist-card">
                  {/* Five-Number Summary Strip */}
                  <div className="cdl-stats-5num-strip">
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Minimum</span>
                      <span className="item-val">{formatNumber(selectedMetric.min)}</span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Q1 (P25)</span>
                      <span className="item-val">{formatNumber(selectedMetric.p25)}</span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Median</span>
                      <span className="item-val" style={{ color: "#2563eb" }}>
                        {formatNumber(selectedMetric.median)}
                      </span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Mean (μ)</span>
                      <span className="item-val" style={{ color: "#7c3aed" }}>
                        {formatNumber(selectedMetric.mean)}
                      </span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Q3 (P75)</span>
                      <span className="item-val">{formatNumber(selectedMetric.p75)}</span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Maximum</span>
                      <span className="item-val">{formatNumber(selectedMetric.max)}</span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">IQR</span>
                      <span className="item-val">{formatNumber(selectedMetric.iqr)}</span>
                    </div>
                    <div className="cdl-stats-5num-item">
                      <span className="item-label">Std Dev (σ)</span>
                      <span className="item-val">{formatNumber(selectedMetric.std)}</span>
                    </div>
                  </div>

                  {/* Distribution Charts: Quantile Bars & Normal PDF Density Curve */}
                  <div style={{ display: "grid", gridTemplateColumns: distributionCurveData.length > 0 ? "repeat(auto-fit, minmax(320px, 1fr))" : "1fr", gap: 16 }}>
                    <div className="cdl-stats-chart-canvas-box">
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8, display: "block" }}>
                        Quantile Dispersion Bar Profile
                      </span>
                      <ResponsiveContainer width="100%" height={180}>
                        <BarChart data={distributionBarData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                          <YAxis stroke="#64748b" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                          <Tooltip
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                const p = payload[0];
                                return (
                                  <div style={{ background: "#0f172a", border: "1px solid #334155", padding: "6px 10px", borderRadius: 6, fontSize: 12, color: "#ffffff" }}>
                                    <strong>{p.payload.name}:</strong> {formatNumber(p.value)} {selectedMetric.unit}
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                            {distributionBarData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {distributionCurveData.length > 0 && (
                      <div className="cdl-stats-chart-canvas-box">
                        <span style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8, display: "block" }}>
                          Gaussian Parametric Density Curve N(μ={formatNumber(selectedMetric.mean, 2)}, σ={formatNumber(selectedMetric.std, 2)})
                        </span>
                        <ResponsiveContainer width="100%" height={180}>
                          <LineChart data={distributionCurveData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                            <XAxis dataKey="x" stroke="#64748b" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                            <YAxis stroke="#64748b" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                            <Tooltip
                              content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                  const p = payload[0];
                                  return (
                                    <div style={{ background: "#0f172a", border: "1px solid #334155", padding: "6px 10px", borderRadius: 6, fontSize: 12, color: "#38bdf8" }}>
                                      x = {p.payload.x} | Density: {p.value.toFixed(4)}
                                    </div>
                                  );
                                }
                                return null;
                              }}
                            />
                            <Line type="monotone" dataKey="density" stroke="#38bdf8" strokeWidth={2.5} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </section>
          )}

          {/* 6. Metric Relationship Matrix (Correlation Analysis) */}
          {(activeSectionTab === "all" || activeSectionTab === "correlations") && (
            <section className="cdl-stats-section">
              <div className="cdl-stats-section-header">
                <div className="cdl-stats-section-title-wrap">
                  <h3 className="cdl-stats-section-title">Metric Relationship Matrix (Pearson r)</h3>
                  <span className="cdl-stats-badge cdl-stats-badge-purple">Bivariate Linear Associations</span>
                </div>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  Correlation describes statistical association only and does <strong>not</strong> imply causation.
                </span>
              </div>

              {matrixMetrics.length < 2 ? (
                <div className="cdl-stats-empty-card" style={{ padding: 24, margin: "10px 0" }}>
                  <span style={{ fontSize: 24 }}>📐</span>
                  <h4 style={{ margin: 0, fontSize: 14 }}>Insufficient Paired Observations for Correlation Matrix</h4>
                  <p style={{ margin: 0, fontSize: 12.5, color: "#64748b" }}>
                    Generating a Pearson r correlation matrix requires at least 3 analysis sessions with valid paired dimensions.
                  </p>
                </div>
              ) : (
                <div className="cdl-stats-heatmap-box">
                  {/* Heatmap Legend */}
                  <div className="cdl-stats-heatmap-legend">
                    <span>Negative (-1.0)</span>
                    <div className="cdl-stats-legend-grad" />
                    <span>Positive (+1.0)</span>
                  </div>

                  {/* Heatmap Grid */}
                  <div className="cdl-stats-heatmap-scroll">
                    <table className="cdl-stats-heatmap-table">
                      <thead>
                        <tr>
                          <th className="cdl-stats-heatmap-corner">Metric Dimension</th>
                          {matrixMetrics.map((m) => (
                            <th key={m.key} className="cdl-stats-heatmap-col-th" title={m.label}>
                              {m.label.length > 15 ? `${m.label.slice(0, 13)}…` : m.label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {matrixMetrics.map((rowM) => (
                          <tr key={rowM.key}>
                            <th className="cdl-stats-heatmap-row-th" title={rowM.label}>
                              {rowM.label}
                            </th>
                            {matrixMetrics.map((colM) => {
                              const rVal = matrixValues[rowM.key]?.[colM.key];
                              const isSelf = rowM.key === colM.key;
                              const bgColor = isSelf ? "rgba(100, 116, 139, 0.12)" : getCorrelationColor(rVal);

                              return (
                                <td
                                  key={colM.key}
                                  className={`cdl-stats-heatmap-cell ${isSelf ? "self" : ""}`}
                                  style={{ backgroundColor: bgColor }}
                                  onMouseEnter={() =>
                                    setHoveredCell({
                                      metricX: rowM.label,
                                      metricY: colM.label,
                                      r: rVal,
                                    })
                                  }
                                  onMouseLeave={() => setHoveredCell(null)}
                                >
                                  {rVal !== null && rVal !== undefined
                                    ? isSelf
                                      ? "1.00"
                                      : rVal.toFixed(2)
                                    : "—"}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {hoveredCell && (
                    <div className="cdl-stats-heatmap-active-pill">
                      <strong>{hoveredCell.metricX}</strong> vs <strong>{hoveredCell.metricY}</strong>:{" "}
                      <span style={{ color: hoveredCell.r >= 0 ? "#38bdf8" : "#c084fc", fontWeight: 700 }}>
                        Pearson r = {hoveredCell.r !== null && hoveredCell.r !== undefined ? hoveredCell.r.toFixed(4) : "N/A"}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Observed Correlation Rankings Table */}
              {correlations.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 10px 0", color: "#0f172a" }}>
                    Strongest Observed Metric Correlations
                  </h4>
                  <div className="cdl-stats-table-box">
                    <table className="cdl-stats-table">
                      <thead>
                        <tr>
                          <th>Metric Dimension A</th>
                          <th>Metric Dimension B</th>
                          <th>Pearson Correlation (r)</th>
                          <th>Paired Sessions (N)</th>
                          <th>Statistical Association</th>
                        </tr>
                      </thead>
                      <tbody>
                        {correlations.map((pair, idx) => (
                          <tr key={idx}>
                            <td><strong>{pair.label_x}</strong></td>
                            <td><strong>{pair.label_y}</strong></td>
                            <td>
                              <span
                                className={`cdl-stats-corr-pill ${
                                  pair.correlation > 0.3
                                    ? "pos"
                                    : pair.correlation < -0.3
                                    ? "neg"
                                    : "neutral"
                                }`}
                              >
                                {pair.correlation > 0 ? "+" : ""}{pair.correlation}
                              </span>
                            </td>
                            <td className="cdl-stats-num">{pair.observation_count}</td>
                            <td>
                              {pair.association === "positive"
                                ? "Positive Linear Association"
                                : pair.association === "negative"
                                ? "Negative Linear Association"
                                : "Near-Zero Linear Association"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* 7. Computational Outlier Detection Section */}
          {(activeSectionTab === "all" || activeSectionTab === "outliers") && (
            <section className="cdl-stats-section">
              <div className="cdl-stats-section-header">
                <div className="cdl-stats-section-title-wrap">
                  <h3 className="cdl-stats-section-title">Computational Outlier Detection</h3>
                  <span className={`cdl-stats-badge ${total_outliers_count > 0 ? "cdl-stats-badge-amber" : "cdl-stats-badge-emerald"}`}>
                    {total_outliers_count} Flagged (1.5×IQR Rule)
                  </span>
                </div>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  Bounds defined by [Q1 - 1.5×IQR, Q3 + 1.5×IQR]. Outliers reflect mathematical dispersion and are not auto-excluded.
                </span>
              </div>

              {allOutliers.length === 0 ? (
                <div className="cdl-stats-outlier-clean">
                  <span style={{ fontSize: 28 }}>✅</span>
                  <div>
                    <h4 style={{ margin: "0 0 4px 0", fontSize: 14, color: "#065f46" }}>
                      No Computational Statistical Outliers Detected
                    </h4>
                    <p style={{ margin: 0, fontSize: 12.5, color: "#047857" }}>
                      All observed deformation dimensions lie strictly within the standard [Q1 - 1.5×IQR, Q3 + 1.5×IQR] parametric bounds (or sample size N &lt; 4).
                    </p>
                  </div>
                </div>
              ) : (
                <div className="cdl-stats-table-box">
                  <table className="cdl-stats-table">
                    <thead>
                      <tr>
                        <th>Session / Date</th>
                        <th>Metric Dimension</th>
                        <th>Observed Outlier Value</th>
                        <th>Expected Range [Lower, Upper]</th>
                        <th>Quality Context</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allOutliers.map((o, idx) => (
                        <tr key={idx}>
                          <td>
                            <strong>Session #{o.session_number}</strong>
                            <div style={{ fontSize: 11, color: "#64748b" }}>{formatDate(o.timestamp)}</div>
                          </td>
                          <td><strong>{o.metric_label}</strong></td>
                          <td>
                            <span className="cdl-stats-outlier-val">
                              {formatNumber(o.value)} {o.unit}
                            </span>
                          </td>
                          <td className="cdl-stats-num">
                            [{formatNumber(o.lower_bound)}, {formatNumber(o.upper_bound)}]
                          </td>
                          <td>
                            {o.qc_level && o.qc_level !== "High" ? (
                              <span className="cdl-stats-badge cdl-stats-badge-amber" title={o.quality_context}>
                                ⚠️ {o.qc_level} QC ({o.qc_score}/100)
                              </span>
                            ) : (
                              <span className="cdl-stats-badge cdl-stats-badge-slate">Standard QC</span>
                            )}
                            <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
                              {o.quality_context}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          {/* 8. Measurement Change Analysis Section (Session-to-Session Changes) */}
          {(activeSectionTab === "all" || activeSectionTab === "changes") && (
            <section className="cdl-stats-section">
              <div className="cdl-stats-section-header">
                <div className="cdl-stats-section-title-wrap">
                  <h3 className="cdl-stats-section-title">Session-to-Session Measurement Change</h3>
                  <span className="cdl-stats-badge cdl-stats-badge-blue">Progression Variance</span>
                </div>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  Baseline vs. terminal variation, consecutive absolute deltas, and Cohen-style standardized computational differences (d).
                </span>
              </div>

              <div className="cdl-stats-table-box">
                <table className="cdl-stats-table">
                  <thead>
                    <tr>
                      <th>Metric Dimension</th>
                      <th>First (Baseline)</th>
                      <th>Latest Session</th>
                      <th>Absolute Delta (Δ)</th>
                      <th>Percentage Change</th>
                      <th>Mean Consec Δ</th>
                      <th>Std Difference (d)</th>
                      <th>Trajectory Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(change_statistics).map(([key, item]) => {
                      const u = item.unit ? ` ${item.unit}` : "";
                      return (
                        <tr key={key}>
                          <td>
                            <strong className="cdl-stats-cell-label">{item.label}</strong>
                          </td>
                          <td className="cdl-stats-num">
                            {formatNumber(item.first_value)}
                            {item.first_value !== null ? u : ""}
                          </td>
                          <td className="cdl-stats-num">
                            {formatNumber(item.latest_value)}
                            {item.latest_value !== null ? u : ""}
                          </td>
                          <td className="cdl-stats-cell-delta">
                            {formatNumber(item.absolute_change)}
                            {item.absolute_change !== null ? u : ""}
                          </td>
                          <td>
                            {item.percentage_change !== null && item.percentage_change !== undefined ? (
                              <span
                                className={`cdl-stats-pct-tag ${
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
                          <td className="cdl-stats-num">{formatNumber(item.mean_consecutive_change)}</td>
                          <td className="cdl-stats-num">
                            {item.standardized_difference !== null && item.standardized_difference !== undefined ? (
                              <span className="cdl-stats-badge cdl-stats-badge-purple">
                                {item.standardized_difference > 0 ? "+" : ""}{item.standardized_difference}
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>{getTrendBadge(item.trend_direction)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* 9. Data Quality & Spatial Consistency Context */}
          {(activeSectionTab === "all" || activeSectionTab === "context") && (
            <div className="cdl-stats-context-grid">
              {/* Quality Distribution Card */}
              <div className="cdl-stats-context-card">
                <div className="cdl-stats-card-top-row">
                  <h4 className="cdl-stats-card-top-title">Quality Control Distribution</h4>
                  <span className="cdl-stats-badge cdl-stats-badge-blue">Validation Layer</span>
                </div>
                <div className="cdl-stats-qc-metrics-row">
                  <div className="cdl-stats-qc-stat-item">
                    <span className="cdl-stats-qc-stat-label">Average Score</span>
                    <span className="cdl-stats-qc-stat-num">
                      {quality_summary.average_score !== null && quality_summary.average_score !== undefined
                        ? `${quality_summary.average_score}`
                        : "—"}
                    </span>
                  </div>
                  <div className="cdl-stats-qc-stat-item">
                    <span className="cdl-stats-qc-stat-label">Range [Min, Max]</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#334155" }}>
                      {quality_summary.min_score ?? "—"} / {quality_summary.max_score ?? "—"}
                    </span>
                  </div>
                  <div className="cdl-stats-qc-stat-item">
                    <span className="cdl-stats-qc-stat-label">Tiers</span>
                    <div style={{ display: "flex", gap: 4 }}>
                      <span className="cdl-stats-tier-chip high">H: {quality_summary.high_count || 0}</span>
                      <span className="cdl-stats-tier-chip mod">M: {quality_summary.moderate_count || 0}</span>
                      <span className="cdl-stats-tier-chip low">L: {quality_summary.low_count || 0}</span>
                    </div>
                  </div>
                </div>
                {quality_summary.unassessed_count > 0 && (
                  <span className="cdl-stats-context-sub" style={{ color: "#d97706" }}>
                    ⚠️ {quality_summary.unassessed_count} session(s) pending automated quality evaluation.
                  </span>
                )}
              </div>

              {/* Spatial Calibration Consistency */}
              <div className="cdl-stats-context-card">
                <div className="cdl-stats-card-top-row">
                  <h4 className="cdl-stats-card-top-title">Spatial Calibration Consistency</h4>
                  <span
                    className={`cdl-stats-badge ${
                      calibration_consistency.status === "consistent"
                        ? "cdl-stats-badge-emerald"
                        : calibration_consistency.status === "mixed"
                        ? "cdl-stats-badge-purple"
                        : "cdl-stats-badge-slate"
                    }`}
                  >
                    {calibration_consistency.status?.toUpperCase() || "UNCALIBRATED"}
                  </span>
                </div>
                <p className="cdl-stats-context-desc">{calibration_consistency.details || "No calibration metadata available."}</p>
                <div className="cdl-stats-context-sub">
                  {calibration_consistency.status === "uncalibrated"
                    ? "All displacement statistics evaluate in image-space pixels."
                    : `${calibration_consistency.calibrated_count || 0} of ${calibration_consistency.total_count || 0} sessions calibrated to physical units.`}
                </div>
              </div>

              {/* ROI Scope Consistency */}
              <div className="cdl-stats-context-card">
                <div className="cdl-stats-card-top-row">
                  <h4 className="cdl-stats-card-top-title">Region of Interest (ROI) Scope</h4>
                  <span
                    className={`cdl-stats-badge ${
                      roi_consistency.status === "consistent"
                        ? "cdl-stats-badge-emerald"
                        : roi_consistency.status === "mixed"
                        ? "cdl-stats-badge-purple"
                        : "cdl-stats-badge-slate"
                    }`}
                  >
                    {roi_consistency.status?.toUpperCase() || "FULL-FRAME"}
                  </span>
                </div>
                <p className="cdl-stats-context-desc">{roi_consistency.details || "Full-image deformation evaluated across study sessions."}</p>
                <div className="cdl-stats-context-sub">
                  {roi_consistency.roi_count === 0
                    ? "Full-frame deformation evaluated across all sessions."
                    : `${roi_consistency.roi_count || 0} of ${roi_consistency.total_count || 0} sessions utilized anatomical ROI masks.`}
                </div>
              </div>
            </div>
          )}

          {/* 10. Study Warnings & Information Notices */}
          {(warnings.length > 0 || info.length > 0) && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {warnings.map((w, i) => (
                <div key={i} className="cdl-stats-banner cdl-stats-banner-warning">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span>⚠️</span>
                    <span>{w}</span>
                  </div>
                </div>
              ))}
              {info.map((inf, i) => (
                <div key={i} className="cdl-stats-banner cdl-stats-banner-info">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span>ℹ️</span>
                    <span>{inf}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
