import { useState, useRef, useEffect, useCallback } from "react";

/**
 * ROISelector
 *
 * Allows users to define a Region of Interest (ROI) over a reference cardiac frame
 * supporting Rectangle, Ellipse, and Polygon geometries.
 *
 * Automatically converts DOM canvas coordinates to native image pixel space.
 *
 * Strict non-diagnostic disclaimer is rendered in compliance with research prototype guidelines.
 */
export default function ROISelector({
  imageFile,
  imageSrc: externalImageSrc,
  roi,
  onChange,
  disabled = false,
  allowTracking = false,
}) {
  const [activeType, setActiveType] = useState(roi?.type || "rectangle");
  const currentMode = roi?.mode || "fixed";
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState(null);
  const [currentPoint, setCurrentPoint] = useState(null);
  const [polyPoints, setPolyPoints] = useState([]); // DOM points for polygon in progress
  const [localImageSrc, setLocalImageSrc] = useState(null);

  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const canvasRef = useRef(null);

  // Manage image source from File object or direct URL
  useEffect(() => {
    if (externalImageSrc) {
      setLocalImageSrc(externalImageSrc);
    } else if (imageFile instanceof File || imageFile instanceof Blob) {
      const url = URL.createObjectURL(imageFile);
      setLocalImageSrc(url);
      return () => URL.revokeObjectURL(url);
    } else if (typeof imageFile === "string") {
      setLocalImageSrc(imageFile);
    } else {
      setLocalImageSrc(null);
    }
  }, [imageFile, externalImageSrc]);

  // Keep activeType in sync if roi.type changes from parent
  useEffect(() => {
    if (roi?.type && roi.type !== activeType) {
      setActiveType(roi.type);
    }
  }, [roi?.type]);

  // Compute coordinate scales between native image resolution and rendered DOM size
  const getScaleFactors = useCallback(() => {
    const img = imageRef.current;
    if (!img || !img.naturalWidth || !img.clientWidth) {
      return { scaleX: 1, scaleY: 1, naturalW: 0, naturalH: 0 };
    }
    return {
      scaleX: img.naturalWidth / img.clientWidth,
      scaleY: img.naturalHeight / img.clientHeight,
      naturalW: img.naturalWidth,
      naturalH: img.naturalHeight,
    };
  }, []);

  // Sync canvas size with image size
  const syncCanvasSize = useCallback(() => {
    const img = imageRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    redrawROI();
  }, []);

  // Redraw existing ROI or current drawing shape onto canvas
  const redrawROI = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !img.clientWidth) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!roi?.enabled && !isDrawing && polyPoints.length === 0) {
      return;
    }

    const { scaleX, scaleY } = getScaleFactors();
    if (scaleX === 0 || scaleY === 0) return;

    // Styling constants
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = "#eab308"; // Amber / Yellow line
    ctx.fillStyle = "rgba(234, 179, 8, 0.22)"; // Semi-transparent yellow fill

    // 1. Draw completed ROI from props if not currently actively dragging
    if (roi?.enabled && roi.coordinates && !isDrawing) {
      ctx.save();
      if (roi.type === "rectangle") {
        const { x, y, width, height } = roi.coordinates;
        // Convert from native image coords back to display coords
        const dx = x / scaleX;
        const dy = y / scaleY;
        const dw = width / scaleX;
        const dh = height / scaleY;

        ctx.strokeRect(dx, dy, dw, dh);
        ctx.fillRect(dx, dy, dw, dh);
      } else if (roi.type === "ellipse") {
        const cx = (roi.coordinates.center_x ?? roi.coordinates.cx) / scaleX;
        const cy = (roi.coordinates.center_y ?? roi.coordinates.cy) / scaleY;
        const rx = (roi.coordinates.radius_x ?? roi.coordinates.rx) / scaleX;
        const ry = (roi.coordinates.radius_y ?? roi.coordinates.ry) / scaleY;

        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.fill();
      } else if (roi.type === "polygon") {
        const pts = roi.coordinates.points || roi.coordinates;
        if (Array.isArray(pts) && pts.length >= 3) {
          ctx.beginPath();
          pts.forEach((pt, idx) => {
            const px = (pt.x ?? pt[0]) / scaleX;
            const py = (pt.y ?? pt[1]) / scaleY;
            if (idx === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          });
          ctx.closePath();
          ctx.stroke();
          ctx.fill();

          // Draw vertex handles
          pts.forEach((pt) => {
            const px = (pt.x ?? pt[0]) / scaleX;
            const py = (pt.y ?? pt[1]) / scaleY;
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(px, py, 4, 0, 2 * Math.PI);
            ctx.fill();
            ctx.stroke();
          });
        }
      }
      ctx.restore();
      return;
    }

    // 2. Draw active in-progress shape
    if (isDrawing && startPoint && currentPoint) {
      ctx.save();
      ctx.setLineDash([5, 4]); // Dashed guide while drawing

      if (activeType === "rectangle") {
        const x = Math.min(startPoint.x, currentPoint.x);
        const y = Math.min(startPoint.y, currentPoint.y);
        const w = Math.abs(currentPoint.x - startPoint.x);
        const h = Math.abs(currentPoint.y - startPoint.y);

        ctx.strokeRect(x, y, w, h);
        ctx.fillRect(x, y, w, h);
      } else if (activeType === "ellipse") {
        const cx = (startPoint.x + currentPoint.x) / 2;
        const cy = (startPoint.y + currentPoint.y) / 2;
        const rx = Math.abs(currentPoint.x - startPoint.x) / 2;
        const ry = Math.abs(currentPoint.y - startPoint.y) / 2;

        if (rx > 1 && ry > 1) {
          ctx.beginPath();
          ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI);
          ctx.stroke();
          ctx.fill();
        }
      }
      ctx.restore();
    }

    // 3. Draw polygon vertices & segments in progress
    if (activeType === "polygon" && polyPoints.length > 0) {
      ctx.save();
      ctx.beginPath();
      polyPoints.forEach((pt, idx) => {
        if (idx === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });

      // Guide line to current cursor
      if (currentPoint) {
        ctx.lineTo(currentPoint.x, currentPoint.y);
      }

      ctx.stroke();

      // Render vertex dots
      polyPoints.forEach((pt, idx) => {
        ctx.fillStyle = idx === 0 ? "#22c55e" : "#ffffff"; // First dot green
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 5, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
      });
      ctx.restore();
    }
  }, [roi, isDrawing, startPoint, currentPoint, polyPoints, activeType, getScaleFactors]);

  // Window resize observer to keep canvas matched
  useEffect(() => {
    const handleResize = () => syncCanvasSize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [syncCanvasSize]);

  useEffect(() => {
    redrawROI();
  }, [redrawROI]);

  // Mouse event handlers on canvas
  const getCanvasCoords = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(canvas.width, e.clientX - rect.left)),
      y: Math.max(0, Math.min(canvas.height, e.clientY - rect.top)),
    };
  };

  const handleMouseDown = (e) => {
    if (disabled || !roi?.enabled) return;
    const pt = getCanvasCoords(e);

    if (activeType === "rectangle" || activeType === "ellipse") {
      setIsDrawing(true);
      setStartPoint(pt);
      setCurrentPoint(pt);
    }
  };

  const handleMouseMove = (e) => {
    if (disabled || !roi?.enabled) return;
    const pt = getCanvasCoords(e);
    setCurrentPoint(pt);

    if (isDrawing || activeType === "polygon") {
      redrawROI();
    }
  };

  const handleMouseUp = () => {
    if (disabled || !roi?.enabled) return;

    if ((activeType === "rectangle" || activeType === "ellipse") && isDrawing && startPoint && currentPoint) {
      setIsDrawing(false);
      const { scaleX, scaleY, naturalW, naturalH } = getScaleFactors();

      if (activeType === "rectangle") {
        const minX = Math.min(startPoint.x, currentPoint.x);
        const minY = Math.min(startPoint.y, currentPoint.y);
        const w = Math.abs(currentPoint.x - startPoint.x);
        const h = Math.abs(currentPoint.y - startPoint.y);

        if (w >= 4 && h >= 4) {
          const nativeX = Math.max(0, Math.min(naturalW - 1, Math.round(minX * scaleX)));
          const nativeY = Math.max(0, Math.min(naturalH - 1, Math.round(minY * scaleY)));
          const nativeW = Math.max(1, Math.min(naturalW - nativeX, Math.round(w * scaleX)));
          const nativeH = Math.max(1, Math.min(naturalH - nativeY, Math.round(h * scaleY)));

          onChange({
            enabled: true,
            type: "rectangle",
            coordinates: {
              x: nativeX,
              y: nativeY,
              width: nativeW,
              height: nativeH,
            },
            mode: currentMode,
          });
        }
      } else if (activeType === "ellipse") {
        const cx = (startPoint.x + currentPoint.x) / 2;
        const cy = (startPoint.y + currentPoint.y) / 2;
        const rx = Math.abs(currentPoint.x - startPoint.x) / 2;
        const ry = Math.abs(currentPoint.y - startPoint.y) / 2;

        if (rx >= 3 && ry >= 3) {
          const nativeCx = Math.max(0, Math.min(naturalW - 1, Math.round(cx * scaleX)));
          const nativeCy = Math.max(0, Math.min(naturalH - 1, Math.round(cy * scaleY)));
          const nativeRx = Math.max(1, Math.round(rx * scaleX));
          const nativeRy = Math.max(1, Math.round(ry * scaleY));

          onChange({
            enabled: true,
            type: "ellipse",
            coordinates: {
              center_x: nativeCx,
              center_y: nativeCy,
              radius_x: nativeRx,
              radius_y: nativeRy,
            },
            mode: currentMode,
          });
        }
      }
      setStartPoint(null);
      setCurrentPoint(null);
    }
  };

  const handleCanvasClick = (e) => {
    if (disabled || !roi?.enabled || activeType !== "polygon") return;
    const pt = getCanvasCoords(e);

    // If clicking close to the starting point and we have at least 3 points, close it
    if (polyPoints.length >= 3) {
      const first = polyPoints[0];
      const dist = Math.hypot(pt.x - first.x, pt.y - first.y);
      if (dist < 15) {
        finalizePolygon(polyPoints);
        return;
      }
    }

    setPolyPoints((prev) => [...prev, pt]);
  };

  const handleDoubleClick = () => {
    if (disabled || !roi?.enabled || activeType !== "polygon") return;
    if (polyPoints.length >= 3) {
      finalizePolygon(polyPoints);
    }
  };

  const finalizePolygon = (points) => {
    if (points.length < 3) return;
    const { scaleX, scaleY } = getScaleFactors();
    const nativePoints = points.map((p) => ({
      x: Math.round(p.x * scaleX),
      y: Math.round(p.y * scaleY),
    }));

    onChange({
      enabled: true,
      type: "polygon",
      coordinates: {
        points: nativePoints,
      },
      mode: currentMode,
    });
    setPolyPoints([]);
  };

  const handleToggleEnable = (e) => {
    const enabled = e.target.checked;
    if (!enabled) {
      setPolyPoints([]);
      onChange({ enabled: false, type: activeType, coordinates: null, mode: currentMode });
    } else {
      onChange({ enabled: true, type: activeType, coordinates: roi?.coordinates || null, mode: currentMode });
    }
  };

  const handleTypeChange = (newType) => {
    setActiveType(newType);
    setPolyPoints([]);
    onChange({
      enabled: roi?.enabled ?? true,
      type: newType,
      coordinates: null, // Clear coordinates when geometry changes
      mode: currentMode,
    });
  };

  const handleModeChange = (newMode) => {
    onChange({
      enabled: roi?.enabled ?? true,
      type: activeType,
      coordinates: roi?.coordinates || null,
      mode: newMode,
    });
  };

  const handleClearROI = () => {
    setPolyPoints([]);
    setIsDrawing(false);
    setStartPoint(null);
    setCurrentPoint(null);
    onChange({
      enabled: roi?.enabled ?? false,
      type: activeType,
      coordinates: null,
      mode: currentMode,
    });
  };

  const hasCoords = Boolean(roi?.coordinates);

  return (
    <div className="roi-selector-card">
      <div className="roi-header-row">
        <label className="roi-toggle-label">
          <input
            type="checkbox"
            className="roi-checkbox"
            checked={Boolean(roi?.enabled)}
            onChange={handleToggleEnable}
            disabled={disabled || !localImageSrc}
          />
          <span className="roi-toggle-text">
            <strong>Enable Region of Interest (ROI) Analysis</strong>
          </span>
        </label>
        {roi?.enabled && (
          <span className="roi-status-pill">
            {hasCoords ? `Active: ${roi.type}${allowTracking ? ` (${currentMode})` : ""}` : "ROI Enabled (Draw on image)"}
          </span>
        )}
      </div>

      {!localImageSrc && (
        <div className="roi-empty-hint">
          <span>Upload Image 1 (Reference Frame) above to define an ROI.</span>
        </div>
      )}

      {roi?.enabled && localImageSrc && (
        <div className="roi-content-body">
          {/* Tracking Mode Toggle if allowTracking is enabled */}
          {allowTracking && (
            <div className="roi-mode-selector-row">
              <span className="roi-mode-label">Tracking Mode:</span>
              <div className="roi-mode-buttons">
                <button
                  type="button"
                  className={`roi-mode-btn ${currentMode === "fixed" ? "active" : ""}`}
                  onClick={() => handleModeChange("fixed")}
                >
                  Fixed ROI
                </button>
                <button
                  type="button"
                  className={`roi-mode-btn ${currentMode === "tracked" ? "active" : ""}`}
                  onClick={() => handleModeChange("tracked")}
                >
                  Tracked ROI
                </button>
              </div>
            </div>
          )}

          {allowTracking && currentMode === "tracked" && (
            <div className="roi-tracked-banner">
              <span className="roi-tracked-badge">TRACKED</span>
              <span>
                <strong>Optical Flow Translation Tracking:</strong> In Tracked ROI mode, the user-defined region is
                translated frame-to-frame across the cine sequence based on median optical flow motion vectors.
                <em> (Research prototype — rigid 2D translation only, no anatomical tissue warping).</em>
              </span>
            </div>
          )}

          {/* Geometry Selector and Controls Toolbar */}
          <div className="roi-toolbar">
            <div className="roi-type-tabs">
              <button
                type="button"
                className={`roi-tab-btn ${activeType === "rectangle" ? "active" : ""}`}
                onClick={() => handleTypeChange("rectangle")}
              >
                Rectangle
              </button>
              <button
                type="button"
                className={`roi-tab-btn ${activeType === "ellipse" ? "active" : ""}`}
                onClick={() => handleTypeChange("ellipse")}
              >
                Ellipse
              </button>
              <button
                type="button"
                className={`roi-tab-btn ${activeType === "polygon" ? "active" : ""}`}
                onClick={() => handleTypeChange("polygon")}
              >
                Polygon
              </button>
            </div>

            <div className="roi-actions">
              {activeType === "polygon" && polyPoints.length >= 3 && (
                <button
                  type="button"
                  className="btn-secondary roi-btn-sm"
                  onClick={() => finalizePolygon(polyPoints)}
                >
                  Finish Polygon ({polyPoints.length} pts)
                </button>
              )}
              <button
                type="button"
                className="btn-secondary roi-btn-sm"
                onClick={handleClearROI}
                disabled={!hasCoords && polyPoints.length === 0}
              >
                Clear ROI
              </button>
            </div>
          </div>

          {/* Interactive Drawing Canvas Container */}
          <div className="roi-stage-container" ref={containerRef}>
            <img
              ref={imageRef}
              src={localImageSrc}
              alt="ROI Reference"
              className="roi-base-image"
              onLoad={syncCanvasSize}
            />
            <canvas
              ref={canvasRef}
              className={`roi-overlay-canvas ${roi?.enabled ? "interactive" : ""}`}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onClick={handleCanvasClick}
              onDoubleClick={handleDoubleClick}
            />
          </div>

          {/* Drawing Instructions & Coordinates Readout */}
          <div className="roi-info-footer">
            <div className="roi-hint-text">
              {activeType === "rectangle" && "💡 Click and drag across the image to draw a rectangular region."}
              {activeType === "ellipse" && "💡 Click and drag to create an elliptical region."}
              {activeType === "polygon" && "💡 Click to add vertices. Double-click or click 'Finish Polygon' when done (min 3 points)."}
            </div>

            {hasCoords && (
              <div className="roi-coords-readout">
                {roi.type === "rectangle" && (
                  <span>
                    X: <strong>{roi.coordinates.x}</strong>, Y: <strong>{roi.coordinates.y}</strong>, W: <strong>{roi.coordinates.width} px</strong>, H: <strong>{roi.coordinates.height} px</strong>
                  </span>
                )}
                {roi.type === "ellipse" && (
                  <span>
                    Center: (<strong>{roi.coordinates.center_x}</strong>, <strong>{roi.coordinates.center_y}</strong>), Radii: ({roi.coordinates.radius_x} &times; {roi.coordinates.radius_y} px)
                  </span>
                )}
                {roi.type === "polygon" && (
                  <span>
                    Polygon: <strong>{(roi.coordinates.points || roi.coordinates).length}</strong> vertices defined
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Research Prototype & Scientific Limitations Notice */}
          <div className="roi-disclaimer-box">
            <span className="roi-disclaimer-icon">⚠️</span>
            <div className="roi-disclaimer-content">
              <strong>Research Prototype Notice:</strong>
              <span>
                {" "}Region of Interest (ROI) restricts metric calculations strictly to the user-specified geometric boundary.
                This is a manual region, <strong>not an automated or clinically validated anatomical segmentation</strong>, and
                implies no diagnostic medical claim. In temporal analysis, the ROI boundary is static and does not automatically
                track wall motion across cine frames.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

