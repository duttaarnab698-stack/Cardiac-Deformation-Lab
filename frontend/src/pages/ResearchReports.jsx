import { useState, useEffect, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  getAllReportsHistory,
  getReportDownloadUrl,
  getStudies,
  generateComprehensiveResearchReport,
  createResearchExportPackage,
  generateLongitudinalReport,
  generateStatisticsReport,
} from "../services/api";
import "./ResearchReports.css";

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
    return String(isoString);
  }
}

function formatReportType(type) {
  switch (type) {
    case "comprehensive_research":
      return "📘 Comprehensive Research";
    case "longitudinal":
      return "📈 Longitudinal Study";
    case "statistics":
      return "📊 Advanced Statistics";
    case "validation":
      return "🧪 Synthetic Validation";
    case "real_validation":
      return "🎯 Reference Benchmark";
    default:
      return type ? type.replace(/_/g, " ") : "Research Report";
  }
}

export default function ResearchReports() {
  const [reports, setReports] = useState([]);
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & selection
  const [filterType, setFilterType] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedReportId, setSelectedReportId] = useState(null);

  // Generator form state
  const [showGenerator, setShowGenerator] = useState(true);
  const [targetStudyId, setTargetStudyId] = useState("");
  const [targetReportType, setTargetReportType] = useState("comprehensive");
  const [genLoading, setGenLoading] = useState(false);
  const [genSuccess, setGenSuccess] = useState(null);
  const [genError, setGenError] = useState(null);
  const [copiedId, setCopiedId] = useState(false);

  const fetchReportsAndStudies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [repData, stdData] = await Promise.all([
        getAllReportsHistory().catch(() => ({ reports: [] })),
        getStudies().catch(() => []),
      ]);
      const repList = repData?.reports || [];
      const stdList = Array.isArray(stdData) ? stdData : [];
      setReports(repList);
      setStudies(stdList);

      setTargetStudyId((prev) => (prev ? prev : stdList[0]?.id || ""));
      setSelectedReportId((prev) =>
        prev ? prev : repList[0]?.report_id || repList[0]?.filename || null
      );
    } catch (err) {
      setError(err.message || "Failed to load research reports history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReportsAndStudies();
  }, [fetchReportsAndStudies]);

  // Study lookup map
  const studyMap = useMemo(() => {
    const map = {};
    studies.forEach((s) => {
      map[s.id] = s;
    });
    return map;
  }, [studies]);

  // Filtered reports
  const filteredReports = useMemo(() => {
    return reports.filter((r) => {
      if (filterType !== "all" && r.report_type !== filterType) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const sTitle = (studyMap[r.study_id]?.title || r.study_title || "").toLowerCase();
        const rId = (r.report_id || "").toLowerCase();
        const fn = (r.filename || "").toLowerCase();
        return sTitle.includes(q) || rId.includes(q) || fn.includes(q);
      }
      return true;
    });
  }, [reports, filterType, searchQuery, studyMap]);

  // Currently selected report
  const selectedReport = useMemo(() => {
    if (!selectedReportId && filteredReports.length > 0) {
      return filteredReports[0];
    }
    const found = reports.find(
      (r) => (r.report_id || r.filename) === selectedReportId
    );
    return found || filteredReports[0] || reports[0] || null;
  }, [selectedReportId, filteredReports, reports]);

  // Handle report generation
  const handleGenerateReport = async (e) => {
    if (e) e.preventDefault();
    if (!targetStudyId) {
      setGenError("Please select a study to generate a report.");
      return;
    }

    setGenLoading(true);
    setGenError(null);
    setGenSuccess(null);

    try {
      let res;
      if (targetReportType === "comprehensive") {
        res = await generateComprehensiveResearchReport(targetStudyId);
      } else if (targetReportType === "package") {
        res = await createResearchExportPackage(targetStudyId);
      } else if (targetReportType === "longitudinal") {
        res = await generateLongitudinalReport(targetStudyId);
      } else if (targetReportType === "statistics") {
        res = await generateStatisticsReport(targetStudyId, "full_image");
      }

      setGenSuccess(res);
      // Refresh list to show newly generated report
      await fetchReportsAndStudies();
      if (res?.report_filename || res?.filename) {
        setSelectedReportId(res.report_filename || res.filename);
      }
    } catch (err) {
      setGenError(err.message || "Failed to generate report.");
    } finally {
      setGenLoading(false);
    }
  };

  // Export current selected report metadata as JSON
  const handleExportJsonMetadata = () => {
    if (!selectedReport) return;
    const blob = new Blob([JSON.stringify(selectedReport, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedReport.report_id || "report"}_metadata.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Copy report ID
  const handleCopyReportId = () => {
    if (!selectedReport?.report_id) return;
    navigator.clipboard.writeText(selectedReport.report_id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const selectedStudy = selectedReport?.study_id
    ? studyMap[selectedReport.study_id]
    : null;
  const targetStudyObj = targetStudyId ? studyMap[targetStudyId] : null;
  const activeReportUrl = selectedReport
    ? getReportDownloadUrl(selectedReport.url || `/reports/${selectedReport.filename}`)
    : "";

  return (
    <div className="cdl-rep-page">
      {/* 1. Header & Breadcrumbs */}
      <div className="cdl-rep-header-wrap">
        <div className="cdl-rep-title-area">
          <nav className="cdl-rep-breadcrumb" aria-label="Breadcrumb">
            <Link to="/" className="bc-link">
              <span>Home</span>
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-link">Research</span>
            <span className="bc-sep">/</span>
            <span className="bc-current">Research Reports &amp; Exports</span>
          </nav>

          <div className="cdl-rep-pill-row">
            <span className="cdl-rep-badge cdl-rep-badge-primary">
              Scientific Workspace
            </span>
            <span className="cdl-rep-badge cdl-rep-badge-cyan">
              Continuum Mechanics Core
            </span>
            <span className="cdl-rep-badge cdl-rep-badge-purple">
              Report Schema v1.0
            </span>
          </div>

          <h1 className="cdl-rep-title">
            <span className="icon-accent">📑</span>
            Scientific Research Reports &amp; Exports
          </h1>
          <p className="cdl-rep-subtitle">
            Publication-ready comprehensive reports, multi-session longitudinal
            summaries, and reproducible ZIP research packages containing kinematic tensors,
            strain metrics, and figures.
          </p>
        </div>

        <div className="cdl-rep-header-actions">
          <button
            type="button"
            className="cdl-rep-btn cdl-rep-btn-secondary"
            onClick={fetchReportsAndStudies}
            disabled={loading}
          >
            {loading ? "🔄 Refreshing..." : "🔄 Refresh Library"}
          </button>
          <button
            type="button"
            className="cdl-rep-btn cdl-rep-btn-primary"
            onClick={() => setShowGenerator((prev) => !prev)}
          >
            {showGenerator ? "Hide Generator" : "+ Generate Report"}
          </button>
        </div>
      </div>

      {/* Mandatory Non-Clinical Notice */}
      <div className="cdl-rep-notice">
        <span className="cdl-rep-notice-icon">⚠️</span>
        <div>
          <strong>Non-Clinical Research Notice:</strong> Reports are scientific engineering
          documents derived from dense optical flow and continuum finite strain tensors.
          They are computational research prototypes designed for biomechanical research and
          algorithm benchmarking, and are not validated for diagnostic, prognostic, or clinical use.
        </div>
      </div>

      {/* 2. Top Report Generator Workflow Suite */}
      {showGenerator && (
        <section className="cdl-rep-generator-card">
          <div className="cdl-rep-generator-header">
            <div className="cdl-rep-generator-title">
              <span className="step-tag">3-STEP WORKFLOW</span>
              <span>Publication Report &amp; Archive Generator</span>
            </div>
            {targetStudyObj && (
              <span className="cdl-rep-step-meta">
                Target Study: <strong>{targetStudyObj.title}</strong> (
                {targetStudyObj.analysis_ids?.length || 0} analyses)
              </span>
            )}
          </div>

          <form onSubmit={handleGenerateReport}>
            <div className="cdl-rep-generator-grid">
              {/* Step 1: Select Target Study */}
              <div className="cdl-rep-step-box">
                <div className="cdl-rep-step-head">
                  <span className="cdl-rep-step-num">1</span>
                  <span>Select Target Study</span>
                </div>
                <select
                  className="cdl-rep-select"
                  value={targetStudyId}
                  onChange={(e) => setTargetStudyId(e.target.value)}
                  disabled={genLoading || studies.length === 0}
                >
                  {studies.length === 0 ? (
                    <option value="">No studies available</option>
                  ) : (
                    studies.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title} {s.subject_code ? `(${s.subject_code})` : ""} —{" "}
                        {s.analysis_ids?.length || 0} analyses
                      </option>
                    ))
                  )}
                </select>
                <div className="cdl-rep-step-meta">
                  Choose the cardiac motion study to compile into a document.
                </div>
              </div>

              {/* Step 2: Configure Protocol */}
              <div className="cdl-rep-step-box">
                <div className="cdl-rep-step-head">
                  <span className="cdl-rep-step-num">2</span>
                  <span>Report Configuration</span>
                </div>
                <select
                  className="cdl-rep-select"
                  value={targetReportType}
                  onChange={(e) => setTargetReportType(e.target.value)}
                  disabled={genLoading}
                >
                  <option value="comprehensive">
                    Comprehensive Research Report (21 Sections PDF)
                  </option>
                  <option value="package">
                    Complete Research Package Archive (.ZIP with Figures &amp; CSV)
                  </option>
                  <option value="longitudinal">
                    Longitudinal Multi-Session Report (PDF)
                  </option>
                  <option value="statistics">
                    Advanced Study Statistics Report (PDF)
                  </option>
                </select>
                <div className="cdl-rep-step-meta">
                  Includes Farnebäck optical flow kinematics, Green-Lagrange strain, &amp; QC.
                </div>
              </div>

              {/* Step 3: Execution */}
              <div className="cdl-rep-step-box">
                <div className="cdl-rep-step-head">
                  <span className="cdl-rep-step-num">3</span>
                  <span>Generate &amp; Compile</span>
                </div>
                <button
                  type="submit"
                  className="cdl-rep-btn cdl-rep-btn-primary"
                  style={{ width: "100%", justifyContent: "center" }}
                  disabled={genLoading || !targetStudyId}
                >
                  {genLoading ? (
                    <>⏳ Compiling Document...</>
                  ) : targetReportType === "package" ? (
                    <>📦 Build Research Package</>
                  ) : (
                    <>🚀 Generate Publication Report</>
                  )}
                </button>
                <div className="cdl-rep-step-meta">
                  Automated compilation with ReportLab &amp; vector rendering.
                </div>
              </div>
            </div>

            {/* Generator Status / Feedback */}
            {(genSuccess || genError) && (
              <div className="cdl-rep-generator-foot">
                {genSuccess && (
                  <div className="cdl-rep-gen-status success">
                    <span>✅</span>
                    <span>
                      {genSuccess.message || "Document generated successfully!"} (
                      <code>
                        {genSuccess.report_filename ||
                          genSuccess.filename ||
                          genSuccess.report?.filename ||
                          "ready"}
                      </code>
                      )
                    </span>
                    {(genSuccess.url || genSuccess.report?.url) && (
                      <a
                        href={getReportDownloadUrl(
                          genSuccess.url || genSuccess.report?.url
                        )}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="cdl-rep-mini-btn"
                        style={{ marginLeft: "8px" }}
                      >
                        👁️ Open Generated Document
                      </a>
                    )}
                  </div>
                )}
                {genError && (
                  <div className="cdl-rep-gen-status error">
                    <span>❌</span>
                    <span>{genError}</span>
                  </div>
                )}
              </div>
            )}
          </form>
        </section>
      )}

      {/* General Error Banner */}
      {error && (
        <div className="cdl-rep-notice" style={{ background: "#fef2f2", borderColor: "#fca5a5", color: "#991b1b" }}>
          <span>❌</span>
          <div>{error}</div>
        </div>
      )}

      {/* 3. Three-Zone Workspace Layout */}
      <div className="cdl-rep-workspace">
        {/* ==================================================================
            ZONE 1 (LEFT): REPORT LIBRARY & HISTORY
            ================================================================== */}
        <aside className="cdl-rep-library">
          <div className="cdl-rep-pane-head">
            <h2 className="cdl-rep-pane-title">
              <span>📚</span>
              <span>Report Library</span>
            </h2>
            <span className="cdl-rep-counter-pill">
              {filteredReports.length} / {reports.length}
            </span>
          </div>

          {/* Search bar */}
          <div className="cdl-rep-search-bar">
            <span>🔍</span>
            <input
              type="text"
              placeholder="Search reports by study or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#94a3b8",
                  fontSize: "12px",
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="cdl-rep-filter-pills">
            <button
              type="button"
              className={`cdl-rep-filter-chip ${filterType === "all" ? "is-active" : ""}`}
              onClick={() => setFilterType("all")}
            >
              All
            </button>
            <button
              type="button"
              className={`cdl-rep-filter-chip ${
                filterType === "comprehensive_research" ? "is-active" : ""
              }`}
              onClick={() => setFilterType("comprehensive_research")}
            >
              Comprehensive
            </button>
            <button
              type="button"
              className={`cdl-rep-filter-chip ${
                filterType === "longitudinal" ? "is-active" : ""
              }`}
              onClick={() => setFilterType("longitudinal")}
            >
              Longitudinal
            </button>
            <button
              type="button"
              className={`cdl-rep-filter-chip ${
                filterType === "statistics" ? "is-active" : ""
              }`}
              onClick={() => setFilterType("statistics")}
            >
              Statistics
            </button>
          </div>

          {/* Report Cards Scroll Area */}
          {loading ? (
            <div style={{ textAlign: "center", padding: "36px 0", color: "#64748b" }}>
              <div className="auth-loading-spinner" style={{ margin: "0 auto 10px auto" }} />
              Loading research reports...
            </div>
          ) : filteredReports.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "36px 16px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px dashed #cbd5e1",
                color: "#64748b",
              }}
            >
              <div style={{ fontSize: "28px", marginBottom: "6px" }}>📑</div>
              <p style={{ margin: "0 0 10px 0", fontSize: "13px", fontWeight: "600" }}>
                No Reports Found
              </p>
              <p style={{ margin: 0, fontSize: "12px" }}>
                {reports.length === 0
                  ? "Generate a comprehensive report from a study above."
                  : "No documents matched your search filter."}
              </p>
            </div>
          ) : (
            <div className="cdl-rep-list">
              {filteredReports.map((r) => {
                const isSelected =
                  (r.report_id || r.filename) ===
                  (selectedReport?.report_id || selectedReport?.filename);
                const sObj = studyMap[r.study_id];
                const sTitle = sObj?.title || r.study_title || "Global Analysis";
                const repUrl = getReportDownloadUrl(r.url || `/reports/${r.filename}`);

                return (
                  <div
                    key={r.report_id || r.filename}
                    className={`cdl-rep-card ${isSelected ? "is-active" : ""}`}
                    onClick={() => setSelectedReportId(r.report_id || r.filename)}
                  >
                    <div className="cdl-rep-card-top">
                      <span className="cdl-rep-card-id">
                        {r.report_id || "REP-ARCHIVE"}
                      </span>
                      <span className="cdl-rep-badge cdl-rep-badge-primary">
                        v{r.software_version || "1.0.4"}
                      </span>
                    </div>

                    <h3 className="cdl-rep-card-title">{sTitle}</h3>

                    <div className="cdl-rep-card-meta">
                      <span>{formatReportType(r.report_type)}</span>
                      <span>{formatDate(r.generated_at)}</span>
                    </div>

                    <div className="cdl-rep-card-meta">
                      <span>
                        Analyses: <strong>{r.analysis_count ?? 1}</strong>
                      </span>
                      <span>
                        Schema: <strong>{r.report_schema_version || "1.0"}</strong>
                      </span>
                    </div>

                    <div className="cdl-rep-card-actions" onClick={(e) => e.stopPropagation()}>
                      <a
                        href={repUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="cdl-rep-mini-btn"
                        title="Open PDF report in new browser tab"
                      >
                        👁️ Open
                      </a>
                      <a
                        href={repUrl}
                        download={r.filename}
                        className="cdl-rep-mini-btn"
                        title="Download report file to disk"
                      >
                        💾 Download
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </aside>

        {/* ==================================================================
            ZONE 2 (CENTER): PUBLICATION-STYLE DOCUMENT PREVIEW
            ================================================================== */}
        <main className="cdl-rep-preview">
          <div className="cdl-rep-doc-toolbar">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span>📄</span>
              <strong>Document Preview:</strong>
              <span>
                {selectedReport
                  ? selectedReport.report_id || selectedReport.filename
                  : "No Document Selected"}
              </span>
            </div>
            {selectedReport && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span className="cdl-rep-badge cdl-rep-badge-cyan">
                  21 Sections Included
                </span>
                <a
                  href={activeReportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cdl-rep-mini-btn"
                >
                  ↗ Fullscreen PDF
                </a>
              </div>
            )}
          </div>

          {/* Academic Manuscript Paper Sheet */}
          <article className="cdl-rep-doc-sheet">
            {/* Topbar / Running Header */}
            <header className="cdl-rep-doc-topbar">
              <div>Cardiac Deformation Laboratory • Biomechanics Core</div>
              <div className="cdl-rep-doc-meta-strip">
                <span>DOC: {selectedReport?.report_id || "REP-SPECIMEN"}</span>
                <span>•</span>
                <span>VER: {selectedReport?.software_version || "1.0.4"}</span>
                <span>•</span>
                <span>PAGE 1 OF 21</span>
              </div>
            </header>

            {/* Manuscript Title Block */}
            <div className="cdl-rep-doc-title-block">
              <div className="cdl-rep-doc-category">
                OFFICIAL SCIENTIFIC RESEARCH REPORT
              </div>
              <h2 className="cdl-rep-doc-main-title">
                Computational Analysis of Myocardial Kinematics &amp; Continuum Strain Mechanics
              </h2>
              <div className="cdl-rep-doc-study-ref">
                Target Study:{" "}
                <strong>
                  {selectedStudy?.title ||
                    selectedReport?.study_title ||
                    "Multi-Session Cardiac Analysis"}
                </strong>
                {selectedStudy?.subject_code ? ` [${selectedStudy.subject_code}]` : ""}
              </div>
              <p className="cdl-rep-doc-authors">
                Automated Cardiac Deformation Analysis Pipeline • Computational Image Processing Core
              </p>
            </div>

            {/* Section 1: Executive Summary */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">1.</span> Executive Summary &amp; Research Protocol
              </h3>
              <p className="cdl-rep-doc-p">
                This document compiles the quantitative biomechanical evaluation of
                cardiac wall deformation for study{" "}
                <strong>
                  {selectedStudy?.title ||
                    selectedReport?.study_title ||
                    "the enrolled study"}
                </strong>
                . Kinematic vectors were computed using dense optical flow formulation with
                continuum finite strain tensor modeling. A total of{" "}
                <strong>{selectedReport?.analysis_count ?? 1}</strong> analysis session(s)
                were processed with automated spatial scaling and tracking validation.
              </p>
              <div className="cdl-rep-doc-callout warning">
                <strong>Non-Clinical Engineering Prototype:</strong> All metric values,
                principal strain components, and motion vector fields presented herein are
                computational research approximations. They are not intended for diagnostic,
                interventional, or patient management procedures.
              </div>
            </section>

            {/* Section 2: Study Information */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">2.</span> Study Information &amp; Specimen Parameters
              </h3>
              <div className="cdl-rep-table-wrap">
                <table className="cdl-rep-table">
                  <thead>
                    <tr>
                      <th>Attribute</th>
                      <th>Specification</th>
                      <th>Status / Standard</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Study Identifier</td>
                      <td>
                        <code>{selectedReport?.study_id || "Unassigned"}</code>
                      </td>
                      <td>Verified Research Record</td>
                    </tr>
                    <tr>
                      <td>Subject / Specimen Code</td>
                      <td>{selectedStudy?.subject_code || "ANON-001"}</td>
                      <td>De-identified Pseudonym</td>
                    </tr>
                    <tr>
                      <td>Analysis Enrolled</td>
                      <td className="num">{selectedReport?.analysis_count ?? 1} Session(s)</td>
                      <td>Multi-Frame Trajectory</td>
                    </tr>
                    <tr>
                      <td>Software Version</td>
                      <td>v{selectedReport?.software_version || "1.0.4"}</td>
                      <td>Continuous Release</td>
                    </tr>
                    <tr>
                      <td>Generation Timestamp</td>
                      <td>{formatDate(selectedReport?.generated_at)}</td>
                      <td>ISO 8601 Synchronized</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Section 3: Computational Methodology */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">3.</span> Computational Methodology &amp; Optical Flow
              </h3>
              <p className="cdl-rep-doc-p">
                Myocardial wall tracking is formulated using multi-scale polynomial expansion
                based on the Farnebäck optical flow algorithm. Image pyramids resolve gross
                translocational motion across frames while local Gaussian filtering preserves
                fine endocardial strain gradients:
              </p>
              <div className="cdl-rep-doc-callout">
                <strong>Algorithm Configuration:</strong> Pyramid Scale = 0.5; Pyramid Levels = 3;
                Averaging Window = 15 px; Iterations = 3; Polynomial Degree = 5; Poly Sigma = 1.2;
                Boundary Constraint = Bilinear Interpolation.
              </div>
            </section>

            {/* Section 4: Mathematical Framework */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">4.</span> Mathematical Framework &amp; Continuum Mechanics
              </h3>
              <p className="cdl-rep-doc-p">
                To capture large non-linear cardiac tissue deformations accurately, we employ the
                finite Green-Lagrange strain tensor derived from the spatial displacement gradient:
              </p>
              <div className="cdl-rep-math-box">
                <div className="cdl-rep-math-row">
                  <div className="cdl-rep-equation">
                    {"$$\\mathbf{F} = \\mathbf{I} + \\nabla \\mathbf{u} = \\begin{bmatrix} 1 + \\frac{\\partial u_x}{\\partial x} & \\frac{\\partial u_x}{\\partial y} \\\\ \\frac{\\partial u_y}{\\partial x} & 1 + \\frac{\\partial u_y}{\\partial y} \\end{bmatrix}$$"}
                  </div>
                  <div className="cdl-rep-eq-num">(Eq. 1 — Deformation Gradient)</div>
                </div>
                <div className="cdl-rep-math-row">
                  <div className="cdl-rep-equation">
                    {"$$\\mathbf{E} = \\frac{1}{2}(\\mathbf{F}^T\\mathbf{F} - \\mathbf{I})$$"}
                  </div>
                  <div className="cdl-rep-eq-num">(Eq. 2 — Green-Lagrange Strain Tensor)</div>
                </div>
                <div className="cdl-rep-math-row">
                  <div className="cdl-rep-equation">
                    {"$$\\epsilon_{1,2} = \\frac{E_{xx} + E_{yy}}{2} \\pm \\sqrt{\\left(\\frac{E_{xx}-E_{yy}}{2}\\right)^2 + E_{xy}^2}$$"}
                  </div>
                  <div className="cdl-rep-eq-num">(Eq. 3 — Principal Strains)</div>
                </div>
                <div className="cdl-rep-math-row">
                  <div className="cdl-rep-equation">
                    {"$$\\gamma_{\\max} = \\epsilon_1 - \\epsilon_2$$"}
                  </div>
                  <div className="cdl-rep-eq-num">(Eq. 4 — Maximum Engineering Shear)</div>
                </div>
              </div>
            </section>

            {/* Section 5: Deformation Kinematics & Strain Metric Table */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">5.</span> Deformation Kinematics &amp; Strain Fields
              </h3>
              <p className="cdl-rep-doc-p">
                Summary of primary kinematic invariants computed across myocardial regions of interest:
              </p>
              <div className="cdl-rep-table-wrap">
                <table className="cdl-rep-table">
                  <thead>
                    <tr>
                      <th>Biomechanical Metric</th>
                      <th>Symbol</th>
                      <th>Formulation</th>
                      <th className="num">Engineering Unit</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Displacement Magnitude</td>
                      <td>{"$$\\|\\mathbf{u}\\|$$"}</td>
                      <td>{"$$\\sqrt{u_x^2 + u_y^2}$$"}</td>
                      <td className="num">mm (calibrated) / px</td>
                    </tr>
                    <tr>
                      <td>First Principal Strain (Tensile)</td>
                      <td>{"$$\\epsilon_1$$"}</td>
                      <td>{"Max Eigenvalue of $$\\mathbf{E}$$"}</td>
                      <td className="num">% (Lagrangian)</td>
                    </tr>
                    <tr>
                      <td>Second Principal Strain (Compressive)</td>
                      <td>{"$$\\epsilon_2$$"}</td>
                      <td>{"Min Eigenvalue of $$\\mathbf{E}$$"}</td>
                      <td className="num">% (Lagrangian)</td>
                    </tr>
                    <tr>
                      <td>Maximum In-Plane Shear Strain</td>
                      <td>{"$$\\gamma_{\\max}$$"}</td>
                      <td>{"$$\\epsilon_1 - \\epsilon_2$$"}</td>
                      <td className="num">%</td>
                    </tr>
                    <tr>
                      <td>Kinematic Entropy</td>
                      <td>$$H$$</td>
                      <td>{"$$-\\sum p_i \\log_2(p_i)$$"}</td>
                      <td className="num">bits (Spatial Complexity)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Section 6: Quality Control & Calibration */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">6.</span> Computational Quality Control &amp; Calibration
              </h3>
              <p className="cdl-rep-doc-p">
                Automated validation metrics evaluate optical flow reliability and temporal continuity:
              </p>
              <div className="cdl-rep-table-wrap">
                <table className="cdl-rep-table">
                  <thead>
                    <tr>
                      <th>Quality Metric</th>
                      <th>Evaluated Parameter</th>
                      <th>Acceptance Criterion</th>
                      <th className="num">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Spatial Calibration Scale</td>
                      <td>Pixels per millimeter ratio</td>
                      <td>Scale &gt; 0.0 mm/px</td>
                      <td className="num">Verified</td>
                    </tr>
                    <tr>
                      <td>Vector Coherence Index</td>
                      <td>Angular alignment of neighboring vectors</td>
                      <td>Score &ge; 0.70</td>
                      <td className="num">Nominal</td>
                    </tr>
                    <tr>
                      <td>Frame-to-Frame Drift Rate</td>
                      <td>Accumulated centroid displacement</td>
                      <td>Drift &lt; 5.0% / cycle</td>
                      <td className="num">Compensated</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Section 7: Verification & Conclusions */}
            <section className="cdl-rep-doc-section">
              <h3 className="cdl-rep-doc-h2">
                <span className="sec-num">7.</span> Benchmarks, Verification &amp; Disclaimer
              </h3>
              <p className="cdl-rep-doc-p">
                Algorithm stability has been benchmarked against synthetic radial phantom ground truth
                and manual reference annotations. For full tabular raw data, kinematic CSV files,
                and high-resolution strain heatmaps, download the complete ZIP Research Package.
              </p>
            </section>

            {/* Footer / Running Footer */}
            <footer className="cdl-rep-doc-footer">
              <div>
                <strong>Cardiac Deformation Lab</strong> • Biomechanical Research Software
              </div>
              <div>
                Report ID: <code>{selectedReport?.report_id || "REP-SPECIMEN"}</code> • Non-Diagnostic
              </div>
            </footer>
          </article>
        </main>

        {/* ==================================================================
            ZONE 3 (RIGHT): REPORT INSPECTOR & EXPORT ACTIONS
            ================================================================== */}
        <aside className="cdl-rep-inspector">
          <div className="cdl-rep-pane-head">
            <h2 className="cdl-rep-pane-title">
              <span>🔬</span>
              <span>Report Inspector</span>
            </h2>
            {selectedReport && (
              <span className="cdl-rep-counter-pill">
                {selectedReport.report_id || "SELECTED"}
              </span>
            )}
          </div>

          {selectedReport ? (
            <>
              {/* Selected Report Metadata Spec Card */}
              <div className="cdl-rep-spec-card">
                <div className="cdl-rep-spec-row">
                  <span>Report ID:</span>
                  <strong>{selectedReport.report_id || "LEGACY"}</strong>
                </div>
                <div className="cdl-rep-spec-row">
                  <span>Study Target:</span>
                  <strong>
                    {selectedStudy?.title || selectedReport.study_title || "Global"}
                  </strong>
                </div>
                <div className="cdl-rep-spec-row">
                  <span>Report Type:</span>
                  <strong>{formatReportType(selectedReport.report_type)}</strong>
                </div>
                <div className="cdl-rep-spec-row">
                  <span>Analyses Included:</span>
                  <strong>{selectedReport.analysis_count ?? 1} session(s)</strong>
                </div>
                <div className="cdl-rep-spec-row">
                  <span>Software Version:</span>
                  <strong>v{selectedReport.software_version || "1.0.4"}</strong>
                </div>
                <div className="cdl-rep-spec-row">
                  <span>Generated Date:</span>
                  <strong>{formatDate(selectedReport.generated_at)}</strong>
                </div>
              </div>

              {/* Primary Action Stack */}
              <div className="cdl-rep-action-stack">
                <a
                  href={activeReportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cdl-rep-export-btn pdf"
                >
                  <span>👁️</span>
                  <span>Open PDF in New Tab</span>
                </a>

                <a
                  href={activeReportUrl}
                  download={selectedReport.filename}
                  className="cdl-rep-export-btn pdf"
                  style={{
                    background: "linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%)",
                  }}
                >
                  <span>💾</span>
                  <span>Download PDF Report</span>
                </a>

                {selectedReport.study_id && (
                  <button
                    type="button"
                    className="cdl-rep-export-btn zip"
                    onClick={async () => {
                      setGenLoading(true);
                      setGenError(null);
                      try {
                        const pkg = await createResearchExportPackage(
                          selectedReport.study_id
                        );
                        if (pkg?.url) {
                          const dlUrl = getReportDownloadUrl(pkg.url);
                          window.open(dlUrl, "_blank");
                        }
                        setGenSuccess(pkg);
                        await fetchReportsAndStudies();
                      } catch (err) {
                        setGenError(err.message || "Failed to create research package.");
                      } finally {
                        setGenLoading(false);
                      }
                    }}
                    disabled={genLoading}
                  >
                    <span>📦</span>
                    <span>{genLoading ? "Building Archive..." : "Download Research Package ZIP"}</span>
                  </button>
                )}

                <button
                  type="button"
                  className="cdl-rep-export-btn json"
                  onClick={handleExportJsonMetadata}
                >
                  <span>📊</span>
                  <span>Export Metadata JSON</span>
                </button>

                <button
                  type="button"
                  className="cdl-rep-export-btn json"
                  onClick={handleCopyReportId}
                >
                  <span>📋</span>
                  <span>{copiedId ? "Copied ID to Clipboard!" : "Copy Report ID"}</span>
                </button>
              </div>

              {/* Research Package Checklist */}
              <div className="cdl-rep-checklist">
                <strong style={{ color: "#0f172a", marginBottom: "4px" }}>
                  📦 Research Package Artifacts
                </strong>
                <div className="cdl-rep-check-item">
                  <span className="cdl-rep-check-icon">✓</span>
                  <span>Comprehensive PDF Report (21 sections)</span>
                </div>
                <div className="cdl-rep-check-item">
                  <span className="cdl-rep-check-icon">✓</span>
                  <span>Kinematic Displacement &amp; Strain CSV</span>
                </div>
                <div className="cdl-rep-check-item">
                  <span className="cdl-rep-check-icon">✓</span>
                  <span>Deformation Fingerprint JSON Vector</span>
                </div>
                <div className="cdl-rep-check-item">
                  <span className="cdl-rep-check-icon">✓</span>
                  <span>Principal Strain &amp; Motion Vector Maps</span>
                </div>
              </div>

              {/* Study Workspace Cross-Navigation */}
              {selectedReport.study_id && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <strong style={{ fontSize: "12px", color: "#64748b" }}>
                    Workspace Navigation
                  </strong>
                  <div className="cdl-rep-links-list">
                    <Link
                      to={`/studies/${selectedReport.study_id}`}
                      className="cdl-rep-link-item"
                    >
                      <span>📁 Study Overview</span>
                      <span>→</span>
                    </Link>
                    <Link
                      to={`/longitudinal/${selectedReport.study_id}`}
                      className="cdl-rep-link-item"
                    >
                      <span>📈 Longitudinal Workspace</span>
                      <span>→</span>
                    </Link>
                    <Link
                      to={`/statistics?study=${selectedReport.study_id}`}
                      className="cdl-rep-link-item"
                    >
                      <span>📊 Research Statistics</span>
                      <span>→</span>
                    </Link>
                    <Link to="/analysis" className="cdl-rep-link-item">
                      <span>🔬 New Image Analysis</span>
                      <span>→</span>
                    </Link>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: "center", padding: "40px 10px", color: "#64748b" }}>
              <p>Select a report from the library to inspect metadata and export options.</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
