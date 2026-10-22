import TrackedROIKeyframeGallery from "./TrackedROIKeyframeGallery";
import TrackingTrajectoryChart from "./TrackingTrajectoryChart";

export default function TrackedROIPreviewModal({
  isOpen,
  onClose,
  loading,
  error,
  previewData,
}) {
  if (!isOpen) return null;

  return (
    <div className="roi-preview-modal-backdrop" onClick={onClose}>
      <div
        className="roi-preview-modal-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="roi-preview-modal-header">
          <div className="modal-title-group">
            <h3>ROI Tracking Preview</h3>
            <span className="roi-tracked-badge">ESTIMATION</span>
          </div>
          <button
            type="button"
            className="roi-modal-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div className="roi-preview-modal-body">
          {loading && (
            <div className="status-banner loading">
              <span className="spinner"></span>
              Estimating frame-to-frame translation via optical flow &amp; rendering keyframes...
            </div>
          )}

          {error && (
            <div className="status-banner error">
              <strong>Preview Error:</strong> {error}
            </div>
          )}

          {previewData && !loading && (
            <>
              {previewData.warning && (
                <div className="roi-tracking-warning-box">
                  <span className="warning-icon">⚠️</span>
                  <div>
                    <strong>Tracking Notice:</strong> {previewData.warning}
                  </div>
                </div>
              )}

              {/* Render keyframe cards */}
              <TrackedROIKeyframeGallery
                trackingPreviews={previewData.previews}
                trackingPath={previewData.tracking_path}
              />

              {/* Render trajectory chart */}
              <div style={{ marginTop: 20 }}>
                <TrackingTrajectoryChart
                  trackingPath={previewData.tracking_path}
                  trackingSummary={previewData.tracking_summary}
                />
              </div>
            </>
          )}
        </div>

        <div className="roi-preview-modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}
