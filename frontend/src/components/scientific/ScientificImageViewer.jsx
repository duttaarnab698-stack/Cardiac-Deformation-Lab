import React, { useState, useRef, useEffect, useCallback } from "react";

/**
 * ScientificImageViewer
 *
 * Professional research image viewer for cardiac kinematic and deformation visualization.
 * Supports:
 * - Zoom (in, out, reset, fit)
 * - Pan with smooth dragging
 * - Fullscreen toggle
 * - Opacity blending (Active visualization map over Reference image)
 * - Independent overlays (ROI, Tracked ROI, Annotations, Vectors, Directions)
 * - Crosshair inspection & coordinate tracking
 * - Pixel / point click sampling with RGB & intensity derivation
 * - Interactive line profile drawing tool
 * - Aspect-ratio preservation without distortion
 * - Integrated color scale legend with physical / dimensionless units
 * - Client-side high-res PNG export
 */
export default function ScientificImageViewer({
  baseImageUrl,
  activeMapUrl,
  opacity = 1,
  overlays = {
    roi: true,
    trackedRoi: true,
    annotations: true,
    vectors: true,
    directions: true,
    crosshair: false,
  },
  roiConfig = null,
  trackingData = null,
  annotations = [],
  vectorDensity = 3,
  scaleMode = "auto",
  scaleRange = null,
  onResetScale = null,
  selectedMetric = {
    name: "Displacement",
    min: 0,
    max: 10,
    unit: "px",
    colormap: "turbo",
  },
  lineProfileActive = false,
  lineProfileCoords = null,
  onLineProfileChange = null,
  onSamplePixel = null,
  isSideBySide = false,
  sideBySideMapUrl = null,
  sideBySideTitle = "Secondary View",
  differenceMode = false,
  diffType = "absolute",
}) {
  const containerRef = useRef(null);
  const baseImgRef = useRef(null);
  const activeImgRef = useRef(null);
  const sideImgRef = useRef(null);

  // Transform state (Pan and Zoom)
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Image intrinsic dimensions
  const [imgDim, setImgDim] = useState({ width: 0, height: 0 });

  // Hover crosshair position (relative to image pixels)
  const [crosshairPos, setCrosshairPos] = useState(null);

  // Line drawing in progress
  const [drawingLine, setDrawingLine] = useState(false);
  const [lineStart, setLineStart] = useState(null);

  // Keep track of image loading
  const [loading, setLoading] = useState(true);

  // Handle image load to capture intrinsic dimensions
  const handleImageLoaded = (e) => {
    if (e.target.naturalWidth && e.target.naturalHeight) {
      setImgDim({
        width: e.target.naturalWidth,
        height: e.target.naturalHeight,
      });
      setLoading(false);
    }
  };

  // Zoom handlers
  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.25, 8.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.25, 0.25));
  const handleResetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const handleFitScreen = () => {
    if (!containerRef.current || !imgDim.width) {
      handleResetZoom();
      return;
    }
    const cWidth = containerRef.current.clientWidth;
    const cHeight = containerRef.current.clientHeight;
    const scaleX = (cWidth - 40) / imgDim.width;
    const scaleY = (cHeight - 40) / imgDim.height;
    const fitScale = Math.min(scaleX, scaleY, 1.0);
    setZoom(fitScale > 0 ? fitScale : 1);
    setPan({ x: 0, y: 0 });
  };

  // Wheel zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((z) => Math.min(Math.max(z * factor, 0.25), 8.0));
  };

  // Pan interaction
  const handleMouseDown = (e) => {
    // If in line profile mode, don't drag-pan
    if (lineProfileActive) {
      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = (e.clientX - rect.left - pan.x) / zoom;
      const clickY = (e.clientY - rect.top - pan.y) / zoom;

      // Bound click inside image coordinates
      const clampedX = Math.max(0, Math.min(imgDim.width || 500, clickX));
      const clampedY = Math.max(0, Math.min(imgDim.height || 500, clickY));

      if (!drawingLine) {
        setDrawingLine(true);
        setLineStart({ x: clampedX, y: clampedY });
        if (onLineProfileChange) {
          onLineProfileChange({ x1: clampedX, y1: clampedY, x2: clampedX, y2: clampedY });
        }
      } else {
        setDrawingLine(false);
        if (onLineProfileChange && lineStart) {
          onLineProfileChange({ x1: lineStart.x, y1: lineStart.y, x2: clampedX, y2: clampedY });
        }
        setLineStart(null);
      }
      return;
    }

    if (e.button === 0) {
      // Left click
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const imgX = (e.clientX - rect.left - pan.x) / zoom;
    const imgY = (e.clientY - rect.top - pan.y) / zoom;

    if (imgDim.width > 0 && imgDim.height > 0) {
      const clampedX = Math.round(Math.max(0, Math.min(imgDim.width, imgX)));
      const clampedY = Math.round(Math.max(0, Math.min(imgDim.height, imgY)));
      setCrosshairPos({ x: clampedX, y: clampedY });

      if (lineProfileActive && drawingLine && lineStart && onLineProfileChange) {
        onLineProfileChange({
          x1: lineStart.x,
          y1: lineStart.y,
          x2: clampedX,
          y2: clampedY,
        });
      }
    }

    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Pixel sampling on click
  const handleClick = (e) => {
    if (lineProfileActive || isDragging) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const imgX = (e.clientX - rect.left - pan.x) / zoom;
    const imgY = (e.clientY - rect.top - pan.y) / zoom;

    if (imgDim.width > 0 && imgDim.height > 0) {
      const px = Math.round(Math.max(0, Math.min(imgDim.width, imgX)));
      const py = Math.round(Math.max(0, Math.min(imgDim.height, imgY)));
      const normX = px / imgDim.width;
      const normY = py / imgDim.height;

      // Sample color / intensity from canvas
      try {
        const offscreen = document.createElement("canvas");
        offscreen.width = 1;
        offscreen.height = 1;
        const ctx = offscreen.getContext("2d");
        const activeImg = activeImgRef.current || baseImgRef.current;
        if (activeImg && activeImg.complete) {
          ctx.drawImage(activeImg, px, py, 1, 1, 0, 0, 1, 1);
          const pData = ctx.getImageData(0, 0, 1, 1).data;
          const r = pData[0];
          const g = pData[1];
          const b = pData[2];
          const intensity = Math.round(0.299 * r + 0.587 * g + 0.114 * b);

          // Estimate metric value from color intensity and scale
          const minVal = scaleRange?.min ?? selectedMetric?.min ?? 0;
          const maxVal = scaleRange?.max ?? selectedMetric?.max ?? 10;
          const estMetric = minVal + (intensity / 255) * (maxVal - minVal);

          if (onSamplePixel) {
            onSamplePixel({
              x: px,
              y: py,
              normX: Number(normX.toFixed(3)),
              normY: Number(normY.toFixed(3)),
              rgb: `rgb(${r}, ${g}, ${b})`,
              intensity,
              estimatedValue: Number(estMetric.toFixed(4)),
            });
          }
        } else if (onSamplePixel) {
          onSamplePixel({ x: px, y: py, normX, normY });
        }
      } catch {
        if (onSamplePixel) {
          onSamplePixel({ x: px, y: py, normX, normY });
        }
      }
    }
  };

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", handleFsChange);
    return () => document.removeEventListener("fullscreenchange", handleFsChange);
  }, []);

  // Export current visualization as PNG
  const handleExportPng = () => {
    if (!imgDim.width || !imgDim.height) return;
    try {
      const canvas = document.createElement("canvas");
      canvas.width = imgDim.width;
      canvas.height = imgDim.height;
      const ctx = canvas.getContext("2d");

      // Draw base image
      if (baseImgRef.current && baseImgRef.current.complete) {
        ctx.drawImage(baseImgRef.current, 0, 0, imgDim.width, imgDim.height);
      }

      // Draw active visualization map with opacity
      if (activeImgRef.current && activeImgRef.current.complete && activeMapUrl) {
        ctx.globalAlpha = opacity;
        ctx.drawImage(activeImgRef.current, 0, 0, imgDim.width, imgDim.height);
        ctx.globalAlpha = 1.0;
      }

      // Draw ROI overlay if enabled
      if (overlays.roi && roiConfig?.coordinates) {
        ctx.strokeStyle = "#0284c7";
        ctx.lineWidth = 3;
        ctx.fillStyle = "rgba(2, 132, 199, 0.15)";
        if (roiConfig.type === "box" || roiConfig.type === "rectangle") {
          const { x, y, width, height } = roiConfig.coordinates;
          ctx.strokeRect(x, y, width, height);
          ctx.fillRect(x, y, width, height);
        } else if (roiConfig.type === "ellipse" || roiConfig.type === "circle") {
          const { cx, cy, rx, ry } = roiConfig.coordinates;
          ctx.beginPath();
          ctx.ellipse(cx, cy, rx, ry || rx, 0, 0, 2 * Math.PI);
          ctx.stroke();
          ctx.fill();
        }
      }

      const dataUrl = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `cardiac_deformation_${selectedMetric.name.toLowerCase().replace(/\s+/g, "_")}.png`;
      a.click();
    } catch (err) {
      console.error("Export PNG failed:", err);
    }
  };

  // Format unit label
  const unitLabel = selectedMetric.unit || "dimensionless";
  const displayMin = scaleRange?.min ?? selectedMetric.min ?? 0;
  const displayMax = scaleRange?.max ?? selectedMetric.max ?? 1;

  return (
    <div
      ref={containerRef}
      className={`scientific-image-viewer-container ${isFullscreen ? "fullscreen-active" : ""}`}
      onWheel={handleWheel}
    >
      {/* Top Toolbar */}
      <div className="sci-viewer-toolbar">
        <div className="sci-viewer-tools-group">
          <button
            className="sci-tool-btn"
            onClick={handleZoomIn}
            title="Zoom In (+)"
            aria-label="Zoom In"
          >
            🔍+
          </button>
          <button
            className="sci-tool-btn"
            onClick={handleZoomOut}
            title="Zoom Out (-)"
            aria-label="Zoom Out"
          >
            🔍-
          </button>
          <button
            className="sci-tool-btn"
            onClick={handleResetZoom}
            title="Reset Zoom (0)"
            aria-label="Reset Zoom"
          >
            ↺ Reset
          </button>
          <button
            className="sci-tool-btn"
            onClick={handleFitScreen}
            title="Fit to Screen"
            aria-label="Fit to Screen"
          >
            ⛶ Fit
          </button>
          <span className="sci-zoom-level">{Math.round(zoom * 100)}%</span>
        </div>

        {/* Dimension & Crosshair readout */}
        <div className="sci-viewer-readout">
          {imgDim.width > 0 && (
            <span className="sci-meta-badge">
              {imgDim.width} × {imgDim.height} px
            </span>
          )}
          {crosshairPos && (
            <span className="sci-coord-badge">
              X: {crosshairPos.x} &nbsp; Y: {crosshairPos.y}
            </span>
          )}
        </div>

        <div className="sci-viewer-tools-group">
          <button
            className="sci-tool-btn"
            onClick={handleExportPng}
            title="Download Visualization (PNG)"
            aria-label="Download Visualization"
          >
            💾 PNG
          </button>
          <button
            className={`sci-tool-btn ${isFullscreen ? "active" : ""}`}
            onClick={toggleFullscreen}
            title="Toggle Fullscreen (F)"
            aria-label="Toggle Fullscreen"
          >
            {isFullscreen ? "🗗 Exit" : "🗖 Fullscreen"}
          </button>
        </div>
      </div>

      {/* Main Viewport */}
      <div
        className={`sci-viewport ${isDragging ? "dragging" : ""} ${lineProfileActive ? "line-tool-active" : ""}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          setIsDragging(false);
          setCrosshairPos(null);
        }}
        onClick={handleClick}
      >
        <div
          className="sci-canvas-transform"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
          }}
        >
          {/* Side-by-side Layout vs Single View */}
          {isSideBySide && sideBySideMapUrl ? (
            <div className="sci-side-by-side-wrap">
              {/* Primary Panel */}
              <div className="sci-side-panel">
                <div className="sci-side-panel-label">{selectedMetric.name}</div>
                <div className="sci-image-stack">
                  {baseImageUrl && (
                    <img
                      ref={baseImgRef}
                      src={baseImageUrl}
                      alt="Base Reference"
                      className="sci-layer-base"
                      onLoad={handleImageLoaded}
                    />
                  )}
                  {activeMapUrl && (
                    <img
                      ref={activeImgRef}
                      src={activeMapUrl}
                      alt={selectedMetric.name}
                      className="sci-layer-map"
                      style={{ opacity }}
                    />
                  )}
                </div>
              </div>

              {/* Secondary Comparison Panel */}
              <div className="sci-side-panel">
                <div className="sci-side-panel-label">{sideBySideTitle}</div>
                <div className="sci-image-stack">
                  <img
                    ref={sideImgRef}
                    src={sideBySideMapUrl}
                    alt={sideBySideTitle}
                    className="sci-layer-map"
                  />
                </div>
              </div>
            </div>
          ) : (
            /* Single Image Stack */
            <div
              className={`sci-image-stack ${differenceMode ? `diff-mode-${diffType}` : ""}`}
              style={{
                width: imgDim.width ? `${imgDim.width}px` : "auto",
                height: imgDim.height ? `${imgDim.height}px` : "auto",
              }}
            >
              {/* Layer 1: Base Original Image */}
              {baseImageUrl && (
                <img
                  ref={baseImgRef}
                  src={baseImageUrl}
                  alt="Original Cardiac Frame"
                  className="sci-layer-base"
                  onLoad={handleImageLoaded}
                />
              )}

              {/* Layer 2: Active Visualization Map */}
              {activeMapUrl && (
                <img
                  ref={activeImgRef}
                  src={activeMapUrl}
                  alt={selectedMetric.name}
                  className="sci-layer-map"
                  style={{ opacity }}
                />
              )}

              {/* SVG Overlays: ROI, Annotations, Vectors, Crosshairs, Line Profile */}
              {imgDim.width > 0 && imgDim.height > 0 && (
                <svg
                  className="sci-svg-overlays"
                  viewBox={`0 0 ${imgDim.width} ${imgDim.height}`}
                  width={imgDim.width}
                  height={imgDim.height}
                >
                  {/* Crosshairs */}
                  {overlays.crosshair && crosshairPos && (
                    <g className="sci-crosshair-group">
                      <line
                        x1={0}
                        y1={crosshairPos.y}
                        x2={imgDim.width}
                        y2={crosshairPos.y}
                        stroke="#f59e0b"
                        strokeWidth="1.5"
                        strokeDasharray="4 2"
                      />
                      <line
                        x1={crosshairPos.x}
                        y1={0}
                        x2={crosshairPos.x}
                        y2={imgDim.height}
                        stroke="#f59e0b"
                        strokeWidth="1.5"
                        strokeDasharray="4 2"
                      />
                      <circle
                        cx={crosshairPos.x}
                        cy={crosshairPos.y}
                        r="4"
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="2"
                      />
                    </g>
                  )}

                  {/* ROI Overlay */}
                  {overlays.roi && roiConfig?.coordinates && (
                    <g className="sci-roi-group">
                      {roiConfig.type === "rectangle" || roiConfig.type === "box" ? (
                        <rect
                          x={roiConfig.coordinates.x}
                          y={roiConfig.coordinates.y}
                          width={roiConfig.coordinates.width}
                          height={roiConfig.coordinates.height}
                          fill="rgba(2, 132, 199, 0.15)"
                          stroke="#0284c7"
                          strokeWidth="2.5"
                        />
                      ) : roiConfig.type === "ellipse" || roiConfig.type === "circle" ? (
                        <ellipse
                          cx={roiConfig.coordinates.cx}
                          cy={roiConfig.coordinates.cy}
                          rx={roiConfig.coordinates.rx}
                          ry={roiConfig.coordinates.ry || roiConfig.coordinates.rx}
                          fill="rgba(2, 132, 199, 0.15)"
                          stroke="#0284c7"
                          strokeWidth="2.5"
                        />
                      ) : null}
                    </g>
                  )}

                  {/* Tracked ROI Trajectory Overlay */}
                  {overlays.trackedRoi && trackingData?.coordinates && (
                    <g className="sci-tracked-roi-group">
                      {trackingData.type === "rectangle" || trackingData.type === "box" ? (
                        <rect
                          x={trackingData.coordinates.x}
                          y={trackingData.coordinates.y}
                          width={trackingData.coordinates.width}
                          height={trackingData.coordinates.height}
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="2"
                          strokeDasharray="5 3"
                        />
                      ) : (
                        <circle
                          cx={trackingData.coordinates.cx || trackingData.coordinates.x || 100}
                          cy={trackingData.coordinates.cy || trackingData.coordinates.y || 100}
                          r={trackingData.coordinates.rx || 30}
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="2"
                          strokeDasharray="5 3"
                        />
                      )}
                    </g>
                  )}

                  {/* Annotations Overlay */}
                  {overlays.annotations &&
                    annotations.map((anno) => {
                      if (anno.annotation_type === "point" && anno.points?.[0]) {
                        return (
                          <g key={anno.id} className="sci-anno-marker">
                            <circle
                              cx={anno.points[0].x}
                              cy={anno.points[0].y}
                              r="5"
                              fill="#ef4444"
                              stroke="#ffffff"
                              strokeWidth="1.5"
                            />
                            <text
                              x={anno.points[0].x + 8}
                              y={anno.points[0].y + 4}
                              fill="#ef4444"
                              fontSize="11"
                              fontWeight="bold"
                            >
                              {anno.annotator_label}
                            </text>
                          </g>
                        );
                      }
                      if (
                        (anno.annotation_type === "polygon" || anno.annotation_type === "contour") &&
                        anno.points?.length > 1
                      ) {
                        const ptsStr = anno.points.map((p) => `${p.x},${p.y}`).join(" ");
                        return (
                          <polygon
                            key={anno.id}
                            points={ptsStr}
                            fill="rgba(239, 68, 68, 0.15)"
                            stroke="#ef4444"
                            strokeWidth="2"
                          />
                        );
                      }
                      return null;
                    })}

                  {/* Interactive Line Profile */}
                  {lineProfileCoords && (
                    <g className="sci-line-profile-group">
                      <line
                        x1={lineProfileCoords.x1}
                        y1={lineProfileCoords.y1}
                        x2={lineProfileCoords.x2}
                        y2={lineProfileCoords.y2}
                        stroke="#e11d48"
                        strokeWidth="2.5"
                        strokeDasharray="6 3"
                      />
                      <circle
                        cx={lineProfileCoords.x1}
                        cy={lineProfileCoords.y1}
                        r="5"
                        fill="#e11d48"
                        stroke="#ffffff"
                        strokeWidth="1.5"
                      />
                      <circle
                        cx={lineProfileCoords.x2}
                        cy={lineProfileCoords.y2}
                        r="5"
                        fill="#e11d48"
                        stroke="#ffffff"
                        strokeWidth="1.5"
                      />
                    </g>
                  )}
                </svg>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Color Scale & Legend Bar */}
      <div className="sci-viewer-legend-bar">
        <div className="sci-legend-meta">
          <span className="sci-legend-title">{selectedMetric.name}</span>
          <span className="sci-legend-unit">
            Unit: <strong>{unitLabel}</strong>
          </span>
          {scaleMode === "manual" && (
            <span className="sci-legend-manual-badge">MANUAL SCALE</span>
          )}
        </div>

        {/* Gradient Legend Scale */}
        <div className="sci-legend-gradient-wrap">
          <span className="sci-legend-val min-val">
            {typeof displayMin === "number" ? displayMin.toFixed(2) : displayMin}
          </span>
          <div className={`sci-legend-bar colormap-${selectedMetric.colormap || "turbo"}`} />
          <span className="sci-legend-val max-val">
            {typeof displayMax === "number" ? displayMax.toFixed(2) : displayMax}
          </span>
        </div>

        {scaleMode === "manual" && onResetScale && (
          <button
            className="sci-reset-scale-btn"
            onClick={onResetScale}
            title="Reset to computed automatic scale limits"
          >
            Reset Scale
          </button>
        )}
      </div>
    </div>
  );
}

