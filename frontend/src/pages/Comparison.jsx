import { useState, useEffect, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  getAnalysisHistory,
  getStudies,
  compareAnalyses,
  saveComparison,
  generateComparisonReport,
  getReportDownloadUrl,
} from "../services/api";
import FingerprintComparisonChart from "../components/FingerprintComparisonChart";
import MetricComparisonCharts from "../components/MetricComparisonCharts";
import MapComparisonView from "../components/MapComparisonView";
import SaveComparisonModal from "../components/SaveComparisonModal";
import SavedComparisonsDrawer from "../components/SavedComparisonsDrawer";
import "./Comparison.css";

function formatVal(val, decimals = 4) {
  if (val === null || val === undefined) return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return val.toExponential(decimals);
  }
  return val.toFixed(decimals);
}

export default function Comparison() {
  const location = useLocation();

  const [historyList, setHistoryList] = useState([]);
  const [studies, setStudies] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState(null);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [activeCategoryTab, setActiveCategoryTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all"); // "all" | "single_pair" | "temporal"

  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [savingComp, setSavingComp] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState(null);

  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportUrl, setReportUrl] = useState(null);

  // Load history and studies
  useEffect(() => {
    setLoadingHistory(true);
    Promise.all([getAnalysisHistory(), getStudies()])
      .then(([historyData, studiesData]) => {
        setHistoryList(historyData || []);
        setStudies(studiesData || []);

        // If navigated here with a primaryId in location state, pre-select it
        const incomingId = location?.state?.primaryId;
        if (incomingId && historyData?.some((r) => r.id === incomingId)) {
          setSelectedIds([incomingId]);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load analysis history.");
      })
      .finally(() => {
        setLoadingHistory(false);
      });
  }, [location?.state?.primaryId]);

  // Find study for an analysis ID
  const getStudyName = (analysisId) => {
    for (const s of studies) {
      if (s.analysis_ids && s.analysis_ids.includes(analysisId)) {
        return s.title;
      }
    }
    return null;
  };

  const handleToggleSelect = (id) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 5) {
        alert("Comparison supports a maximum of 5 analyses concurrently.");
        return prev;
      }
      return [...prev, id];
    });
  };

  const handleRunComparison = async () => {
    if (selectedIds.length < 2) {
      setError("Please select at least 2 analyses to execute comparison.");
      return;
    }
    setComparing(true);
    setError(null);
    setReportUrl(null);
    setSaveSuccessMsg(null);

    try {
      const data = await compareAnalyses(selectedIds);
      setComparisonResult(data);
      // Smooth scroll to comparison results
      setTimeout(() => {
        const resEl = document.getElementById("comparison-results-anchor");
        if (resEl) resEl.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err) {
      setError(err.message || "Failed to execute analysis comparison.");
    } finally {
      setComparing(false);
    }
  };

  const handleSaveComparison = async ({ title, notes }) => {
    if (!comparisonResult) return;
    setSavingComp(true);
    try {
      await saveComparison({
        analysis_ids: comparisonResult.analysis_ids,
        title,
        notes,
        comparison: comparisonResult,
      });
      setIsSaveModalOpen(false);
      setSaveSuccessMsg("Comparison record saved successfully to history!");
      setTimeout(() => setSaveSuccessMsg(null), 4000);
    } catch (err) {
      alert(`Failed to save comparison: ${err.message}`);
    } finally {
      setSavingComp(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!comparisonResult) return;
    setGeneratingReport(true);
    setError(null);
    try {
      const res = await generateComparisonReport({
        analysis_ids: comparisonResult.analysis_ids,
        comparison: comparisonResult,
        title: "Multi-Analysis Comparison Report",
      });
      const downloadUrl = getReportDownloadUrl(res.url);
      setReportUrl(downloadUrl);
    } catch (err) {
      setError(err.message || "Failed to generate comparison report.");
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleLoadSaved = (savedRecord) => {
    if (savedRecord.comparison) {
      setComparisonResult(savedRecord.comparison);
      setSelectedIds(savedRecord.analysis_ids || []);
      setReportUrl(null);
      setSaveSuccessMsg(`Loaded saved comparison: "${savedRecord.title}"`);
      setTimeout(() => setSaveSuccessMsg(null), 4000);
    }
  };

  const isTwoAnalyses = comparisonResult && comparisonResult.analysis_count === 2;

  // Filter comparison table by category
  const filteredRows = comparisonResult?.comparison_table?.filter((r) => {
    if (activeCategoryTab === "all") return true;
    return r.category_key === activeCategoryTab;
  }) || [];

  // Filter available analyses in selector
  const filteredHistory = useMemo(() => {
    return historyList.filter((item) => {
      if (typeFilter === "single_pair" && item.type === "temporal") return false;
      if (typeFilter === "temporal" && item.type !== "temporal") return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const idMatch = item.id?.toLowerCase().includes(q);
        const studyName = getStudyName(item.id)?.toLowerCase() || "";
        const studyMatch = studyName.includes(q);
        return idMatch || studyMatch;
      }
      return true;
    });
  }, [historyList, searchQuery, typeFilter]);

  // Compute average QC score of selected analyses if available
  const avgQcScore = useMemo(() => {
    if (!comparisonResult?.analyses) return null;
    const scores = comparisonResult.analyses
      .map((a) => a.metadata?.quality_control?.score)
      .filter((s) => typeof s === "number");
    if (!scores.length) return null;
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  }, [comparisonResult]);

  return (
    <div className="cdl-comparison-page">
      {/* ====================================================================
          1. PAGE HEADER & ACTIONS
          ==================================================================== */}
      <div className="cdl-comp-header-wrap">
        <div>
          <div className="cdl-comp-breadcrumb">
            <Link to="/" className="bc-home">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              Research
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Analysis Comparison</span>
          </div>
          <h2 className="cdl-comp-title">Analysis Comparison</h2>
          <p className="cdl-comp-subtitle">
            Quantitative multi-session evaluation — parametric metric variances, spatial deformation fields, and 10-D radar signatures across 2 to 5 cardiac deformation evaluations.
          </p>
        </div>

        <div className="cdl-comp-header-actions">
          <button
            type="button"
            className="cdl-comp-btn cdl-comp-btn-secondary"
            onClick={() => setIsDrawerOpen(true)}
            title="Browse and load saved comparison sessions"
          >
            📁 Saved Comparisons
          </button>

          {comparisonResult && (
            <>
              <button
                type="button"
                className="cdl-comp-btn cdl-comp-btn-secondary"
                onClick={() => setIsSaveModalOpen(true)}
                title="Save current comparison session"
              >
                💾 Save Comparison
              </button>

              {reportUrl ? (
                <a
                  href={reportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cdl-comp-btn cdl-comp-btn-primary"
                  title="Open generated PDF report in new tab"
                >
                  📄 Open PDF Report
                </a>
              ) : (
                <button
                  type="button"
                  className="cdl-comp-btn cdl-comp-btn-primary"
                  onClick={handleGenerateReport}
                  disabled={generatingReport}
                  title="Generate publication-grade PDF comparison summary"
                >
                  {generatingReport ? (
                    <>
                      <span className="spinner"></span> Generating PDF...
                    </>
                  ) : (
                    "📄 Export PDF Report"
                  )}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Notifications */}
      {saveSuccessMsg && (
        <div className="status-banner success" style={{ margin: "0" }}>
          {saveSuccessMsg}
        </div>
      )}

      {error && (
        <div className="status-banner error" style={{ margin: "0" }}>
          <strong>Notice:</strong> {error}
        </div>
      )}

      {/* ====================================================================
          2. SUMMARY KPI STRIP
          ==================================================================== */}
      <div className="cdl-comp-summary-strip">
        <div className="cdl-comp-kpi-card kpi-blue">
          <div className="cdl-comp-kpi-header">
            <span className="cdl-comp-kpi-label">Selected Cohort</span>
            <span className="cdl-comp-kpi-icon">📊</span>
          </div>
          <div className="cdl-comp-kpi-val">
            {selectedIds.length} <span style={{ fontSize: "14px", color: "#64748b" }}>/ 5</span>
          </div>
          <span className="cdl-comp-kpi-sub">
            {selectedIds.length >= 2 ? "Ready for comparison" : "Select at least 2 sessions"}
          </span>
        </div>

        <div className="cdl-comp-kpi-card kpi-cyan">
          <div className="cdl-comp-kpi-header">
            <span className="cdl-comp-kpi-label">Comparison Status</span>
            <span className="cdl-comp-kpi-icon">⚖️</span>
          </div>
          <div className="cdl-comp-kpi-val" style={{ fontSize: "18px" }}>
            {comparisonResult ? `${comparisonResult.analysis_count} Evaluated` : "Idle"}
          </div>
          <span className="cdl-comp-kpi-sub">
            {comparisonResult ? "Active side-by-side matrices" : "Awaiting execution"}
          </span>
        </div>

        <div className="cdl-comp-kpi-card kpi-purple">
          <div className="cdl-comp-kpi-header">
            <span className="cdl-comp-kpi-label">Study Context</span>
            <span className="cdl-comp-kpi-icon">📁</span>
          </div>
          <div className="cdl-comp-kpi-val" style={{ fontSize: "16px" }}>
            {comparisonResult?.study_context?.badge || "Cross-Session"}
          </div>
          <span className="cdl-comp-kpi-sub">
            {comparisonResult?.study_context?.message || "Select analyses to inspect cohort"}
          </span>
        </div>

        <div className="cdl-comp-kpi-card kpi-emerald">
          <div className="cdl-comp-kpi-header">
            <span className="cdl-comp-kpi-label">Average Quality</span>
            <span className="cdl-comp-kpi-icon">🛡️</span>
          </div>
          <div className="cdl-comp-kpi-val">
            {avgQcScore !== null ? `${avgQcScore} / 100` : "N/A"}
          </div>
          <span className="cdl-comp-kpi-sub">
            {avgQcScore !== null ? "Mean algorithmic fidelity" : "Evaluated post-comparison"}
          </span>
        </div>
      </div>

      {/* ====================================================================
          3. ANALYSIS SELECTION WORKSPACE
          ==================================================================== */}
      <section className="cdl-comp-selector-section">
        <div className="cdl-comp-selector-header">
          <div>
            <h3 className="cdl-comp-selector-title">
              🔬 Select Analyses to Compare
            </h3>
            <p className="cdl-comp-selector-sub">
              Choose 2 to 5 evaluations from your repository to inspect quantitative divergences ({selectedIds.length} selected).
            </p>
          </div>

          <div className="cdl-comp-selector-actions">
            {/* Live Filter Controls */}
            <input
              type="text"
              placeholder="🔍 Search study or UUID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="cdl-history-search-input"
              style={{ width: "200px" }}
            />

            <div className="cdl-comp-filter-tabs">
              <button
                type="button"
                className={`cdl-comp-tab-btn ${typeFilter === "all" ? "active" : ""}`}
                onClick={() => setTypeFilter("all")}
              >
                All ({historyList.length})
              </button>
              <button
                type="button"
                className={`cdl-comp-tab-btn ${typeFilter === "single_pair" ? "active" : ""}`}
                onClick={() => setTypeFilter("single_pair")}
              >
                Single-Pair
              </button>
              <button
                type="button"
                className={`cdl-comp-tab-btn ${typeFilter === "temporal" ? "active" : ""}`}
                onClick={() => setTypeFilter("temporal")}
              >
                Temporal
              </button>
            </div>

            {selectedIds.length > 0 && (
              <button
                type="button"
                className="cdl-comp-btn cdl-comp-btn-secondary"
                onClick={() => setSelectedIds([])}
              >
                Clear Selection
              </button>
            )}

            <button
              type="button"
              className="cdl-comp-btn cdl-comp-btn-primary"
              onClick={handleRunComparison}
              disabled={selectedIds.length < 2 || comparing}
            >
              {comparing ? (
                <>
                  <span className="spinner"></span> Comparing...
                </>
              ) : (
                `Compare ${selectedIds.length} Analyses`
              )}
            </button>
          </div>
        </div>

        {/* Selection Status Message */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
          <div className="cdl-comp-status-badge">
            {selectedIds.length === 0 && "Select 2–5 analyses to begin comparison"}
            {selectedIds.length === 1 && "1 analysis selected. Select at least one more analysis."}
            {selectedIds.length >= 2 && `Ready to compare (${selectedIds.length} analyses selected)`}
          </div>
        </div>

        {loadingHistory && (
          <div className="status-banner loading">
            <span className="spinner"></span> Synchronizing analysis records from backend repository...
          </div>
        )}

        {!loadingHistory && historyList.length === 0 && (
          <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>
            <span style={{ fontSize: "36px" }}>📊</span>
            <h4 style={{ margin: "12px 0 4px", color: "#0f172a" }}>No analyses recorded yet</h4>
            <p style={{ margin: 0, fontSize: "13px" }}>Execute Single-Pair or Temporal analysis first to build comparison cohorts.</p>
          </div>
        )}

        {/* Analysis Cards Grid */}
        {!loadingHistory && filteredHistory.length > 0 && (
          <div className="cdl-comp-cards-grid">
            {filteredHistory.map((rec) => {
              const isSelected = selectedIds.includes(rec.id);
              const summary = rec.summary || {};
              const studyName = getStudyName(rec.id);
              const isTemporal = rec.type === "temporal";
              const qcObj = summary.quality_control;

              return (
                <div
                  key={rec.id}
                  className={`cdl-comp-card ${isSelected ? "selected" : ""}`}
                  onClick={() => handleToggleSelect(rec.id)}
                >
                  <div className="cdl-comp-card-top">
                    <input
                      type="checkbox"
                      className="cdl-comp-checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span className="cdl-comp-card-type">
                      {isTemporal ? "⏱️ Temporal" : "🔬 Single-Pair"}
                    </span>
                    <span className="cdl-comp-card-time">
                      {new Date(rec.timestamp).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="cdl-comp-card-id">
                    <span>UUID:</span>
                    <code>{rec.id.slice(0, 8)}...</code>
                  </div>

                  {studyName ? (
                    <span className="cdl-comp-card-study">
                      📁 {studyName}
                    </span>
                  ) : (
                    <span className="cdl-comp-tag">Independent</span>
                  )}

                  <div className="cdl-comp-tags-row">
                    {summary.roi?.enabled ? (
                      <span className="cdl-comp-tag roi">
                        ROI: {summary.roi.type || "Custom"} ({summary.roi.mode || "fixed"})
                      </span>
                    ) : (
                      <span className="cdl-comp-tag">Full Image</span>
                    )}

                    {summary.calibration?.enabled ? (
                      <span className="cdl-comp-tag cal">
                        {summary.calibration.pixel_spacing_x} {summary.calibration.unit}/px
                      </span>
                    ) : (
                      <span className="cdl-comp-tag">Pixels</span>
                    )}

                    {qcObj ? (
                      <span
                        className={`cdl-comp-tag ${
                          qcObj.level === "High" ? "qc-high" : qcObj.level === "Moderate" ? "qc-mod" : "qc-low"
                        }`}
                        title={`Computational Quality: ${qcObj.score}/100`}
                      >
                        QC: {qcObj.score} ({qcObj.level})
                      </span>
                    ) : (
                      <span className="cdl-comp-tag">QC: N/A</span>
                    )}
                  </div>

                  {/* Quick Metric Values */}
                  <div className="cdl-comp-km-grid">
                    <div className="cdl-comp-km-item">
                      <span className="cdl-comp-km-label">Mean Disp</span>
                      <span className="cdl-comp-km-val">
                        {formatVal(summary.mean_displacement, 2)} px
                      </span>
                    </div>
                    <div className="cdl-comp-km-item">
                      <span className="cdl-comp-km-label">Mean Strain</span>
                      <span className="cdl-comp-km-val">
                        {formatVal(summary.mean_principal_strain, 3)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Anchor for automatic smooth scrolling */}
      <div id="comparison-results-anchor" />

      {/* ====================================================================
          4. COMPARISON RESULTS SECTION
          ==================================================================== */}
      {comparisonResult && (
        <>
          {/* Compatibility & Cohort Header */}
          <section className="cdl-comp-compat-card">
            <div className="cdl-comp-compat-header">
              <div>
                <h3 className="cdl-comp-selector-title">
                  ⚖️ Comparison Summary &amp; Compatibility
                </h3>
                <p className="cdl-comp-selector-sub">
                  Evaluated {comparisonResult.analysis_count} analyses across technical consistency and spatial scaling.
                </p>
                {comparisonResult.analyses?.length >= 2 && (
                  <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
                    <Link
                      to={`/explorer/${comparisonResult.analyses[0].id}`}
                      className="cdl-comp-btn cdl-comp-btn-secondary"
                      style={{ fontSize: "11px", padding: "5px 12px" }}
                      title="Open Analysis 1 in Interactive Scientific Explorer"
                    >
                      🔭 Explore Analysis 1
                    </Link>
                    <Link
                      to={`/explorer/${comparisonResult.analyses[1].id}`}
                      className="cdl-comp-btn cdl-comp-btn-secondary"
                      style={{ fontSize: "11px", padding: "5px 12px" }}
                      title="Open Analysis 2 in Interactive Scientific Explorer"
                    >
                      🔭 Explore Analysis 2
                    </Link>
                  </div>
                )}
              </div>

              <span className="cdl-comp-status-badge ready">
                {comparisonResult.analysis_count} Analyses Synchronized
              </span>
            </div>

            <div className="cdl-comp-compat-grid">
              <div className="cdl-comp-compat-box">
                <span className="cdl-comp-compat-lbl">Study Context</span>
                <span className={`cdl-comp-compat-pill ${comparisonResult.study_context.status}`}>
                  {comparisonResult.study_context.badge}
                </span>
                <p className="cdl-comp-compat-msg">{comparisonResult.study_context.message}</p>
              </div>

              <div className="cdl-comp-compat-box">
                <span className="cdl-comp-compat-lbl">Calibration Compatibility</span>
                <span className={`cdl-comp-compat-pill ${comparisonResult.calibration_compatibility.status}`}>
                  {comparisonResult.calibration_compatibility.badge}
                </span>
                <p className="cdl-comp-compat-msg">{comparisonResult.calibration_compatibility.message}</p>
              </div>

              <div className="cdl-comp-compat-box">
                <span className="cdl-comp-compat-lbl">Analysis Region Scope</span>
                <span className={`cdl-comp-compat-pill ${comparisonResult.roi_compatibility.status}`}>
                  {comparisonResult.roi_compatibility.badge}
                </span>
                <p className="cdl-comp-compat-msg">{comparisonResult.roi_compatibility.message}</p>
              </div>

              <div className="cdl-comp-compat-box">
                <span className="cdl-comp-compat-lbl">Computational Quality</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {comparisonResult.analyses.map((a, idx) => {
                    const q = a.metadata?.quality_control;
                    return (
                      <span
                        key={idx}
                        className={`cdl-comp-compat-pill ${q ? q.level?.toLowerCase() : "neutral"}`}
                        style={{ fontSize: 11 }}
                      >
                        A{idx + 1}: {q ? `${q.score}/100 (${q.level})` : "N/A"}
                      </span>
                    );
                  })}
                </div>
                <p className="cdl-comp-compat-msg">Algorithmic technical quality scores for each selected evaluation.</p>
              </div>
            </div>

            {/* Warnings if compatibility issues detected */}
            {(comparisonResult.calibration_compatibility.warning || comparisonResult.roi_compatibility.warning) && (
              <div className="cdl-comp-warning-box">
                <span style={{ fontSize: "18px" }}>⚠️</span>
                <div>
                  {comparisonResult.calibration_compatibility.warning && (
                    <p style={{ margin: "0 0 4px 0" }}>
                      <strong>Calibration Notice:</strong> {comparisonResult.calibration_compatibility.warning}
                    </p>
                  )}
                  {comparisonResult.roi_compatibility.warning && (
                    <p style={{ margin: 0 }}>
                      <strong>Region Notice:</strong> {comparisonResult.roi_compatibility.warning}
                    </p>
                  )}
                </div>
              </div>
            )}
          </section>

          {/* ================================================================
              5. LARGEST QUANTITATIVE DIFFERENCES (When 2 analyses compared)
              ================================================================ */}
          {isTwoAnalyses && comparisonResult.largest_differences?.length > 0 && (
            <section className="cdl-comp-diff-section">
              <div className="cdl-comp-compat-header">
                <div>
                  <h4 className="cdl-comp-selector-title">
                    ⚡ Largest Quantitative Differences
                  </h4>
                  <p className="cdl-comp-selector-sub">
                    Parameters exhibiting maximum relative divergence between Analysis 1 (baseline) and Analysis 2.
                  </p>
                </div>
              </div>

              <div className="cdl-comp-diff-grid">
                {comparisonResult.largest_differences.map((d, idx) => (
                  <div key={idx} className="cdl-comp-diff-card">
                    <div className="cdl-comp-diff-card-top">
                      <span className="cdl-comp-diff-cat">{d.category}</span>
                      {d.pct_difference !== null && (
                        <span className={`cdl-comp-diff-pct ${d.pct_difference >= 0 ? "pos" : "neg"}`}>
                          {d.pct_difference >= 0 ? `+${d.pct_difference.toFixed(1)}%` : `${d.pct_difference.toFixed(1)}%`}
                        </span>
                      )}
                    </div>
                    <h5 className="cdl-comp-diff-name">{d.metric_name}</h5>
                    <div className="cdl-comp-diff-row">
                      <div className="cdl-comp-diff-col">
                        <span className="cdl-comp-diff-col-lbl">Analysis 1:</span>
                        <strong className="cdl-comp-diff-col-val">{formatVal(d.val1)}</strong>
                      </div>
                      <span style={{ color: "#94a3b8", fontWeight: 700 }}>→</span>
                      <div className="cdl-comp-diff-col">
                        <span className="cdl-comp-diff-col-lbl">Analysis 2:</span>
                        <strong className="cdl-comp-diff-col-val">{formatVal(d.val2)}</strong>
                      </div>
                    </div>
                    {d.difference !== null && (
                      <div style={{ fontSize: "11px", color: "#64748b" }}>
                        Delta (Δ): <strong>{d.difference >= 0 ? `+${formatVal(d.difference)}` : formatVal(d.difference)} {d.unit}</strong>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div style={{ fontSize: "11px", color: "#64748b", background: "#f8fafc", padding: "10px 14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                ℹ️ <strong>Scientific Note:</strong> Largest quantitative differences reflect algorithmic optical-flow motion variations. They do not imply clinical significance or diagnostic consequence.
              </div>
            </section>
          )}

          {/* ================================================================
              6. QUANTITATIVE COMPARISON TABLE
              ================================================================ */}
          <section className="cdl-comp-table-section">
            <div className="cdl-comp-compat-header">
              <div>
                <h4 className="cdl-comp-selector-title">
                  📊 Quantitative Comparison Table
                </h4>
                <p className="cdl-comp-selector-sub">
                  Comprehensive parametric comparison across continuum strain tensor, kinematics, and temporal dynamics.
                </p>
              </div>

              {/* Category Filter Tabs */}
              <div className="cdl-comp-filter-tabs">
                {[
                  { id: "all", label: "All Metrics" },
                  { id: "quality", label: "Quality" },
                  { id: "displacement", label: "Displacement" },
                  { id: "strain", label: "Strain" },
                  { id: "advanced", label: "Advanced" },
                  { id: "cardiac", label: "Cardiac" },
                  { id: "temporal", label: "Temporal" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    className={`cdl-comp-tab-btn ${activeCategoryTab === tab.id ? "active" : ""}`}
                    onClick={() => setActiveCategoryTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="cdl-comp-table-wrapper">
              <table className="cdl-comp-table">
                <thead>
                  <tr>
                    <th>Metric Parameter</th>
                    <th>Category</th>
                    <th>Unit</th>
                    {comparisonResult.analyses.map((a, i) => (
                      <th key={i}>
                        Analysis {i + 1}
                        <br />
                        <span style={{ fontSize: "10px", color: "#64748b", fontWeight: 500 }}>
                          ({a.metadata.type})
                        </span>
                      </th>
                    ))}
                    {isTwoAnalyses && (
                      <>
                        <th>Difference (Δ)</th>
                        <th>% Variance</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row, idx) => (
                    <tr key={idx}>
                      <td className="metric-name-cell">{row.metric_name}</td>
                      <td className="cat-cell">{row.category}</td>
                      <td className="unit-cell"><code>{row.unit || "—"}</code></td>
                      {row.values.map((v, vIdx) => (
                        <td key={vIdx} className="val-cell">{formatVal(v)}</td>
                      ))}
                      {isTwoAnalyses && (
                        <>
                          <td className="diff-cell">
                            {row.difference !== null
                              ? row.difference >= 0
                                ? `+${formatVal(row.difference)}`
                                : formatVal(row.difference)
                              : "N/A"}
                          </td>
                          <td className="pct-cell">
                            {row.pct_difference !== null ? (
                              <span
                                style={{
                                  padding: "2px 6px",
                                  borderRadius: "4px",
                                  fontSize: "11px",
                                  background: row.pct_difference > 0 ? "#ecfdf5" : row.pct_difference < 0 ? "#fef2f2" : "#f1f5f9",
                                  color: row.pct_difference > 0 ? "#059669" : row.pct_difference < 0 ? "#dc2626" : "#64748b",
                                }}
                              >
                                {row.pct_difference > 0
                                  ? `+${row.pct_difference.toFixed(2)}%`
                                  : `${row.pct_difference.toFixed(2)}%`}
                              </span>
                            ) : (
                              "N/A"
                            )}
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ================================================================
              7. BAR CHARTS (PARAMETRIC COMPARISON)
              ================================================================ */}
          {comparisonResult.chart_metrics && (
            <section className="cdl-comp-compat-card">
              <MetricComparisonCharts chartMetrics={comparisonResult.chart_metrics} />
            </section>
          )}

          {/* ================================================================
              8. 10-D RADAR FINGERPRINT COMPARISON
              ================================================================ */}
          {comparisonResult.fingerprint_comparison && (
            <section className="cdl-comp-compat-card">
              <div style={{ marginBottom: "16px" }}>
                <h4 className="cdl-comp-selector-title">
                  🧭 Deformation Profile Radar Comparison
                </h4>
                <p className="cdl-comp-selector-sub">
                  Superimposed 10-dimensional cardiac deformation signatures characterizing myocardial state across sessions.
                </p>
              </div>
              <FingerprintComparisonChart
                fingerprintComparison={comparisonResult.fingerprint_comparison}
              />
            </section>
          )}

          {/* ================================================================
              9. SIDE-BY-SIDE SPATIAL MAP COMPARISON
              ================================================================ */}
          {comparisonResult.compatible_maps && (
            <section className="cdl-comp-compat-card">
              <MapComparisonView
                compatibleMaps={comparisonResult.compatible_maps}
                analyses={comparisonResult.analyses}
              />
            </section>
          )}

          {/* ================================================================
              10. METHODOLOGY & NON-DIAGNOSTIC NOTICE
              ================================================================ */}
          <section className="methodology-card">
            <div className="methodology-header">
              <span className="methodology-badge">COMPARISON METHODOLOGY</span>
              <h3>Comparative Kinematic Framework &amp; Scientific Limitations</h3>
            </div>

            <div className="methodology-grid">
              <div className="methodology-item">
                <h4>📐 Comparative Mathematical Formulation</h4>
                <p>
                  Comparison evaluates scalar outputs computed from Farnebäck dense optical flow fields
                  and infinitesimal strain tensor calculations. Differences (\(A_2 - A_1\)) and percentage
                  variances quantify algorithmic divergence across imaging evaluations.
                </p>
              </div>

              <div className="methodology-item">
                <h4>📏 Spatial Calibration Sensitivity</h4>
                <p>
                  Displacement in pixels cannot be directly matched to physical distance without valid pixel spacing
                  metadata. If calibration differs or is absent, physical measurements must not be compared.
                  Strain remains dimensionless and unaffected by pixel spacing.
                </p>
              </div>

              <div className="methodology-item">
                <h4>🎯 Regional Demarcation &amp; ROI Scope</h4>
                <p>
                  Comparisons between Full Image evaluations and restricted Regions of Interest (ROIs) reflect
                  spatial localization rather than whole-heart mechanical differences. Tracking confidences
                  indicate optical flow stability rather than anatomical accuracy.
                </p>
              </div>

              <div className="methodology-item">
                <h4>🛡️ Automated Computational Quality Control</h4>
                <p>
                  The Quality Control layer evaluates technical characteristics of input data and computed motion/deformation fields.
                  It does not determine whether cardiac function is normal or abnormal.
                  Quality scores should not be interpreted as clinical measurements.
                </p>
              </div>

              <div className="methodology-item">
                <h4>⚠️ Non-Diagnostic Protocol Statement</h4>
                <p>
                  <strong>This comparison summarizes quantitative image-analysis measurements and is NOT a clinical diagnostic assessment.</strong>
                  Quantitative variances do not establish pathology, normal/abnormal status, or medical diagnosis.
                  Intended strictly for biomechanical research experimentation.
                </p>
              </div>
            </div>
          </section>
        </>
      )}

      {/* Save Comparison Modal */}
      <SaveComparisonModal
        isOpen={isSaveModalOpen}
        onClose={() => setIsSaveModalOpen(false)}
        onSave={handleSaveComparison}
        loading={savingComp}
        defaultTitle={
          comparisonResult
            ? `Comparison of ${comparisonResult.analysis_count} analyses (${new Date().toLocaleDateString()})`
            : ""
        }
      />

      {/* Saved Comparisons Drawer */}
      <SavedComparisonsDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSelectComparison={handleLoadSaved}
      />
    </div>
  );
}
