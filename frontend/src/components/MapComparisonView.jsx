import { useState } from "react";
import { getOutputUrl } from "../services/api";

export default function MapComparisonView({ compatibleMaps, analyses }) {
  const [selectedMapKey, setSelectedMapKey] = useState(
    compatibleMaps && compatibleMaps.length > 0 ? compatibleMaps[0].key : ""
  );

  if (!compatibleMaps || compatibleMaps.length === 0) {
    return (
      <div className="map-comparison-card empty">
        <p>No compatible visualization maps available for side-by-side comparison.</p>
      </div>
    );
  }

  const activeMapObj = compatibleMaps.find((m) => m.key === selectedMapKey) || compatibleMaps[0];

  return (
    <div className="map-comparison-section">
      <div className="map-comparison-header">
        <div>
          <h4>Side-by-Side Spatial Deformation Map Comparison</h4>
          <p className="map-comparison-subtitle">
            Direct spatial visual comparison of optical flow fields and strain gradients
          </p>
        </div>

        {/* Map Type Selector */}
        <div className="map-selector-control">
          <label htmlFor="map-select">Select Colormap:</label>
          <select
            id="map-select"
            className="map-select-dropdown"
            value={selectedMapKey}
            onChange={(e) => setSelectedMapKey(e.target.value)}
          >
            {compatibleMaps.map((m) => (
              <option key={m.key} value={m.key}>
                {m.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="map-grid-container">
        {analyses.map((a, idx) => {
          const path = activeMapObj.paths[idx];
          const imgUrl = getOutputUrl(path);
          const meta = a.metadata || {};

          return (
            <div key={meta.id || idx} className="map-side-card">
              <div className="map-side-header">
                <span className="analysis-tag">Analysis {idx + 1}</span>
                <span className="analysis-type-tag">{meta.type || "Analysis"}</span>
                <span className="analysis-id-tag">ID: {meta.id ? meta.id.slice(0, 8) : `A${idx+1}`}</span>
              </div>

              <div className="map-image-wrapper">
                {imgUrl ? (
                  <img
                    src={imgUrl}
                    alt={`${activeMapObj.title} - Analysis ${idx + 1}`}
                    className="comparison-map-img"
                    loading="lazy"
                  />
                ) : (
                  <div className="map-unavailable-box">
                    <span className="unavailable-icon">🖼️</span>
                    <p>Visualization unavailable for this analysis.</p>
                  </div>
                )}
              </div>

              <div className="map-card-footer">
                <span className="map-title-label">{activeMapObj.title}</span>
                {meta.calibration?.enabled ? (
                  <span className="map-cal-tag">
                    Calibrated ({meta.calibration.pixel_spacing_x} {meta.calibration.unit}/px)
                  </span>
                ) : (
                  <span className="map-cal-tag uncal">Native Pixels</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

