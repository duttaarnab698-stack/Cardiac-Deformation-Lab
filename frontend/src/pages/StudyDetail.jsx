import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getStudy,
  removeAnalysisFromStudy,
  generateAnalysisReport,
  generateComprehensiveResearchReport,
  createResearchExportPackage,
  generateLongitudinalReport,
  getReportDownloadUrl,
  getStudyReportsHistory,
} from "../services/api";
import AnalysisMaps from "../components/AnalysisMaps";
import FingerprintChart from "../components/FingerprintChart";
import TemporalChart from "../components/TemporalChart";
import SummaryCards from "../components/SummaryCards";
import ROIComparisonView from "../components/ROIComparisonView";
import QualityControlCard from "../components/QualityControlCard";

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
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export default function StudyDetail() {
  const { studyId } = useParams();
  const [study, setStudy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMsg, setActionMsg] = useState("");

  // Selected analysis for deep inspection
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);

  // Report state: { [id]: { loading: boolean, reportUrl: string | null } }
  const [reportState, setReportState] = useState({});

  // Research Report Modal State (Step 11.18)
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportTypeSelect, setReportTypeSelect] = useState("comprehensive_research");
  const [generatingReport, setGeneratingReport] = useState(false);
  const [exportingPackage, setExportingPackage] = useState(false);
  const [studyReportsList, setStudyReportsList] = useState([]);
  const [lastGeneratedReport, setLastGeneratedReport] = useState(null);

  const fetchStudyReports = async () => {
    try {
      const res = await getStudyReportsHistory(studyId);
      setStudyReportsList(res.reports || []);
    } catch {
      setStudyReportsList([]);
    }
  };

  const fetchStudyData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getStudy(studyId, true);
      setStudy(data);
      if (data.analyses && data.analyses.length > 0) {
        // Keep selected analysis or default to first valid record
        const valid = data.analyses.filter((a) => !a.deleted);
        if (valid.length > 0 && (!selectedAnalysis || !valid.find((v) => v.id === selectedAnalysis.id))) {
          setSelectedAnalysis(valid[0]);
        }
      } else {
        setSelectedAnalysis(null);
      }
    } catch (err) {
      setError(err.message || "Failed to load study details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudyData();
    fetchStudyReports();
  }, [studyId]);

  const handleGenerateStudyReport = async () => {
    setGeneratingReport(true);
    setError(null);
    try {
      let res;
      if (reportTypeSelect === "comprehensive_research") {
        res = await generateComprehensiveResearchReport(studyId);
      } else if (reportTypeSelect === "longitudinal") {
        res = await generateLongitudinalReport(studyId);
      } else {
        res = await generateComprehensiveResearchReport(studyId);
      }
      setLastGeneratedReport(res);
      setActionMsg(`Report generated successfully: ${res.report_filename || res.filename}`);
      await fetchStudyReports();
    } catch (err) {
      setError(err.message || "Failed to generate report.");
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleExportPackage = async () => {
    setExportingPackage(true);
    setError(null);
    try {
      const res = await createResearchExportPackage(studyId);
      setActionMsg(`Research export package created: ${res.filename}`);
      const downloadUrl = getReportDownloadUrl(res.url);
      window.open(downloadUrl, "_blank");
    } catch (err) {
      setError(err.message || "Failed to create research package.");
    } finally {
      setExportingPackage(false);
    }
  };

  const handleRemoveAnalysis = async (e, analysisId) => {
    e.stopPropagation();
    if (
      !window.confirm(
        "Are you sure you want to remove this analysis from the study?\n\nNOTE: The analysis will remain preserved in global history."
      )
    ) {
      return;
    }

    try {
      await removeAnalysisFromStudy(studyId, analysisId);
      setActionMsg("Analysis unlinked from study.");
      if (selectedAnalysis?.id === analysisId) {
        setSelectedAnalysis(null);
      }
      await fetchStudyData();
    } catch (err) {
      setError(err.message || "Failed to unlink analysis from study.");
    }
  };

  const handleGenerateReport = async (e, analysisId) => {
    if (e) e.stopPropagation();
    setReportState((prev) => ({
      ...prev,
      [analysisId]: { loading: true, reportUrl: null },
    }));

    try {
      const res = await generateAnalysisReport(analysisId);
      const url = getReportDownloadUrl(res.url);
      setReportState((prev) => ({
        ...prev,
        [analysisId]: { loading: false, reportUrl: url },
      }));
      setActionMsg(`Report generated successfully for ${analysisId.slice(0, 8)}`);
    } catch (err) {
      setReportState((prev) => ({
        ...prev,
        [analysisId]: { loading: false, reportUrl: null },
      }));
      setError(err.message || "Report generation failed.");
    }
  };

  if (loading) {
    return (
      <div className="study-detail-page">
        <div className="status-banner loading">
          <span className="spinner"></span> Loading study details...
        </div>
      </div>
    );
  }

  if (error || !study) {
    return (
      <div className="study-detail-page">
        <div className="status-banner error">
          <strong>Notice:</strong> {error || "Study not found"}
        </div>
        <Link to="/studies" className="btn-secondary" style={{ marginTop: "16px", display: "inline-block" }}>
          &larr; Back to Studies
        </Link>
      </div>
    );
  }

  const analysesList = study.analyses || [];
  const displayResult = selectedAnalysis?.result;
  const isTemporal = selectedAnalysis?.type === "temporal";
  const fp = displayResult?.cardiac_deformation_fingerprint?.fingerprint;

  return (
    <div className="study-detail-page">
      {/* Top Breadcrumb & Actions */}
      <div className="study-detail-top-nav">
        <Link to="/studies" className="back-link">
          &larr; All Studies
        </Link>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <Link
            to={`/longitudinal/${study.id}`}
            className="btn-primary"
            style={{
              opacity: analysesList.length > 0 ? 1 : 0.5,
              pointerEvents: analysesList.length > 0 ? "auto" : "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
            title={analysesList.length === 0 ? "Requires at least 1 associated analysis" : "Open multi-session longitudinal study analysis"}
          >
            📈 Open Longitudinal Analysis
          </Link>
          <Link
            to={`/statistics/${study.id}`}
            className="btn-secondary"
            style={{
              opacity: analysesList.length > 0 ? 1 : 0.5,
              pointerEvents: analysesList.length > 0 ? "auto" : "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
            title={analysesList.length === 0 ? "Requires at least 1 associated analysis" : "Open advanced research statistics & correlation matrix"}
          >
            📐 Research Statistics
          </Link>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setShowReportModal(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              background: "#2563eb",
            }}
            title="Generate publication-ready comprehensive research report or export package"
          >
            📑 Generate Research Report
          </button>
          <Link
            to="/annotations"
            className="btn-secondary"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
            title="Open Annotation Workbench for this study's images"
          >
            ✏️ Annotations
          </Link>
          <Link to="/analysis" className="btn-secondary">
            ➕ Run Analysis for this Study
          </Link>
        </div>
      </div>

      {actionMsg && (
        <div className="status-banner loading" style={{ margin: "10px 0" }}>
          {actionMsg}
        </div>
      )}

      {/* Study Overview Header Card */}
      <div className="study-overview-card">
        <div className="study-overview-header">
          <div>
            <span className="study-subject-badge">
              {study.subject_code ? `Subject: ${study.subject_code}` : "No Subject Code"}
            </span>
            <h2 className="study-title">{study.title}</h2>
          </div>
          <span className="study-id-tag">ID: <code>{study.id}</code></span>
        </div>

        {study.description && (
          <p className="study-description">{study.description}</p>
        )}

        <div className="study-metadata-row">
          <div className="meta-col">
            <span className="meta-title">Associated Analyses</span>
            <span className="meta-value">{study.analysis_ids?.length || 0}</span>
          </div>
          <div className="meta-col">
            <span className="meta-title">Date Created</span>
            <span className="meta-value">{formatDate(study.created_at)}</span>
          </div>
          <div className="meta-col">
            <span className="meta-title">Last Updated</span>
            <span className="meta-value">{formatDate(study.updated_at)}</span>
          </div>
        </div>
      </div>

      {/* Associated Analyses Section */}
      <section className="study-analyses-section">
        <div className="section-badge-header">
          <h3>Associated Analyses ({analysesList.length})</h3>
          <span className="badge badge-success">Study Group</span>
        </div>

        {analysesList.length === 0 ? (
          <div className="empty-study-analyses">
            <p>No analyses associated with this study yet.</p>
            <div className="empty-actions">
              <Link to="/analysis" className="btn-primary">
                Run Single Pair Analysis
              </Link>
              <Link to="/temporal" className="btn-secondary">
                Run Temporal Sequence
              </Link>
            </div>
          </div>
        ) : (
          <div className="history-table-container">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Scope</th>
                  <th>Analysis ID</th>
                  <th>Recorded</th>
                  <th>Mean Disp</th>
                  <th>Principal Strain</th>
                  <th>TSI</th>
                  <th>Quality</th>
                  <th>Report</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {analysesList.map((item) => {
                  const isSelected = selectedAnalysis?.id === item.id;
                  const isTemp = item.type === "temporal";
                  const s = item.summary || {};
                  const rState = reportState[item.id] || {};

                  if (item.deleted) {
                    return (
                      <tr key={item.id} className="history-row unlinked-row">
                        <td><span className="tag-unavailable">Unlinked</span></td>
                        <td>-</td>
                        <td><code>{item.id.slice(0, 8)}...</code></td>
                        <td colSpan={4}><em>Analysis record cleared from global history</em></td>
                        <td colSpan={2}>
                          <button
                            type="button"
                            className="btn-delete-item"
                            onClick={(e) => handleRemoveAnalysis(e, item.id)}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    );
                  }

                  return (
                    <tr
                      key={item.id}
                      className={`history-row ${isSelected ? "selected-row" : ""}`}
                      onClick={() => setSelectedAnalysis(item)}
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
                            ROI ({s.roi.type})
                          </span>
                        ) : (
                          <span className="badge badge-secondary">Full Image</span>
                        )}
                      </td>
                      <td className="history-id-cell">
                        <code>{item.id.slice(0, 8)}...</code>
                      </td>
                      <td className="history-date-cell">{formatDate(item.timestamp)}</td>
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
                        {s.temporal_stability_index !== null && s.temporal_stability_index !== undefined
                          ? formatNumber(s.temporal_stability_index)
                          : "N/A"}
                      </td>
                      <td>
                        {s.quality_control ? (
                          <span
                            className={`qc-table-pill ${s.quality_control.level?.toLowerCase()}`}
                            title={`Computational Quality: ${s.quality_control.score}/100 (${s.quality_control.level})`}
                          >
                            {s.quality_control.score} ({s.quality_control.level})
                          </span>
                        ) : (
                          <span className="tag-unavailable" title="Not yet evaluated">N/A</span>
                        )}
                      </td>
                      <td>
                        {rState.reportUrl ? (
                          <a
                            href={rState.reportUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-open-report"
                            onClick={(e) => e.stopPropagation()}
                          >
                            📄 Open
                          </a>
                        ) : (
                          <button
                            type="button"
                            className="btn-report-action"
                            disabled={rState.loading}
                            onClick={(e) => handleGenerateReport(e, item.id)}
                          >
                            {rState.loading ? "Generating..." : "📄 PDF"}
                          </button>
                        )}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn-delete-item"
                          onClick={(e) => handleRemoveAnalysis(e, item.id)}
                          title="Unlink analysis from this study"
                        >
                          Unlink
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Selected Analysis Deep Inspection */}
      {selectedAnalysis && displayResult && (
        <div className="active-detail-container">
          <div className="active-detail-header">
            <div>
              <h3>
                {isTemporal ? "⏱️ Temporal Sequence Analysis" : "🔬 Single Pair Differential Analysis"}
              </h3>
              <span className="record-meta-tag">
                Record ID: <code>{selectedAnalysis.id}</code> &bull; Recorded {formatDate(selectedAnalysis.timestamp)}
                {displayResult?.analysis_scope?.mode === "roi" && (
                  <span className="roi-meta-tag">
                    {" "}&bull; ROI: <strong>{displayResult.analysis_scope.roi_type}</strong> ({displayResult.analysis_scope.pixel_count} px)
                  </span>
                )}
              </span>
            </div>
            <div>
              <button
                type="button"
                className="btn-primary"
                onClick={() => handleGenerateReport(null, selectedAnalysis.id)}
              >
                📄 Generate PDF Report
              </button>
            </div>
          </div>

          {/* ROI vs Full Image Comparison (if ROI was analyzed) */}
          {displayResult?.roi_metrics && (
            <ROIComparisonView result={displayResult} />
          )}

          {/* Computational Quality Control Card */}
          <QualityControlCard
            qc={displayResult?.quality_control}
            analysisId={selectedAnalysis?.id}
            onQcUpdated={(newQc) => {
              if (displayResult) {
                displayResult.quality_control = newQc;
              }
            }}
          />

          {/* 8 Summary Metric Cards */}
          <SummaryCards
            meanDisplacement={
              displayResult?.displacement?.mean_displacement ??
              fp?.D_mean
            }
            maxDisplacement={
              displayResult?.displacement?.max_displacement ??
              fp?.D_max
            }
            meanPrincipalStrain={
              displayResult?.strain_statistics?.principal_strain_1?.mean ??
              displayResult?.principal_strain_1?.summary?.mean ??
              fp?.epsilon_principal
            }
            maxPrincipalStrain={
              displayResult?.strain_statistics?.principal_strain_1?.max ??
              displayResult?.principal_strain_1?.summary?.max ??
              fp?.epsilon_max
            }
            motionCoherence={
              displayResult?.advanced_metrics?.motion_coherence?.mean ??
              fp?.C
            }
            anisotropy={
              displayResult?.advanced_metrics?.anisotropy?.mean ??
              fp?.AI
            }
            strainEntropy={
              displayResult?.advanced_metrics?.entropy ??
              fp?.H
            }
            temporalStability={
              displayResult?.principal_strain_1?.summary?.temporal_stability_index ??
              displayResult?.temporal_stability?.temporal_stability_index ??
              fp?.TSI
            }
            calibration={displayResult?.calibration}
            physicalDisplacement={displayResult?.displacement?.physical_space}
          />

          {/* Temporal Strain Curves (if temporal) */}
          {isTemporal && (
            <div className="results-card">
              <h4>Temporal Strain Dynamics Across Cardiac Cycle</h4>
              <TemporalChart temporalData={displayResult} />
            </div>
          )}

          {/* Spatial 2D Maps (Sections A, B, C, D) */}
          {!isTemporal && displayResult?.outputs && (
            <AnalysisMaps analysisData={displayResult} />
          )}

          {/* Fingerprint Radar */}
          {displayResult.cardiac_deformation_fingerprint && (
            <div className="results-card fingerprint-wrapper-section">
              <FingerprintChart
                fingerprintData={displayResult.cardiac_deformation_fingerprint}
                fingerprint={fp}
              />
            </div>
          )}
        </div>
      )}

      {/* Research Report Generator Modal (Step 11.18) */}
      {showReportModal && (
        <div className="modal-backdrop" onClick={() => setShowReportModal(false)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "680px", width: "90%", padding: "24px" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700" }}>
                📑 Generate Scientific Research Report
              </h3>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowReportModal(false)}
                style={{ padding: "4px 8px" }}
              >
                ✕
              </button>
            </div>

            {/* Non-clinical Disclaimer Banner */}
            <div
              style={{
                background: "#fffbeb",
                border: "1px solid #fef3c7",
                borderLeft: "4px solid #f59e0b",
                padding: "10px 14px",
                borderRadius: "6px",
                marginBottom: "16px",
                fontSize: "12px",
                color: "#92400e",
              }}
            >
              <strong>Research Prototype:</strong> Reports are scientific engineering documents. They do not provide diagnosis, prognosis, treatment recommendations, or claims of clinical validity.
            </div>

            {/* Report Preview Information */}
            <div
              style={{
                background: "#f8fafc",
                border: "1px solid #e2e8f0",
                borderRadius: "6px",
                padding: "12px 16px",
                marginBottom: "16px",
              }}
            >
              <div style={{ fontSize: "13px", marginBottom: "6px" }}>
                <strong>Study:</strong> {study.title} (<code>{study.id.slice(0, 8)}...</code>)
              </div>
              <div style={{ fontSize: "13px", marginBottom: "6px" }}>
                <strong>Associated Analyses:</strong> {analysesList.length} session(s)
              </div>
              <div style={{ fontSize: "13px" }}>
                <strong>Estimated Sections:</strong> 21 Comprehensive Sections (Methodology, Kinematics, Strains, Advanced Metrics, Fingerprint, Temporal, ROI, Calibration, QC, Longitudinal, Statistics, Validation, Benchmarking, Limitations, Appendix)
              </div>
            </div>

            {/* Select Report Type */}
            <div style={{ marginBottom: "20px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: "600", marginBottom: "8px" }}>
                Select Report Type:
              </label>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="reportType"
                    value="comprehensive_research"
                    checked={reportTypeSelect === "comprehensive_research"}
                    onChange={(e) => setReportTypeSelect(e.target.value)}
                  />
                  <span>
                    <strong>Comprehensive Research Report</strong> (Complete 21-section publication PDF with maps, formulas, and appendices)
                  </span>
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: analysesList.length >= 2 ? "pointer" : "not-allowed" }}>
                  <input
                    type="radio"
                    name="reportType"
                    value="longitudinal"
                    checked={reportTypeSelect === "longitudinal"}
                    disabled={analysesList.length < 2}
                    onChange={(e) => setReportTypeSelect(e.target.value)}
                  />
                  <span style={{ color: analysesList.length < 2 ? "#94a3b8" : "inherit" }}>
                    <strong>Longitudinal Progression Report</strong> (Multi-session trend curves, stability indices) {analysesList.length < 2 ? "(Disabled: Requires ≥ 2 analyses)" : ""}
                  </span>
                </label>
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", borderTop: "1px solid #e2e8f0", paddingTop: "16px" }}>
              <button
                type="button"
                className="btn-secondary"
                disabled={exportingPackage || analysesList.length === 0}
                onClick={handleExportPackage}
                title="Create complete ZIP package containing PDF, CSV files, JSON metadata, and figures"
              >
                {exportingPackage ? "Packaging..." : "📦 Export Research Package (.ZIP)"}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={generatingReport || analysesList.length === 0}
                onClick={handleGenerateStudyReport}
                style={{ background: "#2563eb" }}
              >
                {generatingReport ? "Generating PDF..." : "📄 Generate Publication PDF"}
              </button>
            </div>

            {/* Generated Report Quick Actions */}
            {lastGeneratedReport && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "12px",
                  background: "#f0fdf4",
                  border: "1px solid #bbf7d0",
                  borderRadius: "6px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: "13px", color: "#166534" }}>
                  ✅ <strong>Report Ready:</strong> {lastGeneratedReport.report_filename || lastGeneratedReport.filename}
                </span>
                <div style={{ display: "flex", gap: "6px" }}>
                  <a
                    href={getReportDownloadUrl(lastGeneratedReport.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-open-report"
                  >
                    👁️ Open
                  </a>
                  <a
                    href={getReportDownloadUrl(lastGeneratedReport.url)}
                    download
                    className="btn-report-action"
                  >
                    💾 Download
                  </a>
                </div>
              </div>
            )}

            {/* Study Report History */}
            {studyReportsList.length > 0 && (
              <div style={{ marginTop: "20px", borderTop: "1px solid #e2e8f0", paddingTop: "14px" }}>
                <h4 style={{ margin: "0 0 10px 0", fontSize: "13px", fontWeight: "600", color: "#475569" }}>
                  Previous Reports for this Study ({studyReportsList.length})
                </h4>
                <div style={{ maxHeight: "140px", overflowY: "auto" }}>
                  {studyReportsList.map((sr) => (
                    <div
                      key={sr.report_id || sr.filename}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "6px 8px",
                        fontSize: "12px",
                        borderBottom: "1px solid #f1f5f9",
                      }}
                    >
                      <span>
                        <code>{sr.report_id || "REPORT"}</code> • {formatDate(sr.generated_at)}
                      </span>
                      <a
                        href={getReportDownloadUrl(sr.url || `/reports/${sr.filename}`)}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "#2563eb", textDecoration: "none", fontWeight: "600" }}
                      >
                        Open PDF
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

