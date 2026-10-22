function formatVal(val, decimals = 4, suffix = "") {
  if (val === null || val === undefined || val === "N/A") return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return `${val.toExponential(decimals)}${suffix}`;
  }
  return `${val.toFixed(decimals)}${suffix}`;
}

export default function SummaryCards({
  meanDisplacement,
  maxDisplacement,
  meanPrincipalStrain,
  maxPrincipalStrain,
  motionCoherence,
  anisotropy,
  strainEntropy,
  temporalStability,
  calibration = null,
  physicalDisplacement = null,
}) {
  const isCalibrated = Boolean(
    calibration?.enabled &&
    (physicalDisplacement?.mean !== undefined || physicalDisplacement?.mean_displacement !== undefined)
  );

  const dispUnit = isCalibrated ? (calibration?.unit || "mm") : "px";
  const dispUnitLabel = isCalibrated
    ? `Physical Distance (${dispUnit})`
    : "Image Pixels (px)";
  const dispMeasurementBadge = isCalibrated
    ? "Spatially calibrated measurement"
    : "Image-space measurement";

  const meanDispVal = isCalibrated
    ? (physicalDisplacement?.mean ?? physicalDisplacement?.mean_displacement ?? meanDisplacement)
    : meanDisplacement;

  const maxDispVal = isCalibrated
    ? (physicalDisplacement?.max ?? physicalDisplacement?.max_displacement ?? maxDisplacement)
    : maxDisplacement;

  const cards = [
    {
      title: "Mean Displacement",
      value: formatVal(meanDispVal, 4, ` ${dispUnit}`),
      unit: dispUnitLabel,
      badge: dispMeasurementBadge,
      info: isCalibrated
        ? `Average magnitude converted to physical units (${dispUnit}) using spatial pixel spacing.`
        : "Average Euclidean magnitude of displacement vector field across analyzed pixels.",
      accent: "accent-blue",
    },
    {
      title: "Maximum Displacement",
      value: formatVal(maxDispVal, 4, ` ${dispUnit}`),
      unit: dispUnitLabel,
      badge: dispMeasurementBadge,
      info: isCalibrated
        ? `Peak regional displacement converted to physical units (${dispUnit}).`
        : "Peak apparent regional displacement observed in the flow field.",
      accent: "accent-indigo",
    },
    {
      title: "Mean Principal Strain",
      value: formatVal(meanPrincipalStrain, 4),
      unit: "Dimensionless",
      info: "Spatial mean of major principal strain (maximum eigenvalue of strain tensor).",
      accent: "accent-purple",
    },
    {
      title: "Maximum Principal Strain",
      value: formatVal(maxPrincipalStrain, 4),
      unit: "Dimensionless",
      info: "Maximum regional principal deformation amplitude in the image space.",
      accent: "accent-pink",
    },
    {
      title: "Motion Coherence",
      value: formatVal(motionCoherence, 4),
      unit: "Range [0, 1]",
      info: "Local cosine alignment of neighboring displacement vectors.",
      accent: "accent-orange",
    },
    {
      title: "Strain Anisotropy",
      value: formatVal(anisotropy, 4),
      unit: "Range [0, 1]",
      info: "Directional asymmetry index between orthogonal principal strain fields.",
      accent: "accent-amber",
    },
    {
      title: "Strain Entropy",
      value: formatVal(strainEntropy, 4),
      unit: "Nats / Bits",
      info: "Shannon entropy measuring dispersion of regional deformation magnitudes.",
      accent: "accent-teal",
    },
    {
      title: "Temporal Stability Index",
      value: formatVal(temporalStability, 4),
      unit: "Range [0, 1]",
      info: "Sequence consistency metric 1/(1+var) evaluating trajectory smoothness.",
      accent: "accent-green",
    },
  ];

  return (
    <div className="summary-cards-container">
      <div className="summary-cards-grid">
        {cards.map((c) => (
          <div key={c.title} className={`summary-metric-card ${c.accent}`}>
            <div className="card-top">
              <span className="card-title">{c.title}</span>
              <span className="info-tooltip-trigger" title={c.info}>
                ℹ
              </span>
            </div>
            <div className="card-value-display">
              <span className="card-num">{c.value}</span>
            </div>
            <div className="card-bottom">
              <span className="card-unit">{c.unit}</span>
              {c.badge && (
                <span className={`card-measurement-badge ${isCalibrated ? "badge-calibrated" : "badge-uncalibrated"}`}>
                  {c.badge}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

