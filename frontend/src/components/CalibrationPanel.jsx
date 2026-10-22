import { useState } from "react";

/**
 * CalibrationPanel Component
 * Compact collapsible/toggleable panel for optional spatial calibration (mm/pixel or cm/pixel).
 *
 * @param {object} calibration - { enabled: boolean, pixel_spacing_x: string|number, pixel_spacing_y: string|number, unit: string }
 * @param {function} onChange - callback passing updated calibration object
 */
export default function CalibrationPanel({ calibration, onChange }) {
  const { enabled, pixel_spacing_x, pixel_spacing_y, unit } = calibration;

  const handleToggle = (e) => {
    onChange({
      ...calibration,
      enabled: e.target.checked,
    });
  };

  const handleSpacingXChange = (e) => {
    onChange({
      ...calibration,
      pixel_spacing_x: e.target.value,
    });
  };

  const handleSpacingYChange = (e) => {
    onChange({
      ...calibration,
      pixel_spacing_y: e.target.value,
    });
  };

  const handleUnitChange = (e) => {
    onChange({
      ...calibration,
      unit: e.target.value,
    });
  };

  return (
    <div className={`calibration-panel-card ${enabled ? "calibration-active" : ""}`}>
      <div className="calibration-header-toggle">
        <label className="calibration-checkbox-label">
          <input
            type="checkbox"
            checked={enabled}
            onChange={handleToggle}
            className="calibration-checkbox"
          />
          <span className="calibration-title">
            <strong>Use Spatial Calibration</strong> (Optional)
          </span>
        </label>
        <span className="calibration-tag">
          {enabled ? `Active (${unit})` : "Off (Pixel-space)"}
        </span>
      </div>

      {enabled && (
        <div className="calibration-body">
          <p className="calibration-hint">
            Provide physical distance per pixel from vendor acquisition metadata (DICOM / ultrasound header).
            Strain remains dimensionless.
          </p>
          <div className="calibration-inputs-row">
            <div className="cal-input-group">
              <label htmlFor="cal-spacing-x">Pixel Spacing X ({unit}/px):</label>
              <input
                id="cal-spacing-x"
                type="number"
                step="any"
                min="0.0001"
                placeholder="e.g. 0.5"
                value={pixel_spacing_x}
                onChange={handleSpacingXChange}
                className="cal-number-input"
              />
            </div>

            <div className="cal-input-group">
              <label htmlFor="cal-spacing-y">Pixel Spacing Y ({unit}/px):</label>
              <input
                id="cal-spacing-y"
                type="number"
                step="any"
                min="0.0001"
                placeholder="e.g. 0.5"
                value={pixel_spacing_y}
                onChange={handleSpacingYChange}
                className="cal-number-input"
              />
            </div>

            <div className="cal-input-group cal-unit-group">
              <label htmlFor="cal-unit">Physical Unit:</label>
              <select
                id="cal-unit"
                value={unit}
                onChange={handleUnitChange}
                className="cal-unit-select"
              >
                <option value="mm">mm (Millimeters)</option>
                <option value="cm">cm (Centimeters)</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

