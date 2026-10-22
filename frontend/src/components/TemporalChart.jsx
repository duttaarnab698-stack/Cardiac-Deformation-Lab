import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

function formatValue(val) {
  if (typeof val !== "number") return val;
  if (Math.abs(val) > 0 && (Math.abs(val) < 0.0001 || Math.abs(val) >= 10000)) {
    return val.toExponential(4);
  }
  return val.toFixed(4);
}

export default function TemporalChart({ data }) {
  if (!data) return null;

  const p1Values = data.principal_strain_1?.values || [];
  const p2Values = data.principal_strain_2?.values || [];
  const pairCount = Math.max(p1Values.length, p2Values.length);

  if (pairCount === 0) {
    return (
      <div className="chart-empty-state">
        <p>No temporal strain values available to plot.</p>
      </div>
    );
  }

  // Construct chart-ready data points
  const chartData = [];
  for (let i = 0; i < pairCount; i++) {
    chartData.push({
      pair: `Pair ${i + 1} (${i + 1}→${i + 2})`,
      pairIndex: i + 1,
      "Principal Strain 1": p1Values[i] !== undefined ? p1Values[i] : null,
      "Principal Strain 2": p2Values[i] !== undefined ? p2Values[i] : null,
    });
  }

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h4>Temporal Principal Strain Trajectory</h4>
        <p className="chart-subtitle">
          Frame-to-frame evolution of orthogonal principal strain components
        </p>
      </div>

      <div className="chart-container" style={{ width: "100%", height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 16, right: 30, left: 20, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="pair"
              stroke="#6b7280"
              fontSize={12}
              tickLine={false}
              label={{
                value: "Consecutive Frame Pairs",
                position: "insideBottom",
                offset: -12,
                fontSize: 12,
                fill: "#4b5563",
              }}
            />
            <YAxis
              stroke="#6b7280"
              fontSize={12}
              tickFormatter={(v) => formatValue(v)}
              label={{
                value: "Principal Strain",
                angle: -90,
                position: "insideLeft",
                offset: -8,
                fontSize: 12,
                fill: "#4b5563",
              }}
            />
            <Tooltip
              formatter={(val, name) => [formatValue(val), name]}
              contentStyle={{
                backgroundColor: "#ffffff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                fontSize: "13px",
                boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
              }}
            />
            <Legend
              verticalAlign="top"
              height={36}
              wrapperStyle={{ fontSize: "13px" }}
            />
            <Line
              type="monotone"
              dataKey="Principal Strain 1"
              stroke="#4f46e5"
              strokeWidth={2.5}
              activeDot={{ r: 6 }}
              dot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="Principal Strain 2"
              stroke="#06b6d4"
              strokeWidth={2.5}
              activeDot={{ r: 6 }}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

