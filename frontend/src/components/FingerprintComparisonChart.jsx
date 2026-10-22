import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Tooltip,
} from "recharts";

const SERIES_COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#8b5cf6", // Purple
  "#ec4899", // Pink
];

const DIMENSION_LABELS = {
  D_mean: "D_mean (Mean Disp)",
  D_max: "D_max (Max Disp)",
  epsilon_mean: "ε_mean (Mean Strain)",
  epsilon_max: "ε_max (Peak Strain)",
  epsilon_principal: "ε_p1 (Principal Strain)",
  AI: "AI (Anisotropy)",
  H: "H (Strain Entropy)",
  G_epsilon: "G_ε (Gradient)",
  C: "C (Coherence)",
  TSI: "TSI (Stability)",
};

export default function FingerprintComparisonChart({ fingerprintComparison }) {
  if (!fingerprintComparison || !fingerprintComparison.series || fingerprintComparison.series.length === 0) {
    return (
      <div className="chart-empty-state">
        <p>No cardiac deformation fingerprint vectors available for comparison.</p>
      </div>
    );
  }

  const { dimensions, series } = fingerprintComparison;

  // Build chart-ready data points across all 10 dimensions
  const radarData = dimensions.map((dimKey, dimIdx) => {
    const item = {
      dimension: DIMENSION_LABELS[dimKey] || dimKey,
      dimKey,
    };
    series.forEach((s, sIdx) => {
      // Use normalized vector element if available, else raw dimension value
      const vectorVal = s.vector && s.vector[dimIdx] !== undefined ? s.vector[dimIdx] : null;
      item[`series_${sIdx}`] = vectorVal !== null ? Number(vectorVal.toFixed(4)) : 0;
      item[`raw_${sIdx}`] = s.dimensions ? s.dimensions[dimKey] : null;
    });
    return item;
  });

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="radar-comparison-tooltip">
          <p className="tooltip-title">
            <strong>{label}</strong>
          </p>
          <div className="tooltip-series-list">
            {payload.map((entry, idx) => {
              const seriesObj = series[idx];
              const rawVal = entry.payload[`raw_${idx}`];
              return (
                <div key={idx} className="tooltip-series-row" style={{ color: entry.stroke }}>
                  <span>{seriesObj ? seriesObj.label : entry.name}:</span>
                  <strong>{entry.value} (Norm)</strong>
                  {rawVal !== null && rawVal !== undefined && (
                    <span className="tooltip-raw-val">[{rawVal}]</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="fingerprint-comparison-card">
      <div className="chart-header">
        <h4>Cardiac Deformation Fingerprint Comparison</h4>
        <p className="chart-subtitle">
          Superimposed 10-dimensional normalized deformation fingerprints across selected analyses
        </p>
      </div>

      <div className="chart-container" style={{ width: "100%", height: 380 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
            <PolarGrid stroke="rgba(148, 163, 184, 0.25)" />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fill: "var(--text-main)", fontSize: 11 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 1]}
              stroke="#64748b"
              tick={{ fontSize: 9 }}
              tickCount={5}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend verticalAlign="bottom" height={36} iconSize={10} />
            {series.map((s, idx) => (
              <Radar
                key={s.analysis_id || idx}
                name={s.label || `Analysis ${idx + 1}`}
                dataKey={`series_${idx}`}
                stroke={SERIES_COLORS[idx % SERIES_COLORS.length]}
                fill={SERIES_COLORS[idx % SERIES_COLORS.length]}
                fillOpacity={0.2}
                strokeWidth={2}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="fingerprint-note">
        <small>
          <strong>Scientific Methodology:</strong> Vector axes represent 10 canonical deformation descriptors
          scaled to [0, 1]. Higher values indicate higher regional magnitude or spatial entropy.
          Multi-series superposition illustrates mathematical kinematic similarity without implying clinical normality or disease.
        </small>
      </div>
    </div>
  );
}

