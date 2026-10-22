import { useState } from "react";
import FingerprintChart from "./FingerprintChart";

function formatNumber(val, decimals = 4, suffix = "") {
  if (val === null || val === undefined) return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return `${val.toExponential(decimals)}${suffix}`;
  }
  return `${val.toFixed(decimals)}${suffix}`;
}

export default function ROIComparisonView({ result }) {
  const [activeFingerprintTab, setActiveFingerprintTab] = useState("roi"); // 'roi' | 'full' | 'both'

  if (!result || !result.roi_metrics) {
    return null;
  }

  const full = result.full_image_metrics || {};
  const roi = result.roi_metrics || {};
  const scope = result.analysis_scope || {};
  const cal = result.calibration;

  const isCalibrated = Boolean(cal?.enabled);
  const dispUnit = isCalibrated ? (cal?.unit || "mm") : "px";

  // Displacement values
  const fullDispMean = isCalibrated
    ? (full.displacement?.physical_space?.mean ?? full.displacement?.mean_displacement)
    : full.displacement?.mean_displacement;
  const roiDispMean = isCalibrated
    ? (roi.displacement?.physical_space?.mean ?? roi.displacement?.mean_displacement)
    : roi.displacement?.mean_displacement;

  const fullDispMax = isCalibrated
    ? (full.displacement?.physical_space?.max ?? full.displacement?.max_displacement)
    : full.displacement?.max_displacement;
  const roiDispMax = isCalibrated
    ? (roi.displacement?.physical_space?.max ?? roi.displacement?.max_displacement)
    : roi.displacement?.max_displacement;

  // Strain values
  const fullP1Mean = full.strain_statistics?.principal_strain_1?.mean ?? full.principal_strain_1?.summary?.mean;
  const roiP1Mean = roi.strain_statistics?.principal_strain_1?.mean ?? roi.principal_strain_1?.summary?.mean;

  const fullP1Max = full.strain_statistics?.principal_strain_1?.max ?? full.principal_strain_1?.summary?.max;
  const roiP1Max = roi.strain_statistics?.principal_strain_1?.max ?? roi.principal_strain_1?.summary?.max;

  // Advanced metrics
  const fullCoh = full.advanced_metrics?.motion_coherence?.mean ?? full.fingerprint?.fingerprint?.C;
  const roiCoh = roi.advanced_metrics?.motion_coherence?.mean ?? roi.fingerprint?.fingerprint?.C;

  const fullAniso = full.advanced_metrics?.anisotropy?.mean ?? full.fingerprint?.fingerprint?.AI;
  const roiAniso = roi.advanced_metrics?.anisotropy?.mean ?? roi.fingerprint?.fingerprint?.AI;

  const fullEntropy = full.advanced_metrics?.entropy ?? full.fingerprint?.fingerprint?.H;
  const roiEntropy = roi.advanced_metrics?.entropy ?? roi.fingerprint?.fingerprint?.H;

  const fullEnergy = full.advanced_metrics?.deformation_energy?.mean;
  const roiEnergy = roi.advanced_metrics?.deformation_energy?.mean;

  // Cardiac deformation
  const fullRadial = full.cardiac_deformation?.radial?.mean;
  const roiRadial = roi.cardiac_deformation?.radial?.mean;

  const fullCirc = full.cardiac_deformation?.circumferential?.mean;
  const roiCirc = roi.cardiac_deformation?.circumferential?.mean;

  // Pixel coverage
  const roiPx = roi.pixel_count || scope.pixel_count || 0;
  const fullPx = full.pixel_count || 1;
  const pctCoverage = fullPx > 0 ? ((roiPx / fullPx) * 100).toFixed(1) : "0.0";

  const rows = [
    {
      metric: "Mean Displacement",
      unit: dispUnit,
      fullVal: fullDispMean,
      roiVal: roiDispMean,
    },
    {
      metric: "Maximum Displacement",
      unit: dispUnit,
      fullVal: fullDispMax,
      roiVal: roiDispMax,
    },
    {
      metric: "Mean Principal Strain (ε₁)",
      unit: "dimensionless",
      fullVal: fullP1Mean,
      roiVal: roiP1Mean,
    },
    {
      metric: "Maximum Principal Strain (ε₁)",
      unit: "dimensionless",
      fullVal: fullP1Max,
      roiVal: roiP1Max,
    },
    {
      metric: "Motion Coherence",
      unit: "range [0, 1]",
      fullVal: fullCoh,
      roiVal: roiCoh,
    },
    {
      metric: "Strain Anisotropy",
      unit: "range [0, 1]",
      fullVal: fullAniso,
      roiVal: roiAniso,
    },
    {
      metric: "Strain Entropy",
      unit: "nats",
      fullVal: fullEntropy,
      roiVal: roiEntropy,
    },
  ];

  if (fullEnergy !== undefined || roiEnergy !== undefined) {
    rows.push({
      metric: "Mean Deformation Energy",
      unit: "a.u.",
      fullVal: fullEnergy,
      roiVal: roiEnergy,
    });
  }

  if (fullRadial !== undefined || roiRadial !== undefined) {
    rows.push({
      metric: "Mean Radial Strain",
      unit: "dimensionless",
      fullVal: fullRadial,
      roiVal: roiRadial,
    });
  }

  if (fullCirc !== undefined || roiCirc !== undefined) {
    rows.push({
      metric: "Mean Circumferential Strain",
      unit: "dimensionless",
      fullVal: fullCirc,
      roiVal: roiCirc,
    });
  }

  // Fingerprint data
  const fullFpData = full.fingerprint || result.cardiac_deformation_fingerprint;
  const roiFpData = roi.fingerprint || result.roi_fingerprint;
  const isTracked = scope.mode === "tracked_roi" || Boolean(result.tracking_summary);

  return (
    <section className="roi-comparison-section">
      <div className="roi-comparison-header">
        <div className="roi-comparison-title-box">
          <div className="roi-badge-indicator">
            <span className="roi-pulse-dot"></span>
            <span>{isTracked ? "Tracked ROI Analysis Active" : "Fixed ROI Analysis Active"}</span>
          </div>
          <h3 className="roi-title">
            {isTracked ? "Tracked Region of Interest" : "Region of Interest"} ({scope.roi_type || "Custom"}) vs Full Image Comparison
          </h3>
          <p className="roi-subtitle">
            Analyzing <strong>{roiPx.toLocaleString()} active pixels</strong> ({pctCoverage}% of {fullPx.toLocaleString()} frame pixels)
            {isTracked && result.tracking_summary && (
              <span> &bull; Mean Tracking Confidence: <strong>{(result.tracking_summary.mean_confidence * 100).toFixed(1)}%</strong></span>
            )}.
          </p>
        </div>
      </div>

      {/* Side-by-side / Responsive comparison table */}
      <div className="roi-table-wrapper">
        <table className="roi-comparison-table">
          <thead>
            <tr>
              <th>Deformation Metric</th>
              <th>Unit</th>
              <th className="th-full">Full Image (Global)</th>
              <th className="th-roi">Region of Interest (ROI)</th>
              <th>Relative Diff (Δ)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const diff =
                typeof row.fullVal === "number" && typeof row.roiVal === "number"
                  ? row.roiVal - row.fullVal
                  : null;
              const pctDiff =
                diff !== null && Math.abs(row.fullVal) > 1e-6
                  ? (diff / Math.abs(row.fullVal)) * 100
                  : null;

              return (
                <tr key={idx} className="roi-table-row">
                  <td className="roi-metric-name">
                    <strong>{row.metric}</strong>
                  </td>
                  <td className="roi-metric-unit">
                    <code>{row.unit}</code>
                  </td>
                  <td className="roi-val-full">{formatNumber(row.fullVal, 4)}</td>
                  <td className="roi-val-roi">
                    <strong>{formatNumber(row.roiVal, 4)}</strong>
                  </td>
                  <td className="roi-metric-diff">
                    {diff !== null ? (
                      <span
                        className={`roi-diff-tag ${
                          Math.abs(diff) < 1e-4
                            ? "diff-neutral"
                            : diff > 0
                            ? "diff-pos"
                            : "diff-neg"
                        }`}
                      >
                        {diff > 0 ? "+" : ""}
                        {formatNumber(diff, 4)}
                        {pctDiff !== null ? ` (${diff > 0 ? "+" : ""}${pctDiff.toFixed(1)}%)` : ""}
                      </span>
                    ) : (
                      "N/A"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Dual Fingerprint Comparison */}
      {(roiFpData || fullFpData) && (
        <div className="roi-fingerprint-dual-box">
          <div className="roi-fp-header">
            <h4>10-D Deformation Fingerprint: Full Image vs ROI</h4>
            <div className="roi-fp-tabs">
              <button
                type="button"
                className={`roi-tab-btn ${activeFingerprintTab === "roi" ? "active" : ""}`}
                onClick={() => setActiveFingerprintTab("roi")}
              >
                ROI Fingerprint
              </button>
              <button
                type="button"
                className={`roi-tab-btn ${activeFingerprintTab === "full" ? "active" : ""}`}
                onClick={() => setActiveFingerprintTab("full")}
              >
                Full Image Fingerprint
              </button>
              <button
                type="button"
                className={`roi-tab-btn ${activeFingerprintTab === "both" ? "active" : ""}`}
                onClick={() => setActiveFingerprintTab("both")}
              >
                Side-by-Side Radar
              </button>
            </div>
          </div>

          <div className="roi-fp-grid">
            {(activeFingerprintTab === "roi" || activeFingerprintTab === "both") && roiFpData && (
              <div className="roi-fp-card">
                <div className="roi-fp-label">
                  <span className="badge badge-warning">ROI ({scope.roi_type || "Regional"})</span>
                  <span>10-D Kinematic Fingerprint</span>
                </div>
                <FingerprintChart
                  fingerprintData={roiFpData}
                  fingerprint={roiFpData?.fingerprint}
                />
              </div>
            )}

            {(activeFingerprintTab === "full" || activeFingerprintTab === "both") && fullFpData && (
              <div className="roi-fp-card">
                <div className="roi-fp-label">
                  <span className="badge badge-info">Full Image (Global)</span>
                  <span>10-D Kinematic Fingerprint</span>
                </div>
                <FingerprintChart
                  fingerprintData={fullFpData}
                  fingerprint={fullFpData?.fingerprint}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Scientific Limitation Disclaimer */}
      <div className="roi-comparison-disclaimer">
        <span>ℹ️</span>
        <p>
          <strong>Continuum Biomechanics Note:</strong> Differences between global full-image metrics and regional ROI
          metrics reflect localized deformation gradients and focal strain concentrations. This represents a research-grade
          spatial sub-analysis and does not constitute a diagnostic medical finding or validated anatomical partition.
        </p>
      </div>
    </section>
  );
}

