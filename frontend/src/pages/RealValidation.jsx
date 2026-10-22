import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  runRealImageValidation,
  generateRealValidationReport,
  getReportDownloadUrl,
  getHistoryById,
} from "../services/api";

function formatVal(val, decimals = 4) {
  if (val === null || val === undefined) return "—";
  if (typeof val !== "number") return String(val);
  return val.toFixed(decimals);
}

export default function RealValidation() {
  const { analysisId } = useParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [analysisRecord, setAnalysisRecord] = useState(null);

  // PDF report state
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(null);
  const [pdfError, setPdfError] = useState(null);

  useEffect(() => {
    async function loadValidationData() {
      if (!analysisId) return;
      setLoading(true);
      setError(null);
      try {
        const [rec, bench] = await Promise.all([
          getHistoryById(analysisId).catch(() => null),
          runRealImageValidation(analysisId),
        ]);
        setAnalysisRecord(rec);
        setBenchmarkData(bench);
      } catch (err) {
        setError(err.message || "Failed to load real-image benchmark.");
      } finally {
        setLoading(false);
      }
    }
    loadValidationData();
  }, [analysisId]);

  const handleExportPDF = async () => {
    if (!analysisId) return;
    setPdfLoading(true);
    setPdfError(null);
    setPdfSuccess(null);
    try {
      const res = await generateRealValidationReport(analysisId);
      const dlUrl = getReportDownloadUrl(res.url);
      setPdfSuccess(dlUrl);
    } catch (err) {
      setPdfError(err.message || "Failed to generate validation report.");
    } finally {
      setPdfLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="real-validation-page">
        <div className="loading-state">
          <span>⏳</span>
          <p>Running real-image reference benchmark against manual annotations...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="real-validation-page">
        <div className="alert-error-banner">
          <strong>Benchmark Error:</strong> {error}
        </div>
        <Link to={`/annotations/${analysisId}`} className="btn-secondary-link">
          ← Return to Annotation Workbench
        </Link>
      </div>
    );
  }

  const lm = benchmarkData?.landmark_metrics;
  const disp = benchmarkData?.displacement_metrics;
  const roi = benchmarkData?.roi_metrics;
  const strain = benchmarkData?.strain_comparison;
  const score = benchmarkData?.benchmark_score;

  return (
    <div className="real-validation-page">
      {/* Page Header */}
      <div className="page-header">
        <div className="header-title-group">
          <div className="header-badge-row">
            <span className="prototype-badge">RESEARCH BENCHMARK</span>
            <span className="badge-scope">REAL-IMAGE REFERENCE</span>
          </div>
          <h1>Real-Image Annotation Benchmark</h1>
          <p className="page-subtitle">
            Quantitative concordance evaluation between optical-flow motion estimation and manual reference annotations.
          </p>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="btn-export-pdf"
            onClick={handleExportPDF}
            disabled={pdfLoading || benchmarkData?.annotation_count === 0}
          >
            {pdfLoading ? "Generating PDF..." : "📥 Download PDF Benchmark Report"}
          </button>
          <Link to={`/annotations/${analysisId}`} className="btn-secondary-link">
            ✏️ Annotation Workbench
          </Link>
        </div>
      </div>

      {/* Prominent Research Disclaimer */}
      <div className="validation-disclaimer-card">
        <div className="disclaimer-icon">ℹ️</div>
        <div className="disclaimer-content">
          <strong>Research Benchmark Notice:</strong>
          <p>
            Manual annotations reflect subjective operator reference labels for algorithm benchmarking. They do <em>not</em> represent medical ground truth or clinical validity. Motion estimations reflect image-space apparent optical motion.
          </p>
        </div>
      </div>

      {pdfSuccess && (
        <div className="alert-success-banner">
          Benchmark PDF report generated!{" "}
          <a href={pdfSuccess} target="_blank" rel="noopener noreferrer">
            Download PDF Report
          </a>
        </div>
      )}
      {pdfError && <div className="alert-error-banner">{pdfError}</div>}

      {/* Analysis Context Bar */}
      <div className="benchmark-context-card">
        <div className="context-item">
          <span className="ctx-label">Analysis ID</span>
          <strong className="mono">{analysisId?.slice(0, 8)}...</strong>
        </div>
        <div className="context-item">
          <span className="ctx-label">Reference Image</span>
          <span>{analysisRecord?.image1_filename || "N/A"}</span>
        </div>
        <div className="context-item">
          <span className="ctx-label">Target Image</span>
          <span>{analysisRecord?.image2_filename || "N/A"}</span>
        </div>
        <div className="context-item">
          <span className="ctx-label">Reference Annotations</span>
          <span className="badge-count">{benchmarkData?.annotation_count || 0}</span>
        </div>
        {score && (
          <div className="context-item highlight">
            <span className="ctx-label">Research Benchmark Score</span>
            <span className="score-val">{score.score}{score.scale}</span>
          </div>
        )}
      </div>

      {benchmarkData?.annotation_count === 0 ? (
        <div className="empty-benchmark-box">
          <span className="empty-icon">📍</span>
          <h3>No Reference Annotations Found</h3>
          <p>
            To benchmark optical flow against manual reference labels, add landmarks or contour regions in the Annotation Workbench.
          </p>
          <Link to={`/annotations/${analysisId}`} className="btn-primary-action">
            ✏️ Open Annotation Workbench
          </Link>
        </div>
      ) : (
        <>
          {/* Benchmark Scorecard Grid */}
          <div className="benchmark-scorecard-grid">
            <div className="scorecard-card">
              <span className="card-kpi-title">Landmark Endpoint Error</span>
              <span className="card-kpi-val">{formatVal(lm?.mean_endpoint_error)} px</span>
              <span className="card-kpi-sub">
                Max EPE: {formatVal(lm?.max_endpoint_error)} px ({lm?.paired_count || 0} pairs)
              </span>
            </div>

            <div className="scorecard-card">
              <span className="card-kpi-title">Displacement MAE</span>
              <span className="card-kpi-val">{formatVal(disp?.mae)} px</span>
              <span className="card-kpi-sub">
                RMSE: {formatVal(disp?.rmse)} px
              </span>
            </div>

            <div className="scorecard-card">
              <span className="card-kpi-title">Contour / ROI IoU</span>
              <span className="card-kpi-val">{formatVal(roi?.intersection_over_union)}</span>
              <span className="card-kpi-sub">
                Dice Coefficient: {formatVal(roi?.dice_coefficient)}
              </span>
            </div>

            <div className="scorecard-card">
              <span className="card-kpi-title">Centroid Distance</span>
              <span className="card-kpi-val">{formatVal(roi?.centroid_distance)} px</span>
              <span className="card-kpi-sub">
                Overlap: {roi?.overlap_pixels || 0} px²
              </span>
            </div>

            <div className="scorecard-card">
              <span className="card-kpi-title">Ref Geometric Strain</span>
              <span className="card-kpi-val">{formatVal(strain?.mean_reference_strain)}</span>
              <span className="card-kpi-sub">
                Algo Diff: {formatVal(strain?.strain_difference)}
              </span>
            </div>
          </div>

          {/* Section 1: Paired Landmark Motion Concordance */}
          {lm?.pairs && lm.pairs.length > 0 && (
            <div className="benchmark-section-card">
              <h3>📍 Paired Landmark Motion Concordance</h3>
              <p className="section-desc">
                Compares displacement between manually placed corresponding landmarks across frames against optical-flow estimates at those coordinates.
              </p>

              <div className="table-responsive">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th>Landmark Label</th>
                      <th>Frame 1 (x, y)</th>
                      <th>Frame 2 (x, y)</th>
                      <th>Reference Disp (px)</th>
                      <th>Optical Flow Disp (px)</th>
                      <th>Endpoint Error (px)</th>
                      <th>Disp Difference (px)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lm.pairs.map((p, idx) => (
                      <tr key={idx}>
                        <td><strong>{p.landmark_label}</strong></td>
                        <td>({p.coordinate_f0?.x}, {p.coordinate_f0?.y})</td>
                        <td>({p.coordinate_f1?.x}, {p.coordinate_f1?.y})</td>
                        <td>{formatVal(p.reference_displacement?.magnitude)}</td>
                        <td>{formatVal(p.estimated_displacement?.magnitude)}</td>
                        <td>
                          <span className={`pill-error ${p.endpoint_error > 3.0 ? "high" : "normal"}`}>
                            {formatVal(p.endpoint_error)}
                          </span>
                        </td>
                        <td>{formatVal(p.displacement_error)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 2: Manual Geometric Reference Strain */}
          {strain?.segments && strain.segments.length > 0 && (
            <div className="benchmark-section-card">
              <h3>📐 Geometric Reference Strain (Chord Elongation)</h3>
              <p className="section-desc">
                Calculates engineering strain ε = (L1 - L0) / L0 between paired landmark chords and compares with algorithmic principal strain.
              </p>

              <div className="table-responsive">
                <table className="research-table">
                  <thead>
                    <tr>
                      <th>Segment Pair</th>
                      <th>Initial Length L0 (px)</th>
                      <th>Final Length L1 (px)</th>
                      <th>Reference Strain (ε)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {strain.segments.map((seg, idx) => (
                      <tr key={idx}>
                        <td><strong>{seg.segment}</strong></td>
                        <td>{formatVal(seg.initial_length)}</td>
                        <td>{formatVal(seg.final_length)}</td>
                        <td>{formatVal(seg.reference_engineering_strain)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="strain-summary-bar">
                <span>Mean Reference Strain: <strong>{formatVal(strain.mean_reference_strain)}</strong></span>
                <span>Algorithm Principal Strain: <strong>{formatVal(strain.algorithm_mean_strain)}</strong></span>
                <span>Difference: <strong>{formatVal(strain.strain_difference)}</strong></span>
              </div>
            </div>
          )}

          {/* Section 3: ROI & Contour Boundary Concordance */}
          {roi && (
            <div className="benchmark-section-card">
              <h3>🔷 Contour and ROI Boundary Overlap (IoU)</h3>
              <p className="section-desc">
                Quantifies geometric area concordance between manual contour tracing and the analysis Region of Interest (ROI).
              </p>

              <div className="roi-metrics-grid">
                <div className="roi-metric-item">
                  <span className="lbl">Reference Contour</span>
                  <strong>{roi.reference_contour_label || "Manual Region"}</strong>
                </div>
                <div className="roi-metric-item">
                  <span className="lbl">Manual Mask Area</span>
                  <strong>{roi.manual_mask_pixels} px²</strong>
                </div>
                <div className="roi-metric-item">
                  <span className="lbl">Analysis ROI Area</span>
                  <strong>{roi.analysis_roi_pixels} px²</strong>
                </div>
                <div className="roi-metric-item">
                  <span className="lbl">Overlap Intersection</span>
                  <strong>{roi.overlap_pixels} px²</strong>
                </div>
                <div className="roi-metric-item highlight">
                  <span className="lbl">Intersection over Union (IoU)</span>
                  <strong className="iou-val">{formatVal(roi.intersection_over_union)}</strong>
                </div>
                <div className="roi-metric-item">
                  <span className="lbl">Dice Score</span>
                  <strong>{formatVal(roi.dice_coefficient)}</strong>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Scientific Limitations Card */}
      <div className="limitations-card">
        <h4>🔬 Benchmarking Methodology & Limitations</h4>
        <ul>
          <li>
            <strong>Human Observer Variability:</strong> Manual reference annotations are subjective and contain inherent inter- and intra-observer variance.
          </li>
          <li>
            <strong>Image-Space vs Anatomical Motion:</strong> 2D optical flow estimates apparent pixel velocity. This may deviate from out-of-plane myocardial tissue motion.
          </li>
          <li>
            <strong>Chord vs Continuum Mechanics:</strong> Landmark chord strain is a 1D discrete distance approximation, whereas the algorithm computes 2D continuous tensor strain.
          </li>
          <li>
            <strong>Non-Diagnostic Purpose:</strong> These concordance metrics serve strictly to assess algorithmic precision and software reliability.
          </li>
        </ul>
      </div>
    </div>
  );
}
