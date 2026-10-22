import { useState } from "react";
import { computeAnalysisQuality } from "../services/api";

export default function QualityControlCard({ qc: initialQc, analysisId, onQcUpdated }) {
  const [qc, setQc] = useState(initialQc);
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState(null);

  // Sync state if prop changes
  if (initialQc !== undefined && initialQc !== qc && !evaluating) {
    setQc(initialQc);
  }

  const handleComputeQC = async () => {
    if (!analysisId) return;
    setEvaluating(true);
    setEvalError(null);
    try {
      const data = await computeAnalysisQuality(analysisId);
      setQc(data);
      if (onQcUpdated) {
        onQcUpdated(data);
      }
    } catch (err) {
      setEvalError(err.message || "Failed to calculate quality control.");
    } finally {
      setEvaluating(false);
    }
  };

  if (!qc) {
    return (
      <div className="qc-card not-available">
        <div className="qc-header">
          <div>
            <h4>🛡️ Computational Quality</h4>
            <p className="qc-subtitle">Technical validation and numerical integrity assessment</p>
          </div>
          {analysisId && (
            <button
              type="button"
              className="btn-secondary roi-btn-sm"
              onClick={handleComputeQC}
              disabled={evaluating}
            >
              {evaluating ? "Evaluating..." : "Run Quality Assessment"}
            </button>
          )}
        </div>
        <p className="qc-unavailable-text">
          Quality assessment not available for this analysis.
        </p>
        {evalError && <p className="qc-error-text">Error: {evalError}</p>}
      </div>
    );
  }

  const { score, level, components = {}, warnings = [], info = [] } = qc;

  const levelColorClass =
    level === "High" ? "level-high" : level === "Moderate" ? "level-moderate" : "level-low";

  return (
    <div className="qc-card">
      <div className="qc-header">
        <div>
          <div className="qc-title-row">
            <h4>🛡️ Computational Quality</h4>
            <span className={`qc-level-badge ${levelColorClass}`}>
              {level} Quality
            </span>
          </div>
          <p className="qc-subtitle">
            Algorithmic integrity evaluation across input frames, optical flow, and strain tensors
          </p>
        </div>

        <div className="qc-score-circle-wrapper">
          <div className="qc-score-box">
            <span className="qc-score-number">{score}</span>
            <span className="qc-score-denom">/ 100</span>
          </div>
          <span className="qc-score-label">Quality Score</span>
        </div>
      </div>

      {/* Component Scores Grid */}
      <div className="qc-components-grid">
        {/* 1. Image Quality */}
        {components.image_quality && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">🖼️ Image Quality</span>
              <span className={`qc-comp-status ${components.image_quality.status?.toLowerCase()}`}>
                {components.image_quality.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.image_quality.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">{components.image_quality.score}/100</span>
              <span className="qc-comp-weight">Weight: {components.image_quality.weight_pct}%</span>
            </div>
          </div>
        )}

        {/* 2. Optical Flow Quality */}
        {components.motion_quality && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">🌊 Motion Quality</span>
              <span className={`qc-comp-status ${components.motion_quality.status?.toLowerCase()}`}>
                {components.motion_quality.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.motion_quality.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">{components.motion_quality.score}/100</span>
              <span className="qc-comp-weight">Weight: {components.motion_quality.weight_pct}%</span>
            </div>
          </div>
        )}

        {/* 3. Strain Tensor Quality */}
        {components.strain_quality && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">📐 Strain Quality</span>
              <span className={`qc-comp-status ${components.strain_quality.status?.toLowerCase()}`}>
                {components.strain_quality.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.strain_quality.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">{components.strain_quality.score}/100</span>
              <span className="qc-comp-weight">Weight: {components.strain_quality.weight_pct}%</span>
            </div>
          </div>
        )}

        {/* 4. ROI Quality */}
        {components.roi_quality && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">🎯 Region of Interest</span>
              <span className={`qc-comp-status ${components.roi_quality.status?.toLowerCase()}`}>
                {components.roi_quality.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.roi_quality.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">{components.roi_quality.score}/100</span>
              <span className="qc-comp-weight">
                {components.roi_quality.applicable ? `Weight: ${components.roi_quality.weight_pct}%` : "Full Image"}
              </span>
            </div>
          </div>
        )}

        {/* 5. Tracking Quality (if applicable) */}
        {components.tracking_quality && components.tracking_quality.applicable && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">🔄 ROI Tracking</span>
              <span className={`qc-comp-status ${components.tracking_quality.status?.toLowerCase()}`}>
                {components.tracking_quality.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.tracking_quality.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">{components.tracking_quality.score}/100</span>
              <span className="qc-comp-weight">Weight: {components.tracking_quality.weight_pct}%</span>
            </div>
          </div>
        )}

        {/* 6. Temporal Quality */}
        {components.temporal_quality && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">⏱️ Temporal Dynamics</span>
              <span className={`qc-comp-status ${components.temporal_quality.status?.toLowerCase()}`}>
                {components.temporal_quality.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.temporal_quality.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">{components.temporal_quality.score}/100</span>
              <span className="qc-comp-weight">
                {components.temporal_quality.applicable ? `Weight: ${components.temporal_quality.weight_pct}%` : "Single-Pair"}
              </span>
            </div>
          </div>
        )}

        {/* 7. Calibration Consistency */}
        {components.calibration_consistency && (
          <div className="qc-comp-box">
            <div className="qc-comp-top">
              <span className="qc-comp-name">📏 Spatial Calibration</span>
              <span className={`qc-comp-status ${components.calibration_consistency.calibrated ? "calibrated" : "uncalibrated"}`}>
                {components.calibration_consistency.status}
              </span>
            </div>
            <div className="qc-progress-track">
              <div
                className="qc-progress-fill"
                style={{ width: `${components.calibration_consistency.score || 0}%` }}
              />
            </div>
            <div className="qc-comp-bottom">
              <span className="qc-comp-score">
                {components.calibration_consistency.calibrated ? "Physical (mm)" : "Image-Space (px)"}
              </span>
              <span className="qc-comp-weight">Verified</span>
            </div>
          </div>
        )}
      </div>

      {/* Warnings Panel */}
      <div className="qc-panels-row">
        <div className={`qc-panel warnings-panel ${warnings.length > 0 ? "has-warnings" : "no-warnings"}`}>
          <h5>⚠️ Analysis Quality Warnings</h5>
          {warnings.length > 0 ? (
            <ul className="qc-bullet-list">
              {warnings.map((w, idx) => (
                <li key={idx} className="qc-warning-item">
                  {w}
                </li>
              ))}
            </ul>
          ) : (
            <p className="qc-clean-msg">
              ✓ No major computational quality issues detected.
            </p>
          )}
        </div>

        {/* Info Panel */}
        <div className="qc-panel info-panel">
          <h5>ℹ️ Informational Notes</h5>
          {info.length > 0 ? (
            <ul className="qc-bullet-list">
              {info.map((inf, idx) => (
                <li key={idx} className="qc-info-item">
                  {inf}
                </li>
              ))}
            </ul>
          ) : (
            <p className="qc-clean-msg">
              Standard image-space parameters evaluated.
            </p>
          )}
        </div>
      </div>

      {/* Scientific Disclaimer */}
      <div className="qc-disclaimer-box">
        <small>
          <strong>Computational Quality Disclaimer:</strong> This quality assessment evaluates algorithmic
          and numerical properties of the computational pipeline. It does NOT make clinical diagnoses, evaluate patient
          health, or determine medical normality/abnormality.
        </small>
      </div>
    </div>
  );
}

