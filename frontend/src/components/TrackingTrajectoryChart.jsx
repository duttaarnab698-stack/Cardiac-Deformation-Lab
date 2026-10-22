import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";

export default function TrackingTrajectoryChart({ trackingPath, trackingSummary }) {
  if (!trackingPath || trackingPath.length === 0) {
    return null;
  }

  const chartData = trackingPath.map((item) => ({
    frame: `Frame ${item.frame_index}`,
    frameIndex: item.frame_index,
    confidence: item.tracking_confidence ?? 0,
    centerX: item.roi?.center?.x ?? null,
    centerY: item.roi?.center?.y ?? null,
    displacement: item.displacement?.magnitude ?? 0,
    status: item.status || "valid",
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="tracking-chart-tooltip">
          <p className="tooltip-title">
            <strong>{label}</strong> ({data.status.toUpperCase()})
          </p>
          <p className="tooltip-item conf">
            <span>Confidence:</span> <strong>{(data.confidence * 100).toFixed(1)}%</strong>
          </p>
          {data.centerX !== null && data.centerY !== null && (
            <p className="tooltip-item pos">
              <span>Center:</span> ({data.centerX.toFixed(1)}, {data.centerY.toFixed(1)}) px
            </p>
          )}
          <p className="tooltip-item disp">
            <span>Step Motion:</span> {data.displacement.toFixed(2)} px
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="tracking-trajectory-card">
      <div className="chart-header">
        <h4>ROI Tracking Trajectory &amp; Confidence</h4>
        <p className="chart-subtitle">
          Frame-to-frame optical flow tracking confidence and ROI centroid coordinates
        </p>
      </div>

      {trackingSummary && (
        <div className="tracking-summary-badges">
          <div className="track-badge">
            <span className="badge-label">Mean Confidence</span>
            <span className="badge-value">
              {trackingSummary.mean_confidence !== undefined
                ? `${(trackingSummary.mean_confidence * 100).toFixed(1)}%`
                : "N/A"}
            </span>
          </div>
          <div className="track-badge">
            <span className="badge-label">Min Confidence</span>
            <span className="badge-value">
              {trackingSummary.min_confidence !== undefined
                ? `${(trackingSummary.min_confidence * 100).toFixed(1)}%`
                : "N/A"}
            </span>
          </div>
          <div className="track-badge">
            <span className="badge-label">Tracked Frames</span>
            <span className="badge-value">
              {trackingSummary.successful_tracking_frames} / {trackingSummary.frame_count}
            </span>
          </div>
          <div className="track-badge">
            <span className="badge-label">Failed Frames</span>
            <span className={`badge-value ${trackingSummary.failed_tracking_frames > 0 ? "failed-text" : ""}`}>
              {trackingSummary.failed_tracking_frames}
            </span>
          </div>
        </div>
      )}

      <div className="chart-container" style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 10, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
            <XAxis
              dataKey="frame"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis
              yAxisId="conf"
              domain={[0, 1]}
              stroke="#3b82f6"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              label={{
                value: "Confidence",
                angle: -90,
                position: "insideLeft",
                fill: "#3b82f6",
                fontSize: 12,
              }}
            />
            <YAxis
              yAxisId="pos"
              orientation="right"
              stroke="#8b5cf6"
              tick={{ fontSize: 11 }}
              label={{
                value: "Centroid (px)",
                angle: 90,
                position: "insideRight",
                fill: "#8b5cf6",
                fontSize: 12,
              }}
            />
            <ReferenceLine
              yAxisId="conf"
              y={0.55}
              stroke="#10b981"
              strokeDasharray="4 4"
              label={{ value: "High Quality (0.55)", fill: "#10b981", fontSize: 10, position: "insideTopRight" }}
            />
            <ReferenceLine
              yAxisId="conf"
              y={0.30}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: "Marginal (0.30)", fill: "#f59e0b", fontSize: 10, position: "insideBottomRight" }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend verticalAlign="top" height={36} iconSize={10} />
            <Line
              yAxisId="conf"
              type="monotone"
              dataKey="confidence"
              name="Tracking Confidence"
              stroke="#3b82f6"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#3b82f6" }}
              activeDot={{ r: 6 }}
            />
            <Line
              yAxisId="pos"
              type="monotone"
              dataKey="centerX"
              name="Center X (px)"
              stroke="#8b5cf6"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
            <Line
              yAxisId="pos"
              type="monotone"
              dataKey="centerY"
              name="Center Y (px)"
              stroke="#ec4899"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="tracking-methodology-note">
        <small>
          <strong>Scientific Methodology:</strong> Confidence score evaluates vector coherence, outlier retention,
          and regional mask coverage across optical flow fields. Translations below 0.30 confidence represent unreliable
          optical flow tracking. Rigid 2D translation only; does not compensate for contour deformation or out-of-plane motion.
        </small>
      </div>
    </div>
  );
}
