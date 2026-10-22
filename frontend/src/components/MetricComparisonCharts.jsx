import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

const BAR_COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#8b5cf6", // Purple
  "#ec4899", // Pink
];

export default function MetricComparisonCharts({ chartMetrics }) {
  if (!chartMetrics || chartMetrics.length === 0) return null;

  return (
    <div className="metric-comparison-section">
      <div className="chart-header">
        <h4>Key Quantitative Metrics Comparison</h4>
        <p className="chart-subtitle">
          Direct quantitative bar comparisons across selected analyses for primary kinematic parameters
        </p>
      </div>

      <div className="metric-charts-grid">
        {chartMetrics.map((metric) => {
          const chartData = metric.data || [];
          const allZeroOrNull = chartData.every(
            (d) => d.value === null || d.value === undefined || d.value === 0
          );

          return (
            <div key={metric.key} className="metric-chart-card">
              <div className="metric-chart-header">
                <h5>{metric.title}</h5>
                <span className="metric-unit-badge">{metric.unit}</span>
              </div>

              {allZeroOrNull && !chartData.some((d) => d.value !== null) ? (
                <div className="metric-chart-empty">
                  <span>Parameter unavailable in selected analyses</span>
                </div>
              ) : (
                <div style={{ width: "100%", height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData}
                      margin={{ top: 12, right: 16, bottom: 10, left: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                      <XAxis
                        dataKey="label"
                        stroke="#64748b"
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        stroke="#64748b"
                        tick={{ fontSize: 10 }}
                        tickFormatter={(v) => (Math.abs(v) >= 1000 ? v.toExponential(1) : v)}
                      />
                      <Tooltip
                        formatter={(val) => [
                          val !== null && val !== undefined ? `${val} ${metric.unit}` : "N/A",
                          metric.title,
                        ]}
                        contentStyle={{
                          background: "var(--bg-surface)",
                          borderColor: "var(--border-color)",
                          borderRadius: 6,
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                        {chartData.map((_, idx) => (
                          <Cell
                            key={`cell-${idx}`}
                            fill={BAR_COLORS[idx % BAR_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

