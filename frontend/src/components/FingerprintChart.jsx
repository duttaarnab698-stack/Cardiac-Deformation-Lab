import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
} from "recharts";

const DIMENSION_CONFIG = [
  { key: "D_mean", name: "Mean Displacement", symbol: "D_mean", desc: "Average motion magnitude (px)" },
  { key: "D_max", name: "Max Displacement", symbol: "D_max", desc: "Peak motion amplitude (px)" },
  { key: "epsilon_mean", name: "Mean Strain", symbol: "ε_mean", desc: "Average representative strain" },
  { key: "epsilon_max", name: "Max Strain", symbol: "ε_max", desc: "Peak representative strain" },
  { key: "epsilon_principal", name: "Principal Strain", symbol: "ε_principal", desc: "Dominant local deformation" },
  { key: "AI", name: "Anisotropy", symbol: "AI", desc: "Directional asymmetry index" },
  { key: "H", name: "Strain Entropy", symbol: "H", desc: "Histogram dispersion entropy" },
  { key: "G_epsilon", name: "Strain Gradient", symbol: "G_ε", desc: "Spatial rate of strain change" },
  { key: "C", name: "Motion Coherence", symbol: "C", desc: "Local vector directional alignment" },
  { key: "TSI", name: "Temporal Stability", symbol: "TSI", desc: "Multi-frame trajectory consistency" },
];

function formatVal(val, decimals = 4) {
  if (val === null || val === undefined || val === "N/A") return "N/A";
  if (typeof val !== "number") return String(val);
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return val.toExponential(decimals);
  }
  return val.toFixed(decimals);
}

export default function FingerprintChart({ fingerprintData, fingerprint }) {
  // Support both fingerprintData prop (with vector, normalized_vector) or plain fingerprint object
  const activeFpData = fingerprintData || {};
  const fpMap = fingerprint || activeFpData.fingerprint || {};

  const normalizedVector = activeFpData.normalized_vector || [];
  const rawVector = activeFpData.vector || [];

  const radarData = DIMENSION_CONFIG.map((dim, idx) => {
    // Attempt from normalized vector first
    let norm = normalizedVector[idx];
    let raw = rawVector[idx];

    // If raw is not in vector, pull directly from fpMap object
    if ((raw === undefined || raw === null) && fpMap[dim.key] !== undefined) {
      raw = fpMap[dim.key];
    }

    const isNormValid = norm !== null && norm !== undefined && !isNaN(norm);
    let normalizedScore = isNormValid ? Number(norm) : 0;

    // Fallback normalization if only raw is provided
    if (!isNormValid && typeof raw === "number" && !isNaN(raw)) {
      normalizedScore = Math.min(Math.max(raw, 0), 1);
    }

    return {
      dimension: dim.symbol,
      fullName: dim.name,
      description: dim.desc,
      normalizedScore,
      rawValue: raw,
    };
  });

  return (
    <div className="fingerprint-enhanced-container">
      <div className="fingerprint-visual-row">
        {/* Radar Chart */}
        <div className="fingerprint-radar-box">
          <div className="chart-header">
            <h4>10-D Cardiac Deformation Fingerprint Radar</h4>
            <p className="chart-subtitle">
              Normalized multi-dimensional deformation profile (scaled 0 &rarr; 1 for relative visual comparison)
            </p>
          </div>
          <div style={{ width: "100%", height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="var(--border-color, #e2e8f0)" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fill: "var(--text-main, #334155)", fontSize: 11, fontWeight: 600 }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 1]}
                  tick={{ fill: "var(--text-muted, #94a3b8)", fontSize: 9 }}
                  stroke="var(--border-color, #e2e8f0)"
                />
                <Radar
                  name="Deformation Profile"
                  dataKey="normalizedScore"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.35}
                />
                <Tooltip
                  formatter={(value, name, item) => [
                    `${formatVal(value)} (raw: ${formatVal(item.payload.rawValue)})`,
                    "Normalized",
                  ]}
                  contentStyle={{
                    backgroundColor: "var(--bg-surface, #ffffff)",
                    border: "1px solid var(--border-color, #e2e8f0)",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "var(--text-main, #0f172a)",
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Compact 10-D Dimension Status Table */}
        <div className="fingerprint-table-box">
          <h4 className="table-title">Fingerprint Dimension Components</h4>
          <div className="fp-compact-table-container">
            <table className="fp-compact-table">
              <thead>
                <tr>
                  <th>Dimension</th>
                  <th>Raw Value</th>
                  <th>Normalized</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {DIMENSION_CONFIG.map((dim, idx) => {
                  const entry = radarData[idx];
                  const hasVal = entry.rawValue !== null && entry.rawValue !== undefined && entry.rawValue !== "N/A";
                  return (
                    <tr key={dim.key}>
                      <td>
                        <span className="dim-symbol">{dim.symbol}</span>
                        <span className="dim-name">{dim.name}</span>
                      </td>
                      <td className="dim-val-cell">
                        <strong>{formatVal(entry.rawValue)}</strong>
                      </td>
                      <td className="dim-norm-cell">
                        {hasVal ? formatVal(entry.normalizedScore, 3) : "—"}
                      </td>
                      <td>
                        <span
                          className={`fp-status-tag ${
                            hasVal ? "status-computed" : "status-missing"
                          }`}
                        >
                          {hasVal ? "Computed" : "Missing"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
