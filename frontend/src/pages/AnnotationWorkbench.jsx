import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  createAnnotation,
  getAnnotations,
  deleteAnnotation,
  convertAnnotationToRoi,
  exportAnnotations,
  importAnnotations,
  getAnalysisHistory,
  getFrameImageUrl,
} from "../services/api";
import "./AnnotationWorkbench.css";

const PRESET_LABELS = [
  "LV boundary",
  "RV boundary",
  "myocardial region",
  "landmark",
  "motion reference",
  "deformation reference",
];

const TOOL_DEFS = [
  { id: "point", label: "Point", icon: "📍", type: "point", shortcut: "P" },
  { id: "landmark", label: "Landmark", icon: "🏷️", type: "landmark", shortcut: "L" },
  { id: "polyline", label: "Polyline", icon: "📏", type: "polyline", shortcut: "Line" },
  { id: "polygon", label: "Polygon", icon: "🔷", type: "polygon", shortcut: "Poly" },
  { id: "contour", label: "Contour", icon: "✏️", type: "contour", shortcut: "Free" },
  { id: "pan", label: "Pan View", icon: "✋", type: null, shortcut: "Space" },
];

export default function AnnotationWorkbench() {
  const { analysisId } = useParams();


  // History & Image selection
  const [historyList, setHistoryList] = useState([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState(analysisId || "");
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [selectedImageFilename, setSelectedImageFilename] = useState("");
  const [selectedFrameIndex, setSelectedFrameIndex] = useState(0);

  // Image display & natural dimensions
  const [imageDimensions, setImageDimensions] = useState({ width: 512, height: 512 });
  const [imageLoaded, setImageLoaded] = useState(false);

  // Zoom and Pan
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Tools: "point" | "landmark" | "polyline" | "polygon" | "contour" | "pan"
  const [activeTool, setActiveTool] = useState("polygon");

  // In-progress points in image pixel coordinates
  const [currentPoints, setCurrentPoints] = useState([]);
  const [isFreehandDrawing, setIsFreehandDrawing] = useState(false);

  // Annotation Metadata Form
  const [annotationType, setAnnotationType] = useState("polygon");
  const [annotatorLabel, setAnnotatorLabel] = useState("myocardial region");
  const [landmarkName, setLandmarkName] = useState("");
  const [description, setDescription] = useState("");
  const [regionName, setRegionName] = useState("");

  // Saved annotations state
  const [savedAnnotations, setSavedAnnotations] = useState([]);
  const [loadingAnnotations, setLoadingAnnotations] = useState(false);
  const [showOverlays, setShowOverlays] = useState(true);

  // Notifications & UI feedback
  const [uiMessage, setUiMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [roiSuccessMessage, setRoiSuccessMessage] = useState(null);

  const svgRef = useRef(null);
  const containerRef = useRef(null);

  // Load analysis history on mount
  useEffect(() => {
    async function fetchHistoryData() {
      try {
        const historyData = await getAnalysisHistory();
        const list = Array.isArray(historyData) ? historyData : [];
        setHistoryList(list);
        if (!selectedAnalysisId && list.length > 0) {
          const firstId = list[0]?.id || list[0]?.analysis_id || "";
          setSelectedAnalysisId(firstId);
        }
      } catch (err) {
        console.error("Failed to load history:", err);
      }
    }
    fetchHistoryData();
  }, [selectedAnalysisId]);

  // Update active analysis and default image when selectedAnalysisId changes
  useEffect(() => {
    if (!selectedAnalysisId) return;
    const found = historyList.find(
      (h) => (h.id || h.analysis_id) === selectedAnalysisId
    );
    if (found) {
      setActiveAnalysis(found);
      const res = found.result || {};
      const defaultImg =
        found.image1_filename ||
        res.image1 ||
        found.image1 ||
        found.image_filenames?.[0] ||
        res.images?.[0] ||
        "";
      setSelectedImageFilename(defaultImg);
      setSelectedFrameIndex(0);
    }
  }, [selectedAnalysisId, historyList]);


  const fetchAnnotations = useCallback(async () => {
    setLoadingAnnotations(true);
    try {
      const data = await getAnnotations({
        analysis_id: selectedAnalysisId || undefined,
        image_filename: selectedImageFilename || undefined,
      });
      setSavedAnnotations(data || []);
    } catch (err) {
      console.error("Failed to fetch annotations:", err);
    } finally {
      setLoadingAnnotations(false);
    }
  }, [selectedAnalysisId, selectedImageFilename]);

  // Load annotations whenever selectedImageFilename or selectedAnalysisId changes
  useEffect(() => {
    if (selectedAnalysisId || selectedImageFilename) {
      fetchAnnotations();
    }
  }, [selectedAnalysisId, selectedImageFilename, fetchAnnotations]);

  // Handle image load to capture natural resolution
  const handleImageLoad = (e) => {
    const naturalW = e.target.naturalWidth || 512;
    const naturalH = e.target.naturalHeight || 512;
    setImageDimensions({ width: naturalW, height: naturalH });
    setImageLoaded(true);
    // Reset view
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Convert mouse event coordinates on the SVG element to original image pixel coordinates
  const getOriginalImageCoords = (e) => {
    if (!svgRef.current) return null;
    const svg = svgRef.current;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return null;
    const transformed = pt.matrixTransform(ctm.inverse());
    return {
      x: Math.max(0, Math.min(imageDimensions.width, Math.round(transformed.x * 10) / 10)),
      y: Math.max(0, Math.min(imageDimensions.height, Math.round(transformed.y * 10) / 10)),
    };
  };

  // Mouse Down handler
  const handleMouseDown = (e) => {
    if (activeTool === "pan" || e.button === 1 || e.spaceKey) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      return;
    }

    if (e.button !== 0) return; // Left click only for drawing

    const coords = getOriginalImageCoords(e);
    if (!coords) return;

    if (activeTool === "point" || activeTool === "landmark") {
      setCurrentPoints([coords]);
    } else if (activeTool === "contour") {
      setIsFreehandDrawing(true);
      setCurrentPoints([coords]);
    } else if (activeTool === "polyline" || activeTool === "polygon") {
      if (activeTool === "polygon" && currentPoints.length >= 3) {
        const startPt = currentPoints[0];
        const dist = Math.hypot(coords.x - startPt.x, coords.y - startPt.y);
        if (dist < 15) {
          return;
        }
      }
      setCurrentPoints((prev) => [...prev, coords]);
    }
  };

  // Mouse Move handler
  const handleMouseMove = (e) => {
    if (isPanning) {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
      return;
    }

    if (activeTool === "contour" && isFreehandDrawing) {
      const coords = getOriginalImageCoords(e);
      if (!coords) return;
      setCurrentPoints((prev) => {
        const last = prev[prev.length - 1];
        if (!last || Math.hypot(coords.x - last.x, coords.y - last.y) >= 4) {
          return [...prev, coords];
        }
        return prev;
      });
    }
  };

  // Mouse Up handler
  const handleMouseUp = () => {
    if (isPanning) {
      setIsPanning(false);
    }
    if (activeTool === "contour" && isFreehandDrawing) {
      setIsFreehandDrawing(false);
    }
  };

  // Double click closes polygon
  const handleDoubleClick = () => {
    if (activeTool === "polygon" && currentPoints.length >= 3) {
      setUiMessage("Polygon closed. Review properties in inspector and click 'Save Annotation'.");
    }
  };

  // Undo last point
  const handleUndo = () => {
    setCurrentPoints((prev) => prev.slice(0, -1));
  };

  // Clear current drawing
  const handleClear = () => {
    setCurrentPoints([]);
    setErrorMessage(null);
    setUiMessage(null);
  };

  // Zoom controls
  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 4.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
  const handleResetZoom = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Save current annotation
  const handleSaveAnnotation = async () => {
    if (currentPoints.length === 0) {
      setErrorMessage("No coordinates placed. Draw points or a contour on the canvas first.");
      return;
    }

    setErrorMessage(null);
    setUiMessage(null);

    const payload = {
      analysis_id: selectedAnalysisId || null,
      image_filename: selectedImageFilename || "image.png",
      annotation_type: annotationType,
      annotator_label: annotatorLabel,
      points: currentPoints,
      frame_index: selectedFrameIndex,
      metadata: {
        description: description || undefined,
        region_name: regionName || undefined,
        landmark_name: landmarkName || undefined,
        image_dimensions: imageDimensions,
      },
    };

    try {
      await createAnnotation(payload);
      setUiMessage(`Annotation '${annotatorLabel}' saved successfully.`);
      setCurrentPoints([]);
      fetchAnnotations();
    } catch (err) {
      setErrorMessage(err.message || "Failed to save annotation.");
    }
  };

  // Delete annotation
  const handleDeleteAnnotation = async (id) => {
    if (!window.confirm("Are you sure you want to delete this reference annotation?")) return;
    try {
      await deleteAnnotation(id);
      fetchAnnotations();
    } catch (err) {
      setErrorMessage(err.message || "Failed to delete annotation.");
    }
  };

  // Convert annotation to ROI
  const handleConvertToRoi = async (id) => {
    try {
      const roiConfig = await convertAnnotationToRoi(id);
      setRoiSuccessMessage(
        `ROI generated: Type '${roiConfig.type}' with ${roiConfig.coordinates?.length || 0} vertices. Ready for masked deformation analysis.`
      );
    } catch (err) {
      setErrorMessage(err.message || "ROI conversion failed.");
    }
  };

  // Export Annotations
  const handleExport = async () => {
    if (!selectedAnalysisId) return;
    try {
      const pkg = await exportAnnotations(selectedAnalysisId);
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(pkg, null, 2));
      const dlAnchor = document.createElement("a");
      dlAnchor.setAttribute("href", dataStr);
      dlAnchor.setAttribute("download", `annotations_${selectedAnalysisId.slice(0, 8)}.json`);
      document.body.appendChild(dlAnchor);
      dlAnchor.click();
      dlAnchor.remove();
    } catch (err) {
      setErrorMessage(err.message || "Export failed.");
    }
  };

  // Import Annotations
  const handleImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const pkg = JSON.parse(event.target.result);
        const res = await importAnnotations(pkg);
        setUiMessage(`Imported ${res.imported_count} annotation(s) successfully.`);
        fetchAnnotations();
      } catch (err) {
        setErrorMessage(err.message || "Import failed. Invalid JSON package.");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  // Available images from analysis
  const availableImages = useMemo(() => {
    const list = [];
    if (activeAnalysis) {
      const res = activeAnalysis.result || {};
      const img1 = activeAnalysis.image1_filename || res.image1 || activeAnalysis.image1;
      const img2 = activeAnalysis.image2_filename || res.image2 || activeAnalysis.image2;
      const frameList = activeAnalysis.image_filenames || res.images || [];

      if (img1) {
        list.push({
          filename: img1,
          label: "Frame 1 (Reference)",
          frameIndex: 0,
        });
      }
      if (img2 && img2 !== img1) {
        list.push({
          filename: img2,
          label: "Frame 2 (Deformed)",
          frameIndex: 1,
        });
      }
      if (Array.isArray(frameList)) {
        frameList.forEach((fn, idx) => {
          if (!list.find((img) => img.filename === fn)) {
            list.push({
              filename: fn,
              label: `Frame ${idx + 1}`,
              frameIndex: idx,
            });
          }
        });
      }
    }
    return list;
  }, [activeAnalysis]);

  // Active image URL using getFrameImageUrl
  const activeImageUrl = selectedImageFilename
    ? getFrameImageUrl(selectedImageFilename)
    : "";


  // Category counts
  const categoryCounts = useMemo(() => {
    const counts = { point: 0, landmark: 0, polyline: 0, polygon: 0, contour: 0 };
    savedAnnotations.forEach((ann) => {
      const t = ann.annotation_type;
      if (counts[t] !== undefined) counts[t]++;
      else if (t === "region") counts.polygon++;
    });
    return counts;
  }, [savedAnnotations]);

  // Active workflow step
  const activeWorkflowStep = useMemo(() => {
    if (savedAnnotations.length > 0) return 4;
    if (currentPoints.length > 0) return 3;
    if (selectedImageFilename) return 2;
    return 1;
  }, [savedAnnotations, currentPoints, selectedImageFilename]);

  return (
    <div className="cdl-anno-page">
      {/* 1. Page Header & Breadcrumbs */}
      <div className="cdl-anno-header-wrap">
        <div className="cdl-anno-title-area">
          <div className="cdl-anno-breadcrumb">
            <Link to="/studies" className="bc-link">
              📁 Studies
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Annotation Workspace</span>
          </div>

          <div className="cdl-anno-pill-row">
            <span className="cdl-anno-badge cdl-anno-badge-blue">
              🔬 Scientific Annotation Lab
            </span>
            <span className="cdl-anno-badge cdl-anno-badge-purple">
              Manual Reference Grounding
            </span>
            {selectedAnalysisId && (
              <span className="cdl-anno-badge cdl-anno-badge-slate" style={{ fontFamily: "monospace" }}>
                Analysis: {selectedAnalysisId.slice(0, 8)}...
              </span>
            )}
            {selectedImageFilename && (
              <span className="cdl-anno-badge cdl-anno-badge-emerald">
                {selectedImageFilename}
              </span>
            )}
          </div>

          <h1 className="cdl-anno-title">Cardiac Image Annotation Workstation</h1>
          <p className="cdl-anno-subtitle">
            Interactive high-precision reference delineation for quantitative real-image motion, strain tensor validation, and anatomical boundary grounding.
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="cdl-anno-header-actions">
          {selectedAnalysisId && (
            <Link
              to={`/real-validation/${selectedAnalysisId}`}
              className="cdl-anno-btn-primary"
              title="Run real-image validation benchmark using these annotations"
            >
              📊 Run Real-Image Benchmark
            </Link>
          )}

          <button
            type="button"
            className="cdl-anno-btn-secondary"
            onClick={handleExport}
            disabled={savedAnnotations.length === 0}
            title="Export annotations as JSON package"
          >
            📥 Export JSON
          </button>

          <label className="cdl-anno-btn-secondary" style={{ cursor: "pointer" }} title="Import annotations from JSON">
            📤 Import JSON
            <input
              type="file"
              accept=".json"
              onChange={handleImportFile}
              style={{ display: "none" }}
            />
          </label>
        </div>
      </div>

      {/* 2. Top 5-Step Workflow Progress Tracker */}
      <div className="cdl-anno-workflow-card">
        <div className="cdl-anno-workflow-track">
          <div className={`cdl-anno-workflow-step ${activeWorkflowStep >= 1 ? (activeWorkflowStep > 1 ? "completed" : "active") : ""}`}>
            <div className="cdl-anno-step-num">{activeWorkflowStep > 1 ? "✓" : "1"}</div>
            <div className="cdl-anno-step-info">
              <span className="cdl-anno-step-title">1. Select Image</span>
              <span className="cdl-anno-step-sub">Analysis &amp; Frame</span>
            </div>
          </div>

          <div className={`cdl-anno-workflow-step ${activeWorkflowStep >= 2 ? (activeWorkflowStep > 2 ? "completed" : "active") : ""}`}>
            <div className="cdl-anno-step-num">{activeWorkflowStep > 2 ? "✓" : "2"}</div>
            <div className="cdl-anno-step-info">
              <span className="cdl-anno-step-title">2. Select Tool</span>
              <span className="cdl-anno-step-sub">Point, Polygon, Landmark</span>
            </div>
          </div>

          <div className={`cdl-anno-workflow-step ${activeWorkflowStep >= 3 ? (activeWorkflowStep > 3 ? "completed" : "active") : ""}`}>
            <div className="cdl-anno-step-num">{activeWorkflowStep > 3 ? "✓" : "3"}</div>
            <div className="cdl-anno-step-info">
              <span className="cdl-anno-step-title">3. Draw Reference</span>
              <span className="cdl-anno-step-sub">Delineate boundary</span>
            </div>
          </div>

          <div className={`cdl-anno-workflow-step ${activeWorkflowStep >= 4 ? (activeWorkflowStep > 4 ? "completed" : "active") : ""}`}>
            <div className="cdl-anno-step-num">{activeWorkflowStep > 4 ? "✓" : "4"}</div>
            <div className="cdl-anno-step-info">
              <span className="cdl-anno-step-title">4. Save / Export</span>
              <span className="cdl-anno-step-sub">Record geometry</span>
            </div>
          </div>

          <div className={`cdl-anno-workflow-step ${activeWorkflowStep >= 5 ? "active" : ""}`}>
            <div className="cdl-anno-step-num">5</div>
            <div className="cdl-anno-step-info">
              <span className="cdl-anno-step-title">5. Validate Benchmark</span>
              <span className="cdl-anno-step-sub">Quantify error vs flow</span>
            </div>
          </div>
        </div>
      </div>

      {/* Non-Diagnostic Research Disclaimer */}
      <div className="cdl-anno-disclaimer-card">
        <span className="cdl-anno-disclaimer-badge">Research Notice</span>
        <p className="cdl-anno-disclaimer-text">
          Manual annotations serve as subjective reference labels for computational benchmarking and software verification. They do <strong>not</strong> establish clinical ground truth or anatomical diagnostic accuracy.
        </p>
      </div>

      {/* Notifications / Alerts */}
      {errorMessage && (
        <div className="cdl-anno-banner cdl-anno-banner-error">
          <span>⚠️ {errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)} style={{ border: "none", background: "transparent", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {uiMessage && (
        <div className="cdl-anno-banner cdl-anno-banner-success">
          <span>✅ {uiMessage}</span>
          <button type="button" onClick={() => setUiMessage(null)} style={{ border: "none", background: "transparent", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {roiSuccessMessage && (
        <div className="cdl-anno-banner cdl-anno-banner-info">
          <span>🎯 {roiSuccessMessage}</span>
          <button type="button" onClick={() => setRoiSuccessMessage(null)} style={{ border: "none", background: "transparent", cursor: "pointer" }}>✕</button>
        </div>
      )}

      {/* 3. Main 3-Zone Workspace Layout */}
      <div className="cdl-anno-workspace-grid">
        {/* =================================================================
           ZONE 1: LEFT TOOL PANEL
           ================================================================= */}
        <div className="cdl-anno-tool-col">
          {/* Analysis & Image Frame Selector Card */}
          <div className="cdl-anno-panel-card">
            <div className="cdl-anno-panel-header">
              <span>Target Analysis</span>
              <span className="cdl-anno-badge cdl-anno-badge-slate">{historyList.length} Runs</span>
            </div>

            <div className="cdl-anno-select-group">
              <label className="cdl-anno-select-label">Analysis Session:</label>
              <select
                value={selectedAnalysisId}
                onChange={(e) => setSelectedAnalysisId(e.target.value)}
                className="cdl-anno-select"
              >
                {historyList.map((h) => {
                  const aid = h.id || h.analysis_id || "";
                  const imgLabel =
                    h.image1_filename ||
                    h.result?.image1 ||
                    h.study?.title ||
                    "Analysis Run";
                  return (
                    <option key={aid} value={aid}>
                      {aid ? aid.slice(0, 8) + "..." : "Analysis"} ({imgLabel})
                    </option>
                  );
                })}
              </select>

            </div>

            <div className="cdl-anno-select-group">
              <label className="cdl-anno-select-label">Active Image Frame:</label>
              <select
                value={selectedImageFilename}
                onChange={(e) => {
                  setSelectedImageFilename(e.target.value);
                  const matched = availableImages.find((img) => img.filename === e.target.value);
                  if (matched) setSelectedFrameIndex(matched.frameIndex);
                }}
                className="cdl-anno-select"
              >
                {availableImages.map((img) => (
                  <option key={img.filename} value={img.filename}>
                    {img.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Annotation Tools Selector Card */}
          <div className="cdl-anno-panel-card">
            <div className="cdl-anno-panel-header">
              <span>Annotation Tools</span>
              <span className="cdl-anno-badge cdl-anno-badge-blue">{activeTool.toUpperCase()}</span>
            </div>

            <div className="cdl-anno-tools-list">
              {TOOL_DEFS.map((tool) => (
                <button
                  key={tool.id}
                  type="button"
                  className={`cdl-anno-tool-btn ${activeTool === tool.id ? "active" : ""}`}
                  onClick={() => {
                    setActiveTool(tool.id);
                    if (tool.type) setAnnotationType(tool.type);
                  }}
                >
                  <div className="cdl-anno-tool-icon-label">
                    <span>{tool.icon}</span>
                    <span>{tool.label}</span>
                  </div>
                  <span className="cdl-anno-tool-badge">{tool.shortcut}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Help Card */}
          <div className="cdl-anno-panel-card" style={{ fontSize: 12, color: "#64748b", lineHeight: 1.5 }}>
            <strong style={{ color: "#0f172a", display: "block", marginBottom: 4 }}>💡 Drawing Tips:</strong>
            {activeTool === "polygon" && "Click consecutive vertices. Click the pulsing green start node or double-click to close the polygon."}
            {activeTool === "polyline" && "Click consecutive points along the boundary. Press Undo to remove the last placed point."}
            {activeTool === "contour" && "Hold left click and drag smoothly over the myocardial boundary for freehand tracing."}
            {activeTool === "landmark" && "Click a single point to mark an anatomical feature (e.g. Apex, Base, Valve insertion)."}
            {activeTool === "point" && "Click to place a single fiducial displacement tracking marker."}
            {activeTool === "pan" && "Click and drag to pan the canvas. Or hold Spacebar while using any drawing tool."}
          </div>
        </div>

        {/* =================================================================
           ZONE 2: CENTER SCIENTIFIC ANNOTATION CANVAS
           ================================================================= */}
        <div className="cdl-anno-canvas-col">
          <div className="cdl-anno-canvas-card">
            {/* Floating Scientific Toolbar */}
            <div className="cdl-anno-floating-toolbar">
              <div className="cdl-anno-tool-group">
                <button type="button" className="cdl-anno-btn-mini" onClick={handleZoomOut} title="Zoom Out">
                  −
                </button>
                <span className="cdl-anno-zoom-readout">{Math.round(zoom * 100)}%</span>
                <button type="button" className="cdl-anno-btn-mini" onClick={handleZoomIn} title="Zoom In">
                  +
                </button>
                <button type="button" className="cdl-anno-btn-mini" onClick={handleResetZoom} title="Reset View (1:1)">
                  ↺ Fit
                </button>
              </div>

              <div className="cdl-anno-tool-group">
                <button
                  type="button"
                  className="cdl-anno-btn-mini"
                  onClick={handleUndo}
                  disabled={currentPoints.length === 0}
                  title="Undo last placed point"
                >
                  ↩ Undo Point
                </button>
                <button
                  type="button"
                  className="cdl-anno-btn-mini"
                  onClick={handleClear}
                  disabled={currentPoints.length === 0}
                  title="Clear in-progress drawing"
                >
                  ✕ Clear
                </button>
                <button
                  type="button"
                  className={`cdl-anno-btn-mini ${showOverlays ? "active" : ""}`}
                  onClick={() => setShowOverlays(!showOverlays)}
                  title="Toggle visibility of saved reference overlays"
                >
                  👁️ {showOverlays ? "Overlays On" : "Overlays Off"}
                </button>
              </div>
            </div>

            {/* Viewport Surface */}
            <div
              className={`cdl-anno-viewport ${isPanning ? "panning" : ""}`}
              ref={containerRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onDoubleClick={handleDoubleClick}
            >
              {!selectedImageFilename ? (
                <div style={{ textAlign: "center", color: "#64748b" }}>
                  <span style={{ fontSize: 36, display: "block", marginBottom: 12 }}>🔬</span>
                  <p style={{ margin: 0, fontSize: 13 }}>Select an analysis session and image to begin annotation.</p>
                </div>
              ) : (
                <div
                  className="cdl-anno-transform-wrap"
                  style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                    transformOrigin: "center center",
                  }}
                >
                  {/* Cardiac Image Layer */}
                  <img
                    src={activeImageUrl}
                    alt="Cardiac Frame"
                    className="cdl-anno-cardiac-img"
                    onLoad={handleImageLoad}
                    draggable={false}
                  />

                  {/* SVG Annotation Geometry Layer (1:1 with natural resolution) */}
                  {imageLoaded && (
                    <svg
                      ref={svgRef}
                      className="cdl-anno-svg-overlay"
                      viewBox={`0 0 ${imageDimensions.width} ${imageDimensions.height}`}
                      width={imageDimensions.width}
                      height={imageDimensions.height}
                    >
                      {/* Render Saved Annotations */}
                      {showOverlays &&
                        savedAnnotations.map((ann) => {
                          const pts = ann.points || [];
                          const isContour = ["polygon", "contour", "region"].includes(ann.annotation_type);
                          const isLine = ann.annotation_type === "polyline";
                          const isPt = ["point", "landmark"].includes(ann.annotation_type);

                          if (isContour && pts.length >= 3) {
                            const ptsStr = pts.map((p) => `${p.x},${p.y}`).join(" ");
                            return (
                              <g key={ann.id} className="saved-annotation-group">
                                <polygon points={ptsStr} className="saved-polygon-shape" />
                                {pts.map((p, i) => (
                                  <circle key={i} cx={p.x} cy={p.y} r={3} className="saved-vertex-point" />
                                ))}
                                {ann.metadata?.centroid && (
                                  <text
                                    x={ann.metadata.centroid.x}
                                    y={ann.metadata.centroid.y}
                                    className="saved-label-text"
                                  >
                                    {ann.annotator_label}
                                  </text>
                                )}
                              </g>
                            );
                          }


                          if (isLine && pts.length >= 2) {
                            const ptsStr = pts.map((p) => `${p.x},${p.y}`).join(" ");
                            return (
                              <polyline key={ann.id} points={ptsStr} className="saved-polyline-shape" />
                            );
                          }

                          if (isPt && pts.length >= 1) {
                            const p = pts[0];
                            return (
                              <g key={ann.id}>
                                <circle cx={p.x} cy={p.y} r={5} className="saved-landmark-point" />
                                <text x={p.x + 8} y={p.y + 4} className="saved-landmark-text">
                                  {ann.metadata?.landmark_name || ann.annotator_label}
                                </text>
                              </g>
                            );
                          }
                          return null;
                        })}

                      {/* Render In-Progress Draft Points */}
                      {currentPoints.length > 0 && (
                        <g className="in-progress-group">
                          {activeTool === "polygon" && currentPoints.length >= 3 && (
                            <polygon
                              points={currentPoints.map((p) => `${p.x},${p.y}`).join(" ")}
                              className="draft-polygon-shape"
                            />
                          )}

                          {(activeTool === "polyline" || activeTool === "polygon" || activeTool === "contour") &&
                            currentPoints.length >= 2 && (
                              <polyline
                                points={currentPoints.map((p) => `${p.x},${p.y}`).join(" ")}
                                className="draft-polyline-shape"
                              />
                            )}

                          {currentPoints.map((p, i) => (
                            <circle
                              key={i}
                              cx={p.x}
                              cy={p.y}
                              r={i === 0 && activeTool === "polygon" ? 6 : 4}
                              className={`draft-vertex-point ${i === 0 && activeTool === "polygon" ? "closing-target" : ""}`}
                            />
                          ))}
                        </g>
                      )}
                    </svg>
                  )}
                </div>
              )}
            </div>

            {/* Canvas Bottom Status Bar */}
            <div className="cdl-anno-canvas-footer">
              <div>
                {currentPoints.length > 0 ? (
                  <span>
                    In-progress vertices: <strong>{currentPoints.length}</strong>. Double click or click start node to close.
                  </span>
                ) : (
                  <span>
                    Tool active: <strong>{activeTool.toUpperCase()}</strong> &bull; Resolution:{" "}
                    <strong>{imageDimensions.width} × {imageDimensions.height} px</strong>
                  </span>
                )}
              </div>
              <div>
                <span>Saved Overlays: <strong>{savedAnnotations.length}</strong></span>
              </div>
            </div>
          </div>
        </div>

        {/* =================================================================
           ZONE 3: RIGHT ANNOTATION INSPECTOR PANEL
           ================================================================= */}
        <div className="cdl-anno-inspector-col">
          {/* Category Counts Tiles */}
          <div className="cdl-anno-panel-card" style={{ padding: "12px 14px" }}>
            <div className="cdl-anno-counts-grid">
              <div className="cdl-anno-count-tile">
                <span className="cdl-anno-count-num">{categoryCounts.point}</span>
                <span className="cdl-anno-count-lbl">Points</span>
              </div>
              <div className="cdl-anno-count-tile">
                <span className="cdl-anno-count-num">{categoryCounts.landmark}</span>
                <span className="cdl-anno-count-lbl">Landmarks</span>
              </div>
              <div className="cdl-anno-count-tile">
                <span className="cdl-anno-count-num">{categoryCounts.polyline}</span>
                <span className="cdl-anno-count-lbl">Polylines</span>
              </div>
              <div className="cdl-anno-count-tile">
                <span className="cdl-anno-count-num">{categoryCounts.polygon}</span>
                <span className="cdl-anno-count-lbl">Polygons</span>
              </div>
            </div>
          </div>

          {/* Properties & Save Card */}
          <div className="cdl-anno-panel-card">
            <div className="cdl-anno-panel-header">
              <span>Annotation Properties</span>
              <span className={`cdl-anno-badge ${currentPoints.length > 0 ? "cdl-anno-badge-amber" : "cdl-anno-badge-slate"}`}>
                {currentPoints.length > 0 ? "Draft Active" : "Inspector"}
              </span>
            </div>

            <div className="cdl-anno-form-group">
              <label>Preset Anatomical Label:</label>
              <select
                value={annotatorLabel}
                onChange={(e) => setAnnotatorLabel(e.target.value)}
                className="cdl-anno-select"
              >
                {PRESET_LABELS.map((lbl) => (
                  <option key={lbl} value={lbl}>
                    {lbl}
                  </option>
                ))}
              </select>
            </div>

            <div className="cdl-anno-form-group">
              <label>Custom Label / Landmark Name:</label>
              <input
                type="text"
                placeholder="e.g. Apex, Basal Septum, Papillary..."
                value={landmarkName}
                onChange={(e) => setLandmarkName(e.target.value)}
                className="cdl-anno-text-input"
              />
            </div>

            <div className="cdl-anno-form-group">
              <label>Annotation Type:</label>
              <select
                value={annotationType}
                onChange={(e) => setAnnotationType(e.target.value)}
                className="cdl-anno-select"
              >
                <option value="polygon">Polygon (Closed Region)</option>
                <option value="contour">Freehand Contour</option>
                <option value="landmark">Landmark Point</option>
                <option value="polyline">Polyline</option>
                <option value="region">Region of Interest (ROI)</option>
              </select>
            </div>

            <div className="cdl-anno-form-group">
              <label>Description / Notes:</label>
              <input
                type="text"
                placeholder="Optional annotator notes..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="cdl-anno-text-input"
              />
            </div>

            <button
              type="button"
              className="cdl-anno-btn-primary"
              onClick={handleSaveAnnotation}
              disabled={currentPoints.length === 0}
              style={{ justifyContent: "center", marginTop: 4 }}
            >
              💾 Save Annotation
            </button>
          </div>

          {/* Saved Annotations List Card */}
          <div className="cdl-anno-panel-card">
            <div className="cdl-anno-panel-header">
              <span>Saved Annotations ({savedAnnotations.length})</span>
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  type="button"
                  className="cdl-anno-btn-mini"
                  onClick={handleExport}
                  title="Export Annotations JSON"
                >
                  📥 Export
                </button>
              </div>
            </div>

            {loadingAnnotations ? (
              <p style={{ color: "#64748b", fontSize: 12, margin: 0 }}>Loading saved annotations...</p>
            ) : savedAnnotations.length === 0 ? (
              <p style={{ color: "#64748b", fontSize: 12, margin: 0 }}>No reference annotations saved for this image.</p>
            ) : (
              <div className="cdl-anno-items-list">
                {savedAnnotations.map((ann) => (
                  <div key={ann.id} className="cdl-anno-item-card">
                    <div className="cdl-anno-item-top">
                      <strong className="cdl-anno-item-title">{ann.annotator_label}</strong>
                      <span className="cdl-anno-badge cdl-anno-badge-blue" style={{ fontSize: 9.5 }}>
                        {ann.annotation_type}
                      </span>
                    </div>

                    <div className="cdl-anno-item-meta">
                      <span>Points: {ann.points?.length || 0}</span>
                      {ann.metadata?.area && (
                        <span>Area: {Math.round(ann.metadata.area)} px²</span>
                      )}
                      {ann.metadata?.landmark_name && (
                        <span>&bull; {ann.metadata.landmark_name}</span>
                      )}
                    </div>

                    <div className="cdl-anno-item-actions">
                      {["polygon", "contour", "region"].includes(ann.annotation_type) && (
                        <button
                          type="button"
                          className="cdl-anno-btn-action roi"
                          onClick={() => handleConvertToRoi(ann.id)}
                          title="Convert to ROI definition"
                        >
                          Convert to ROI
                        </button>
                      )}
                      <button
                        type="button"
                        className="cdl-anno-btn-action delete"
                        onClick={() => handleDeleteAnnotation(ann.id)}
                        title="Delete annotation"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Real-Image Validation Action Card */}
          {selectedAnalysisId && (
            <div className="cdl-anno-benchmark-card">
              <h4 className="cdl-anno-benchmark-title">
                <span>📊</span> Real-Image Validation Benchmark
              </h4>
              <p className="cdl-anno-benchmark-desc">
                Evaluate optical flow displacement and strain tensors against these saved anatomical reference landmarks.
              </p>
              <Link
                to={`/real-validation/${selectedAnalysisId}`}
                className="cdl-anno-btn-primary"
                style={{ justifyContent: "center", textDecoration: "none" }}
              >
                Launch Real-Image Benchmark &rarr;
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
