import React, { useState } from "react";

/**
 * MetricInspector
 *
 * Displays detailed computational statistics, units, mathematical interpretations,
 * point/pixel inspection, region summary (ROI), computational quality warning,
 * and collapsible methodology derivation for the selected metric.
 */

const METRIC_DEFINITIONS = {
  displacement: {
    title: "Displacement Magnitude",
    unitDefault: "px",
    description: "Euclidean magnitude of dense 2D optical-flow motion vectors between image states.",
    formula: "D(x, y) = \\sqrt{u(x, y)^2 + v(x, y)^2}",
    interpretation:
      "Mean displacement represents the average magnitude of estimated image motion across valid pixels in the analyzed field.",
    tooltip: "Estimated image motion between analyzed states.",
  },
  motion_vectors: {
    title: "Motion Vectors (u, v)",
    unitDefault: "px",
    description: "Horizontal (u) and vertical (v) displacement components derived from dense Farnebäck flow.",
    formula: "\\vec{d} = (u, v)^T",
    interpretation: "Vector components characterize directional velocity and local trajectory.",
    tooltip: "2D directional velocity field.",
  },
  exx: {
    title: "Normal Strain Exx",
    unitDefault: "dimensionless",
    description: "Horizontal spatial gradient component of displacement field.",
    formula: "E_{xx} = \\frac{\\partial u}{\\partial x}",
    interpretation: "Positive values describe horizontal elongation; negative values describe horizontal shortening.",
    tooltip: "Horizontal normal strain component.",
  },
  eyy: {
    title: "Normal Strain Eyy",
    unitDefault: "dimensionless",
    description: "Vertical spatial gradient component of displacement field.",
    formula: "E_{yy} = \\frac{\\partial v}{\\partial y}",
    interpretation: "Positive values describe vertical elongation; negative values describe vertical shortening.",
    tooltip: "Vertical normal strain component.",
  },
  exy: {
    title: "Shear Strain Exy",
    unitDefault: "dimensionless",
    description: "Engineering shear strain indicating angular distortion between orthogonal coordinate axes.",
    formula: "E_{xy} = \\frac{1}{2} \\left(\\frac{\\partial u}{\\partial y} + \\frac{\\partial v}{\\partial x}\\right)",
    interpretation: "Quantifies rotational shear and angular deformation.",
    tooltip: "Shear strain component describing angular distortion.",
  },
  principal_strain: {
    title: "Principal Strain (P1)",
    unitDefault: "dimensionless",
    description: "Maximal eigenvalue of the 2D infinitesimal strain tensor.",
    formula: "\\lambda_{1,2} = \\frac{E_{xx} + E_{yy}}{2} \\pm \\sqrt{\\left(\\frac{E_{xx} - E_{yy}}{2}\\right)^2 + E_{xy}^2}",
    interpretation: "Eigenvalue-based principal strain representing maximal tensile deformation along principal axes.",
    tooltip: "Eigenvalue-based principal strain derived from the 2D strain tensor.",
  },
  principal_direction: {
    title: "Principal Direction (θ)",
    unitDefault: "deg",
    description: "Orientation angle of the principal strain eigenvector.",
    formula: "\\theta = \\frac{1}{2} \\arctan\\left(\\frac{2 E_{xy}}{E_{xx} - E_{yy}}\\right)",
    interpretation: "Specifies the dominant angle of maximal deformation relative to the image coordinate frame.",
    tooltip: "Orientation angle of dominant deformation axis.",
  },
  radial: {
    title: "Radial Deformation",
    unitDefault: "dimensionless",
    description: "Projection of displacement along the radial vector connecting centroid to pixel.",
    formula: "d_r = \\vec{d} \\cdot \\hat{r}",
    interpretation: "Positive indicates radial expansion (outward motion); negative indicates radial contraction (inward motion).",
    tooltip: "Radial component of motion relative to estimated center.",
  },
  circumferential: {
    title: "Circumferential Deformation",
    unitDefault: "dimensionless",
    description: "Projection of displacement along the tangential vector orthogonal to the radial vector.",
    formula: "d_\\theta = \\vec{d} \\cdot \\hat{\\theta}",
    interpretation: "Quantifies rotational motion and circumferential tangential sliding.",
    tooltip: "Circumferential tangential component of deformation.",
  },
  coherence: {
    title: "Motion Coherence",
    unitDefault: "normalized [0, 1]",
    description: "Ratio of the norm of the local mean vector to the mean of local vector norms.",
    formula: "C = \\frac{\\|\\sum_{i} \\vec{v}_i\\|}{\\sum_{i} \\|\\vec{v}_i\\| + \\epsilon}",
    interpretation: "Measures local alignment and directional uniformity of optical flow vectors.",
    tooltip: "Measure summarizing local consistency of estimated motion.",
  },
  anisotropy: {
    title: "Strain Anisotropy",
    unitDefault: "dimensionless [0, 1]",
    description: "Normalized difference between principal eigenvalues.",
    formula: "A = \\frac{|\\lambda_1 - \\lambda_2|}{|\\lambda_1| + |\\lambda_2| + \\epsilon}",
    interpretation: "0 indicates isotropic uniform scaling; 1 indicates purely unidirectional deformation.",
    tooltip: "Measure describing directional difference between principal deformation components.",
  },
  gradient: {
    title: "Strain Gradient",
    unitDefault: "dimensionless / px",
    description: "Spatial rate of change of principal strain magnitude.",
    formula: "\\nabla E = \\sqrt{\\left(\\frac{\\partial \\lambda_1}{\\partial x}\\right)^2 + \\left(\\frac{\\partial \\lambda_1}{\\partial y}\\right)^2}",
    interpretation: "High values identify spatial boundaries with steep strain transitions.",
    tooltip: "Spatial rate of change of strain magnitude.",
  },
  energy: {
    title: "Deformation Energy",
    unitDefault: "dimensionless",
    description: "Second invariant representing total strain energy density in small-strain approximation.",
    formula: "W = \\frac{1}{2} (E_{xx}^2 + E_{yy}^2 + 2 E_{xy}^2)",
    interpretation: "Summarizes the total computational strain energy across the image domain.",
    tooltip: "Computational deformation energy density.",
  },
};

function formatVal(val, decimals = 4) {
  if (val === null || val === undefined) return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return val.toExponential(decimals);
  }
  return val.toFixed(decimals);
}

export default function MetricInspector({
  selectedMode = "displacement",
  analysisRecord = null,
  sampledPixel = null,
}) {
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  // Extract calibration
  const cal = analysisRecord?.calibration;
  const isCalibrated = Boolean(cal?.enabled && cal?.pixel_spacing_x);
  const calUnit = cal?.unit || "mm";

  // Resolve active metric definition
  const defKey = Object.keys(METRIC_DEFINITIONS).find((k) =>
    selectedMode.toLowerCase().includes(k)
  ) || "displacement";
  const def = METRIC_DEFINITIONS[defKey];

  // Derive stats for the active metric
  const dispStats =
    analysisRecord?.displacement ||
    analysisRecord?.displacement_statistics ||
    {};
  const strainStats = analysisRecord?.strain_statistics || {};
  const advStats = analysisRecord?.advanced_metrics || {};
  const cardiacDef = analysisRecord?.cardiac_deformation || {};
  const qc = analysisRecord?.quality_control;
  const roiMetrics = analysisRecord?.roi_metrics;
  const analysisScope = analysisRecord?.analysis_scope;

  // Resolve numerical stats based on metric
  let mean = null;
  let min = null;
  let max = null;
  let std = null;
  let activeUnit = def.unitDefault;

  if (defKey === "displacement") {
    if (isCalibrated && dispStats.physical_space) {
      mean = dispStats.physical_space.mean_displacement;
      max = dispStats.physical_space.max_displacement;
      min = dispStats.physical_space.min_displacement;
      std = dispStats.physical_space.std_displacement;
      activeUnit = calUnit;
    } else {
      const pxSpace = dispStats.pixel_space || dispStats;
      mean = pxSpace.mean_displacement ?? pxSpace.mean;
      max = pxSpace.max_displacement ?? pxSpace.max;
      min = pxSpace.min_displacement ?? pxSpace.min;
      std = pxSpace.std_displacement ?? pxSpace.std;
      activeUnit = "px";
    }
  } else if (defKey === "principal_strain") {
    const p1 = strainStats.principal_strain_1 || {};
    mean = p1.mean;
    min = p1.min;
    max = p1.max;
    std = p1.std;
  } else if (defKey === "exx") {
    const exx = strainStats.exx || {};
    mean = exx.mean;
    min = exx.min;
    max = exx.max;
    std = exx.std;
  } else if (defKey === "eyy") {
    const eyy = strainStats.eyy || {};
    mean = eyy.mean;
    min = eyy.min;
    max = eyy.max;
    std = eyy.std;
  } else if (defKey === "exy") {
    const exy = strainStats.exy || {};
    mean = exy.mean;
    min = exy.min;
    max = exy.max;
    std = exy.std;
  } else if (defKey === "principal_direction") {
    mean = analysisRecord?.mean_principal_direction_radians
      ? (analysisRecord.mean_principal_direction_radians * 180) / Math.PI
      : null;
    activeUnit = "deg";
  } else if (defKey === "coherence") {
    const coh = advStats.motion_coherence || {};
    mean = coh.mean;
    min = coh.min;
    max = coh.max;
  } else if (defKey === "anisotropy") {
    const ani = advStats.anisotropy || {};
    mean = ani.mean;
    max = ani.max;
  } else if (defKey === "gradient") {
    const grad = advStats.strain_gradient || {};
    mean = grad.mean;
    max = grad.max;
  } else if (defKey === "energy") {
    const en = advStats.deformation_energy || {};
    mean = en.mean;
    max = en.max;
  } else if (defKey === "radial") {
    const rad = cardiacDef.radial || {};
    mean = rad.mean;
    min = rad.min;
    max = rad.max;
  } else if (defKey === "circumferential") {
    const circ = cardiacDef.circumferential || {};
    mean = circ.mean;
    min = circ.min;
    max = circ.max;
  }

  // Quality assessment values
  const qcScore = qc?.quality_score ?? null;
  const qcLevel = qc?.quality_level ?? "Unassessed";
  const isQcLow = qcLevel === "Low";

  return (
    <div className="sci-metric-inspector">
      {/* Quality Control Warning Bar */}
      <div className={`sci-qc-bar qc-level-${qcLevel.toLowerCase()}`}>
        <div className="sci-qc-header">
          <span className="sci-qc-title">⚙️ Computational Quality</span>
          {qcScore !== null ? (
            <span className="sci-qc-score">
              {qcScore} / 100 &nbsp;({qcLevel})
            </span>
          ) : (
            <span className="sci-qc-score">Quality assessment not available</span>
          )}
        </div>
        {isQcLow && (
          <p className="sci-qc-warning-msg">
            ⚠️ Interpret quantitative visualization with caution because computational
            quality checks identified potential motion or tracking inconsistencies.
          </p>
        )}
      </div>

      {/* Metric Title & Tooltip */}
      <div className="sci-inspector-header">
        <h3 className="sci-metric-name">{def.title}</h3>
        <span className="sci-tooltip-pill" title={def.tooltip}>
          ℹ️ {def.tooltip}
        </span>
      </div>

      {/* Primary Statistics Grid */}
      <div className="sci-stats-grid">
        <div className="sci-stat-item">
          <span className="sci-stat-lbl">Mean</span>
          <span className="sci-stat-val">{formatVal(mean)}</span>
        </div>
        <div className="sci-stat-item">
          <span className="sci-stat-lbl">Min</span>
          <span className="sci-stat-val">{formatVal(min)}</span>
        </div>
        <div className="sci-stat-item">
          <span className="sci-stat-lbl">Max</span>
          <span className="sci-stat-val">{formatVal(max)}</span>
        </div>
        <div className="sci-stat-item">
          <span className="sci-stat-lbl">Std Dev</span>
          <span className="sci-stat-val">{formatVal(std)}</span>
        </div>
        <div className="sci-stat-item" style={{ gridColumn: "span 2" }}>
          <span className="sci-stat-lbl">Measurement Unit</span>
          <span className="sci-stat-val" style={{ fontSize: "12px", color: "#0284c7" }}>
            {activeUnit}
          </span>
        </div>
      </div>

      {/* Computational Description & Interpretation */}
      <div className="sci-inspector-section">
        <h4 className="sci-section-subtitle">Mathematical Interpretation</h4>
        <p className="sci-interpretation-text">{def.interpretation}</p>
        <p className="sci-desc-text">{def.description}</p>
      </div>

      {/* Point / Pixel Inspection Details */}
      <div className="sci-inspector-section sci-pixel-inspection-box">
        <h4 className="sci-section-subtitle">🎯 Sampled Point Inspection</h4>
        {sampledPixel ? (
          <div className="sci-pixel-grid">
            <div className="sci-pixel-row">
              <span className="lbl">Coordinates (X, Y):</span>
              <span className="val">
                {sampledPixel.x}, {sampledPixel.y} px
              </span>
            </div>
            {sampledPixel.rgb && (
              <div className="sci-pixel-row">
                <span className="lbl">Pixel Color &amp; Intensity:</span>
                <span className="val">
                  <span
                    className="sci-color-dot"
                    style={{ backgroundColor: sampledPixel.rgb }}
                  />
                  {sampledPixel.intensity} / 255
                </span>
              </div>
            )}
            <div className="sci-pixel-row">
              <span className="lbl">Estimated {def.title}:</span>
              <span className="val highlight">
                {sampledPixel.estimatedValue !== undefined
                  ? `${sampledPixel.estimatedValue} ${activeUnit}`
                  : "Not available for this analysis."}
              </span>
            </div>
            <div className="sci-pixel-row">
              <span className="lbl">Motion Vector (u, v):</span>
              <span className="val">
                {sampledPixel.u !== undefined
                  ? `u: ${sampledPixel.u}, v: ${sampledPixel.v}`
                  : "Not available for this analysis."}
              </span>
            </div>
          </div>
        ) : (
          <p className="sci-subtle-hint">
            Click on the image visualization to inspect local pixel coordinates, RGB intensity,
            and estimated deformation metrics.
          </p>
        )}
      </div>

      {/* Region Summary (ROI) */}
      <div className="sci-inspector-section sci-roi-summary-box">
        <h4 className="sci-section-subtitle">📍 Region of Interest (ROI) Summary</h4>
        {roiMetrics ? (
          <div className="sci-roi-metrics-grid">
            <div className="sci-roi-metric-item">
              <span className="lbl">ROI Mode</span>
              <span className="val">{(analysisScope?.mode || "ROI").toUpperCase()}</span>
            </div>
            <div className="sci-roi-metric-item">
              <span className="lbl">Area / Pixel Count</span>
              <span className="val">
                {roiMetrics.pixel_count ? `${roiMetrics.pixel_count} px` : "N/A"}
              </span>
            </div>
            <div className="sci-roi-metric-item">
              <span className="lbl">Mean Displacement</span>
              <span className="val">
                {formatVal(
                  roiMetrics.displacement?.pixel_space?.mean_displacement ??
                    roiMetrics.displacement?.mean_displacement
                )}{" "}
                px
              </span>
            </div>
            <div className="sci-roi-metric-item">
              <span className="lbl">Mean Principal Strain</span>
              <span className="val">
                {formatVal(roiMetrics.strain_statistics?.principal_strain_1?.mean)}
              </span>
            </div>
            <div className="sci-roi-metric-item">
              <span className="lbl">Motion Coherence</span>
              <span className="val">
                {formatVal(roiMetrics.advanced_metrics?.motion_coherence?.mean)}
              </span>
            </div>
            <div className="sci-roi-metric-item">
              <span className="lbl">Strain Anisotropy</span>
              <span className="val">
                {formatVal(roiMetrics.advanced_metrics?.anisotropy?.mean)}
              </span>
            </div>
          </div>
        ) : (
          <p className="sci-subtle-hint">No ROI selected for this analysis.</p>
        )}
      </div>

      {/* Units Panel */}
      <div className="sci-inspector-section sci-units-box">
        <h4 className="sci-section-subtitle">📐 Dimensionality &amp; Physical Units</h4>
        <div className="sci-units-list">
          <div className="sci-unit-row">
            <span>Image-Space Displacement:</span>
            <strong>pixels (px)</strong>
          </div>
          <div className="sci-unit-row">
            <span>Physical Displacement:</span>
            <strong>{isCalibrated ? `${calUnit} (Calibrated)` : "Uncalibrated (px only)"}</strong>
          </div>
          <div className="sci-unit-row">
            <span>Infinitesimal Strain Tensor:</span>
            <strong>dimensionless</strong>
          </div>
          <div className="sci-unit-row">
            <span>Principal Directions / Angles:</span>
            <strong>degrees (°)</strong>
          </div>
        </div>
      </div>

      {/* Methodology Collapsible Section */}
      <div className="sci-inspector-section sci-methodology-accordion">
        <button
          className="sci-accordion-header-btn"
          onClick={() => setMethodologyOpen(!methodologyOpen)}
        >
          <span>📐 How this measurement was calculated</span>
          <span>{methodologyOpen ? "▲" : "▼"}</span>
        </button>
        {methodologyOpen && (
          <div className="sci-accordion-body">
            <div className="sci-formula-box">
              <code>{def.formula}</code>
            </div>
            <p className="sci-formula-explanation">
              Calculated using dense Gunnar Farnebäck polynomial expansion optical flow and spatial
              derivative operators on 2D cardiac frames. Strain eigenvalues are derived from the
              symmetric Green-Lagrange infinitesimal tensor approximation.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

