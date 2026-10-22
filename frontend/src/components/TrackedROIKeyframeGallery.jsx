import { getOutputUrl } from "../services/api";

export default function TrackedROIKeyframeGallery({ trackingPreviews, trackingPath }) {
  if (!trackingPreviews) return null;

  const keyframes = [
    {
      id: "first",
      title: "Initial Reference Frame (Frame 1)",
      path: trackingPreviews.first,
      frameIdx: 1,
    },
    {
      id: "middle",
      title: "Mid-Cycle Frame",
      path: trackingPreviews.middle,
      frameIdx: trackingPath ? Math.round(trackingPath.length / 2) : "Mid",
    },
    {
      id: "last",
      title: "Terminal Frame",
      path: trackingPreviews.last,
      frameIdx: trackingPath ? trackingPath.length : "Last",
    },
  ].filter((kf) => Boolean(kf.path));

  if (keyframes.length === 0) return null;

  return (
    <div className="tracked-keyframe-section">
      <div className="keyframe-header">
        <h4>Tracked ROI Keyframe Overlays</h4>
        <p className="keyframe-subtitle">
          Bounding boxes translated across temporal sequence at representative cardiac cycle intervals
        </p>
      </div>

      <div className="tracked-keyframe-grid">
        {keyframes.map((kf) => (
          <div key={kf.id} className="keyframe-card">
            <div className="keyframe-card-header">
              <span className="keyframe-title">{kf.title}</span>
            </div>
            <div className="keyframe-image-wrapper">
              <img
                src={getOutputUrl(kf.path)}
                alt={kf.title}
                className="keyframe-image"
                loading="lazy"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
