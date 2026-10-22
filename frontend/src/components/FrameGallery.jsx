import { getFrameImageUrl } from "../services/api";

export default function FrameGallery({
  frames = [],
  selectedFrames = [],
  onToggleFrame,
  onSelectAll,
  onClearSelection,
  onRemoveFrame,
  showRemove = false,
}) {
  if (!frames || frames.length === 0) {
    return (
      <div className="frame-gallery-empty">
        <p>No frames available to display.</p>
      </div>
    );
  }

  const allSelected = frames.length > 0 && selectedFrames.length === frames.length;

  return (
    <div className="frame-gallery-container">
      <div className="frame-gallery-toolbar">
        <div className="gallery-stats">
          <span>
            Total Frames: <strong>{frames.length}</strong>
          </span>
          <span className="stat-separator">•</span>
          <span>
            Selected for Analysis:{" "}
            <strong className={selectedFrames.length >= 2 ? "text-success" : "text-warning"}>
              {selectedFrames.length}
            </strong>
          </span>
        </div>

        <div className="gallery-actions">
          <button
            type="button"
            className="btn-gallery-action"
            onClick={allSelected ? onClearSelection : onSelectAll}
          >
            {allSelected ? "Deselect All" : "Select All"}
          </button>
          <button
            type="button"
            className="btn-gallery-action btn-gallery-clear"
            onClick={onClearSelection}
            disabled={selectedFrames.length === 0}
          >
            Clear Selection
          </button>
        </div>
      </div>

      <div className="frame-gallery-grid">
        {frames.map((frame, index) => {
          const isSelected = selectedFrames.includes(frame.id || frame);
          const frameKey = frame.id || frame;
          const frameName = frame.name || frame;
          const imageUrl = frame.previewUrl || getFrameImageUrl(frame.filename || frame);

          return (
            <div
              key={frameKey}
              className={`frame-card ${isSelected ? "frame-selected" : "frame-unselected"}`}
              onClick={() => onToggleFrame(frameKey)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onToggleFrame(frameKey);
                }
              }}
            >
              <div className="frame-card-badge">
                <span className="frame-index-num">#{index + 1}</span>
                <input
                  type="checkbox"
                  className="frame-checkbox"
                  checked={isSelected}
                  onChange={() => {}} // Handled by parent card click
                  tabIndex={-1}
                />
              </div>

              <div className="frame-thumb-box">
                <img
                  src={imageUrl}
                  alt={`Frame ${index + 1}`}
                  className="frame-thumb-img"
                  loading="lazy"
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                    if (e.currentTarget.nextElementSibling) {
                      e.currentTarget.nextElementSibling.style.display = "flex";
                    }
                  }}
                />
                <div className="frame-thumb-fallback" style={{ display: "none" }}>
                  <span>Frame #{index + 1}</span>
                </div>
              </div>

              <div className="frame-card-footer">
                <span className="frame-label" title={frameName}>
                  {frameName.length > 18 ? `${frameName.slice(0, 8)}...${frameName.slice(-8)}` : frameName}
                </span>
                {showRemove && onRemoveFrame && (
                  <button
                    type="button"
                    className="btn-remove-frame"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveFrame(frameKey);
                    }}
                    title="Remove frame from sequence"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

