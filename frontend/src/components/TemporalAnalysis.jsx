import { useState, useEffect, useRef, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  uploadImage,
  uploadVideo,
  getVideoInfo,
  extractVideoFrames,
  analyzeTemporalStrain,
  previewROITracking,
  getStudies,
  addAnalysisToStudy,
  getFrameImageUrl,
} from "../services/api";
import TemporalChart from "./TemporalChart";
import FingerprintChart from "./FingerprintChart";
import SummaryCards from "./SummaryCards";
import InterpretationPanel from "./InterpretationPanel";
import MethodologySection from "./MethodologySection";
import CalibrationPanel from "./CalibrationPanel";
import ROISelector from "./ROISelector";
import ROIComparisonView from "./ROIComparisonView";
import TrackingTrajectoryChart from "./TrackingTrajectoryChart";
import TrackedROIKeyframeGallery from "./TrackedROIKeyframeGallery";
import TrackedROIPreviewModal from "./TrackedROIPreviewModal";
import { useAnalysis } from "../context/AnalysisContext";

export default function TemporalAnalysis({ initialMode = "sequence" }) {
  const { setLatestTemporalResult } = useAnalysis();

  // Mode: "sequence" (Image Sequence) | "video" (Video Upload & Extraction)
  const [subMode, setSubMode] = useState(initialMode);

  // ── ROI State ──────────────────────────────────────────────────────────
  const [roi, setRoi] = useState({
    enabled: false,
    type: "rectangle",
    coordinates: null,
    mode: "fixed",
  });

  // ── ROI Tracking Preview State ─────────────────────────────────────────
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [previewData, setPreviewData] = useState(null);

  // ── Image Sequence State ────────────────────────────────────────────────
  const [sequenceFiles, setSequenceFiles] = useState([]); // array of { id, file, name, previewUrl }
  const [selectedSequenceIds, setSelectedSequenceIds] = useState([]);

  // ── Video Mode State ───────────────────────────────────────────────────
  const [videoFile, setVideoFile] = useState(null);
  const [uploadingVideo, setUploadingVideo] = useState(false);
  const [uploadedVideoData, setUploadedVideoData] = useState(null);
  const [videoInfo, setVideoInfo] = useState(null);
  const [frameInterval, setFrameInterval] = useState(1);
  const [maxFrames, setMaxFrames] = useState(50);
  const [extractingFrames, setExtractingFrames] = useState(false);
  const [extractedFrames, setExtractedFrames] = useState([]); // array of registered filenames
  const [selectedExtractedFrames, setSelectedExtractedFrames] = useState([]);

  // ── Playback & Active Frame State ──────────────────────────────────────
  const [activeFrameIndex, setActiveFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 0.5x, 1x, 2x
  const playbackTimerRef = useRef(null);

  // ── Global Processing / Results State ─────────────────────────────────
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progressMsg, setProgressMsg] = useState("");
  const [result, setResult] = useState(null);

  // ── Spatial Calibration State ──────────────────────────────────────────
  const [calibration, setCalibration] = useState({
    enabled: false,
    pixel_spacing_x: "",
    pixel_spacing_y: "",
    unit: "mm",
  });

  // ── Study Selector State ───────────────────────────────────────────────
  const [availableStudies, setAvailableStudies] = useState([]);
  const [selectedStudyId, setSelectedStudyId] = useState("");

  useEffect(() => {
    getStudies()
      .then((data) => setAvailableStudies(data || []))
      .catch(() => {});
  }, []);

  // Selected study object
  const activeStudy = useMemo(() => {
    return availableStudies.find((s) => s.id === selectedStudyId) || null;
  }, [availableStudies, selectedStudyId]);

  // Clean up object URLs on unmount or file change
  useEffect(() => {
    return () => {
      sequenceFiles.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
    };
  }, [sequenceFiles]);

  // Total frames available in current mode
  const currentFramesList = useMemo(() => {
    if (subMode === "sequence") {
      return sequenceFiles.map((item, idx) => ({
        id: item.id,
        name: item.name || `Frame ${idx + 1}`,
        url: item.previewUrl,
        file: item.file,
        index: idx,
      }));
    } else {
      return extractedFrames.map((fn, idx) => ({
        id: fn,
        name: `Frame ${idx + 1}`,
        url: getFrameImageUrl(fn),
        filename: fn,
        index: idx,
      }));
    }
  }, [subMode, sequenceFiles, extractedFrames]);

  // Adjust activeFrameIndex bounds
  useEffect(() => {
    if (activeFrameIndex >= currentFramesList.length && currentFramesList.length > 0) {
      setActiveFrameIndex(currentFramesList.length - 1);
    }
  }, [currentFramesList.length, activeFrameIndex]);

  // Cine Playback Loop
  useEffect(() => {
    if (isPlaying && currentFramesList.length > 1) {
      const intervalMs = Math.round(300 / playbackSpeed);
      playbackTimerRef.current = setInterval(() => {
        setActiveFrameIndex((prev) => (prev + 1) % currentFramesList.length);
      }, intervalMs);
    } else {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    }
    return () => {
      if (playbackTimerRef.current) clearInterval(playbackTimerRef.current);
    };
  }, [isPlaying, currentFramesList.length, playbackSpeed]);

  // Active displayed frame item
  const activeFrame = currentFramesList[activeFrameIndex] || null;

  // ── Sequence Handlers ─────────────────────────────────────────────────
  const handleSequenceFilesChange = (e) => {
    const rawFiles = Array.from(e.target.files || []);
    if (rawFiles.length === 0) return;

    const newItems = rawFiles.map((file, idx) => ({
      id: `${file.name}_${file.size}_${file.lastModified}_${idx}`,
      file,
      name: file.name,
      previewUrl: URL.createObjectURL(file),
    }));

    setSequenceFiles((prev) => {
      const combined = [...prev, ...newItems];
      setSelectedSequenceIds(combined.map((item) => item.id));
      return combined;
    });
    setError(null);
  };

  const handleToggleSequenceFrame = (id) => {
    setSelectedSequenceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleClearAllSequence = () => {
    sequenceFiles.forEach((item) => {
      if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    });
    setSequenceFiles([]);
    setSelectedSequenceIds([]);
    setActiveFrameIndex(0);
    setIsPlaying(false);
  };

  // ── Video Handlers ────────────────────────────────────────────────────
  const handleVideoFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setVideoFile(file);
      setUploadedVideoData(null);
      setVideoInfo(null);
      setExtractedFrames([]);
      setSelectedExtractedFrames([]);
      setError(null);
    }
  };

  const handleUploadAndProbeVideo = async () => {
    if (!videoFile) {
      setError("Please select a video file first.");
      return;
    }

    setUploadingVideo(true);
    setError(null);
    try {
      const uploadRes = await uploadVideo(videoFile);
      setUploadedVideoData(uploadRes);

      const info = await getVideoInfo(uploadRes.saved_filename);
      setVideoInfo(info);
    } catch (err) {
      setError(err.message || "Failed to upload or read video metadata.");
    } finally {
      setUploadingVideo(false);
    }
  };

  const handleExtractFrames = async () => {
    if (!uploadedVideoData?.saved_filename) {
      setError("Please upload a video before extracting frames.");
      return;
    }

    setExtractingFrames(true);
    setError(null);
    try {
      const res = await extractVideoFrames(
        uploadedVideoData.saved_filename,
        frameInterval,
        maxFrames
      );
      setExtractedFrames(res.frames || []);
      setSelectedExtractedFrames(res.frames || []);
      setActiveFrameIndex(0);
    } catch (err) {
      setError(err.message || "Failed to extract frames from video.");
    } finally {
      setExtractingFrames(false);
    }
  };

  // ── Preview ROI Tracking ───────────────────────────────────────────────
  const handlePreviewTracking = async () => {
    setPreviewError(null);
    setPreviewLoading(true);
    setPreviewModalOpen(true);

    try {
      if (!roi.enabled || !roi.coordinates) {
        throw new Error("Please enable and draw an ROI region before previewing tracking.");
      }

      let filenamesToProcess = [];

      if (subMode === "sequence") {
        const selectedItems = sequenceFiles.filter((item) =>
          selectedSequenceIds.includes(item.id)
        );

        if (selectedItems.length < 2) {
          throw new Error("Preview tracking requires at least 2 selected frames.");
        }

        for (let i = 0; i < selectedItems.length; i++) {
          const uploadRes = await uploadImage(selectedItems[i].file);
          if (!uploadRes.saved_filename) {
            throw new Error(`Failed to upload ${selectedItems[i].name}`);
          }
          filenamesToProcess.push(uploadRes.saved_filename);
        }
      } else {
        if (selectedExtractedFrames.length < 2) {
          throw new Error("Preview tracking requires at least 2 selected extracted frames.");
        }
        filenamesToProcess = [...selectedExtractedFrames];
      }

      const previewRes = await previewROITracking(filenamesToProcess, roi);
      setPreviewData(previewRes);
    } catch (err) {
      setPreviewError(err.message || "Failed to generate tracking preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  // ── Unified Temporal Execution ─────────────────────────────────────────
  const handleRunTemporalAnalysis = async () => {
    setError(null);

    let filenamesToProcess = [];

    if (subMode === "sequence") {
      const selectedItems = sequenceFiles.filter((item) =>
        selectedSequenceIds.includes(item.id)
      );

      if (selectedItems.length < 2) {
        setError(
          "Image Sequence mode requires at least 2 selected frames for temporal strain analysis."
        );
        return;
      }

      setLoading(true);
      setProgressMsg(`Uploading 0 of ${selectedItems.length} frames...`);

      try {
        for (let i = 0; i < selectedItems.length; i++) {
          setProgressMsg(`Uploading frame ${i + 1} of ${selectedItems.length}...`);
          const uploadRes = await uploadImage(selectedItems[i].file);
          if (!uploadRes.saved_filename) {
            throw new Error(`Failed to upload ${selectedItems[i].name}`);
          }
          filenamesToProcess.push(uploadRes.saved_filename);
        }
      } catch (err) {
        setError(err.message || "Error uploading frame sequence.");
        setLoading(false);
        setProgressMsg("");
        return;
      }
    } else {
      if (selectedExtractedFrames.length < 2) {
        setError(
          "Video mode requires at least 2 selected extracted frames for temporal analysis."
        );
        return;
      }
      filenamesToProcess = [...selectedExtractedFrames];
      setLoading(true);
    }

    // Validate calibration inputs if enabled
    let calPayload = null;
    if (calibration.enabled) {
      const sx = parseFloat(calibration.pixel_spacing_x);
      const sy = parseFloat(calibration.pixel_spacing_y);
      if (isNaN(sx) || isNaN(sy) || sx <= 0 || sy <= 0) {
        setError("Spatial calibration requires valid positive numbers (> 0) for Pixel Spacing X and Y.");
        setLoading(false);
        return;
      }
      calPayload = {
        enabled: true,
        pixel_spacing_x: sx,
        pixel_spacing_y: sy,
        unit: calibration.unit,
      };
    }

    // Validate optional ROI if enabled
    let roiPayload = null;
    if (roi.enabled) {
      if (!roi.coordinates) {
        setError("ROI analysis is enabled, but no region has been defined. Please draw an ROI on the canvas.");
        setLoading(false);
        return;
      }
      roiPayload = roi;
    }

    setProgressMsg(
      `Calculating Farnebäck flow & strain tensors across ${filenamesToProcess.length} frames...`
    );

    try {
      const temporalData = await analyzeTemporalStrain(filenamesToProcess, calPayload, roiPayload);
      setResult(temporalData);
      setLatestTemporalResult(temporalData);

      if (selectedStudyId && temporalData.analysis_id) {
        try {
          await addAnalysisToStudy(selectedStudyId, temporalData.analysis_id);
        } catch {
          // Non-blocking error
        }
      }
    } catch (err) {
      setError(err.message || "An error occurred during temporal strain analysis.");
    } finally {
      setLoading(false);
      setProgressMsg("");
    }
  };

  const p1 = result?.principal_strain_1?.summary;
  const fp = result?.cardiac_deformation_fingerprint?.fingerprint;

  return (
    <div className="cdl-temporal-workspace-root">
      {/* 1. TOP CONTROL BAR (MODALITY & SETTINGS) */}
      <section className="cdl-temporal-controls-panel" aria-label="Temporal Configuration Bar">
        <div className="cdl-temporal-mode-pills">
          <button
            type="button"
            className={`cdl-temporal-mode-btn ${subMode === "sequence" ? "active" : ""}`}
            onClick={() => {
              setSubMode("sequence");
              setError(null);
            }}
          >
            <span>🖼️</span>
            <span>Image Sequence</span>
          </button>
          <button
            type="button"
            className={`cdl-temporal-mode-btn ${subMode === "video" ? "active" : ""}`}
            onClick={() => {
              setSubMode("video");
              setError(null);
            }}
          >
            <span>🎬</span>
            <span>Cine Video</span>
          </button>
        </div>

        <div className="cdl-temporal-quick-configs">
          {/* Study Select */}
          <select
            className="cdl-config-select"
            style={{ width: 220 }}
            value={selectedStudyId}
            onChange={(e) => setSelectedStudyId(e.target.value)}
          >
            <option value="">Standalone Analysis (No Study)</option>
            {availableStudies.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title} {s.subject_code ? `(${s.subject_code})` : ""}
              </option>
            ))}
          </select>

          {/* Calibration Toggle */}
          <button
            type="button"
            className="cdl-btn-view-study"
            onClick={() => setCalibration((c) => ({ ...c, enabled: !c.enabled }))}
          >
            📏 {calibration.enabled ? `Calibration (${calibration.unit})` : "Pixel-Space"}
          </button>

          {/* ROI Toggle */}
          <button
            type="button"
            className="cdl-btn-view-study"
            onClick={() => setRoi((r) => ({ ...r, enabled: !r.enabled }))}
          >
            🎯 {roi.enabled ? `ROI (${roi.mode})` : "Full Image"}
          </button>
        </div>
      </section>

      {/* ERROR BANNER */}
      {error && (
        <div className="cdl-alert-banner cdl-alert-error" style={{ margin: "14px 0" }} role="alert">
          <div>
            <strong>Notice:</strong> {error}
          </div>
          <button
            className="cdl-btn-table-icon"
            onClick={() => setError(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. THREE-ZONE TEMPORAL WORKSTATION */}
      <section className="cdl-temporal-workstation-grid" aria-label="Temporal Workstation">
        {/* ====================================================================
            ZONE 1: FRAME NAVIGATOR (LEFT)
            ==================================================================== */}
        <div className="cdl-temporal-zone-left">
          <div className="cdl-nav-header">
            <h3 className="cdl-nav-title">Frame Navigator</h3>
            <span className="cdl-nav-counter-pill">
              {currentFramesList.length} Frames
            </span>
          </div>

          {/* Upload Input for Sequence */}
          {subMode === "sequence" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="cdl-upload-slot" style={{ padding: "8px 10px" }}>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.bmp,.tif,.tiff"
                  multiple
                  disabled={loading}
                  onChange={handleSequenceFilesChange}
                />
                <span style={{ fontSize: 13, fontWeight: 700, color: "#2563eb" }}>
                  + Add Frames
                </span>
                <span style={{ fontSize: 11, color: "#64748b" }}>Select 3+ image frames</span>
              </div>
              {sequenceFiles.length > 0 && (
                <button
                  type="button"
                  className="cdl-btn-table-action"
                  style={{ alignSelf: "flex-end", fontSize: 11, padding: "3px 8px" }}
                  onClick={handleClearAllSequence}
                >
                  Clear All
                </button>
              )}
            </div>
          )}

          {/* Upload Input for Video */}
          {subMode === "video" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="cdl-upload-slot" style={{ padding: "8px 10px" }}>
                <input
                  type="file"
                  accept=".mp4,.avi,.mov,.mkv,.webm"
                  disabled={uploadingVideo || extractingFrames || loading}
                  onChange={handleVideoFileSelect}
                />
                <span style={{ fontSize: 13, fontWeight: 700, color: "#2563eb" }}>
                  {videoFile ? videoFile.name : "+ Select Video"}
                </span>
                <span style={{ fontSize: 11, color: "#64748b" }}>.mp4, .avi, .mov</span>
              </div>

              {videoFile && !videoInfo && (
                <button
                  type="button"
                  className="cdl-btn-primary-action"
                  style={{ fontSize: 12, padding: "6px 12px", justifyContent: "center" }}
                  onClick={handleUploadAndProbeVideo}
                  disabled={uploadingVideo}
                >
                  {uploadingVideo ? "Probing Video..." : "Upload & Inspect"}
                </button>
              )}

              {videoInfo && extractedFrames.length === 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 11.5 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Step Interval:</span>
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={frameInterval}
                      onChange={(e) => setFrameInterval(Math.max(1, parseInt(e.target.value) || 1))}
                      style={{ width: 50, padding: "2px 4px", borderRadius: 4, border: "1px solid #cbd5e1" }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Max Frames:</span>
                    <input
                      type="number"
                      min="2"
                      max="200"
                      value={maxFrames}
                      onChange={(e) => setMaxFrames(Math.max(2, parseInt(e.target.value) || 2))}
                      style={{ width: 50, padding: "2px 4px", borderRadius: 4, border: "1px solid #cbd5e1" }}
                    />
                  </div>
                  <button
                    type="button"
                    className="cdl-btn-primary-action"
                    style={{ fontSize: 12, padding: "6px 12px", justifyContent: "center", marginTop: 4 }}
                    onClick={handleExtractFrames}
                    disabled={extractingFrames}
                  >
                    {extractingFrames ? "Extracting..." : "Extract Frames"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Scrollable Frame List */}
          <div className="cdl-frames-scroll-list">
            {currentFramesList.length === 0 ? (
              <div style={{ textAlign: "center", padding: "24px 8px", color: "#94a3b8", fontSize: 12.5 }}>
                No frames loaded yet.
              </div>
            ) : (
              currentFramesList.map((item, idx) => {
                const isSelected =
                  subMode === "sequence"
                    ? selectedSequenceIds.includes(item.id)
                    : selectedExtractedFrames.includes(item.id);
                const isActive = activeFrameIndex === idx;

                return (
                  <div
                    key={item.id}
                    className={`cdl-frame-list-item ${isActive ? "selected" : ""}`}
                    onClick={() => setActiveFrameIndex(idx)}
                  >
                    <input
                      type="checkbox"
                      className="cdl-checkbox-styled"
                      checked={isSelected}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => {
                        if (subMode === "sequence") {
                          handleToggleSequenceFrame(item.id);
                        } else {
                          setSelectedExtractedFrames((prev) =>
                            prev.includes(item.id)
                              ? prev.filter((x) => x !== item.id)
                              : [...prev, item.id]
                          );
                        }
                      }}
                    />
                    <img
                      src={item.url}
                      alt={item.name}
                      className="cdl-frame-thumb-mini"
                    />
                    <div className="cdl-frame-item-info">
                      <span className="cdl-frame-item-name">{item.name}</span>
                      <span className="cdl-frame-item-index">Index: #{idx + 1}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ====================================================================
            ZONE 2: CARDIAC FRAME VIEWER & CINE PLAYBACK (CENTER)
            ==================================================================== */}
        <div className="cdl-temporal-zone-center">
          <div className="cdl-cine-viewer-card">
            <div className="cdl-viewer-header-row">
              <div className="cdl-viewer-title-group">
                <span style={{ fontSize: 18 }}>⏱️</span>
                <h3 className="cdl-viewer-title">
                  Cardiac Cine Stream Viewer
                </h3>
              </div>
              <span className="cdl-comparison-tag">
                {currentFramesList.length > 0
                  ? `Frame ${activeFrameIndex + 1} of ${currentFramesList.length}`
                  : "Awaiting Sequence"}
              </span>
            </div>

            {/* If ROI is enabled and we have frames, embed the ROISelector on the active frame */}
            {roi.enabled && activeFrame ? (
              <div>
                <ROISelector
                  imageFile={activeFrame.file || null}
                  imageSrc={!activeFrame.file ? activeFrame.url : null}
                  roi={roi}
                  onChange={setRoi}
                  disabled={loading}
                  allowTracking={true}
                />
              </div>
            ) : (
              /* Dark Cine Canvas Stage */
              <div className="cdl-cine-screen">
                {activeFrame ? (
                  <>
                    <img
                      src={activeFrame.url}
                      alt={activeFrame.name}
                      className="cdl-cine-display-img"
                    />
                    <div className="cdl-cine-hud-badge">
                      Frame #{activeFrameIndex + 1} &bull; Kinematics: Green-Lagrangian
                    </div>
                  </>
                ) : (
                  <div className="cdl-canvas-empty-state">
                    <span className="cdl-empty-wave-icon">🫀</span>
                    <span className="cdl-empty-stage-text">
                      Upload image frames or cine video to inspect temporal deformation
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Playback Controls Bar */}
            <div className="cdl-playback-bar">
              <div className="cdl-playback-btns">
                <button
                  type="button"
                  className="cdl-playback-btn"
                  onClick={() => setActiveFrameIndex(0)}
                  disabled={currentFramesList.length === 0}
                  title="First Frame"
                >
                  ⏮
                </button>
                <button
                  type="button"
                  className="cdl-playback-btn"
                  onClick={() =>
                    setActiveFrameIndex((prev) =>
                      prev > 0 ? prev - 1 : currentFramesList.length - 1
                    )
                  }
                  disabled={currentFramesList.length === 0}
                  title="Previous Frame"
                >
                  ◀
                </button>
                <button
                  type="button"
                  className="cdl-playback-btn play-btn"
                  onClick={() => setIsPlaying(!isPlaying)}
                  disabled={currentFramesList.length < 2}
                  title={isPlaying ? "Pause" : "Play Sequence"}
                >
                  {isPlaying ? "⏸" : "▶"}
                </button>
                <button
                  type="button"
                  className="cdl-playback-btn"
                  onClick={() =>
                    setActiveFrameIndex((prev) => (prev + 1) % currentFramesList.length)
                  }
                  disabled={currentFramesList.length === 0}
                  title="Next Frame"
                >
                  ▶
                </button>
                <button
                  type="button"
                  className="cdl-playback-btn"
                  onClick={() => setActiveFrameIndex(currentFramesList.length - 1)}
                  disabled={currentFramesList.length === 0}
                  title="Last Frame"
                >
                  ⏭
                </button>
              </div>

              <div className="cdl-playback-info">
                {currentFramesList.length > 0
                  ? `Position: ${activeFrameIndex + 1} / ${currentFramesList.length}`
                  : "No Sequence"}
              </div>

              <button
                type="button"
                className="cdl-speed-toggle-btn"
                onClick={() =>
                  setPlaybackSpeed((prev) => (prev === 1 ? 2 : prev === 2 ? 0.5 : 1))
                }
              >
                Speed: {playbackSpeed}x
              </button>
            </div>

            {/* Horizontal Timeline Scrubber */}
            {currentFramesList.length > 0 && (
              <div className="cdl-horizontal-timeline" aria-label="Cardiac Cycle Timeline">
                {currentFramesList.map((f, idx) => (
                  <div
                    key={f.id}
                    className={`cdl-timeline-node ${activeFrameIndex === idx ? "active" : ""}`}
                    onClick={() => setActiveFrameIndex(idx)}
                  >
                    <div className="cdl-timeline-dot" />
                    <span className="cdl-timeline-label">F{idx + 1}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ====================================================================
            ZONE 3: METRICS INSPECTOR & START ANALYSIS (RIGHT)
            ==================================================================== */}
        <div className="cdl-temporal-zone-right">
          <div className="cdl-temporal-inspector-card">
            <div className="cdl-inspector-header">
              <h3 className="cdl-inspector-title">Temporal Metrics</h3>
              <span className="cdl-config-badge">INSPECTION</span>
            </div>

            {/* 4 Quick Metric Tiles */}
            <div className="cdl-inspector-metric-grid">
              <div className="cdl-inspector-metric-tile">
                <span className="cdl-tile-label">Frames</span>
                <span className="cdl-tile-val">{currentFramesList.length}</span>
              </div>
              <div className="cdl-inspector-metric-tile">
                <span className="cdl-tile-label">Pairs</span>
                <span className="cdl-tile-val">
                  {Math.max(0, currentFramesList.length - 1)}
                </span>
              </div>
              <div className="cdl-inspector-metric-tile">
                <span className="cdl-tile-label">Mean Strain</span>
                <span className="cdl-tile-val">
                  {p1?.mean !== undefined && p1?.mean !== null
                    ? Number(p1.mean).toFixed(4)
                    : "—"}
                </span>
              </div>
              <div className="cdl-inspector-metric-tile">
                <span className="cdl-tile-label">TSI Index</span>
                <span className="cdl-tile-val">
                  {result?.temporal_stability?.temporal_stability_index !== undefined
                    ? Number(result.temporal_stability.temporal_stability_index).toFixed(3)
                    : p1?.temporal_stability_index !== undefined
                    ? Number(p1.temporal_stability_index).toFixed(3)
                    : "—"}
                </span>
              </div>
            </div>

            {/* Configuration Checklist */}
            <div className="cdl-temporal-checklist">
              <div className="cdl-check-row">
                <span className="cdl-check-label">Study</span>
                <span className="cdl-check-val">
                  {activeStudy ? activeStudy.title : "Standalone"}
                </span>
              </div>
              <div className="cdl-check-row">
                <span className="cdl-check-label">Subject</span>
                <span className="cdl-check-val">
                  {activeStudy?.subject_code || "Unassigned"}
                </span>
              </div>
              <div className="cdl-check-row">
                <span className="cdl-check-label">Calibration</span>
                <span className="cdl-check-val">
                  {calibration.enabled ? `${calibration.unit}/px` : "Pixel-space (px)"}
                </span>
              </div>
              <div className="cdl-check-row">
                <span className="cdl-check-label">ROI Mode</span>
                <span className="cdl-check-val">
                  {roi.enabled ? `${roi.mode.toUpperCase()} (${roi.type})` : "Full Field"}
                </span>
              </div>
            </div>

            {/* ROI Tracking Preview Trigger if Tracked Mode */}
            {roi.enabled && roi.coordinates && roi.mode === "tracked" && (
              <button
                type="button"
                className="cdl-btn-view-study"
                style={{ width: "100%", justifyContent: "center" }}
                onClick={handlePreviewTracking}
                disabled={previewLoading || loading}
              >
                {previewLoading ? "Generating Preview..." : "🔍 Preview ROI Tracking"}
              </button>
            )}

            {/* Primary Execution CTA */}
            <button
              type="button"
              className="cdl-btn-start-temporal"
              onClick={handleRunTemporalAnalysis}
              disabled={
                loading ||
                uploadingVideo ||
                extractingFrames ||
                (subMode === "sequence" && selectedSequenceIds.length < 2) ||
                (subMode === "video" && selectedExtractedFrames.length < 2)
              }
            >
              <span>⏱️</span>
              <span>
                {loading ? "Calculating Kinetics..." : "Start Temporal Analysis"}
              </span>
            </button>

            {/* Progress Card during calculation */}
            {loading && (
              <div className="cdl-temporal-progress-card">
                <div className="cdl-temporal-spinner" />
                <span>{progressMsg || "Calculating Farnebäck flow & strain..."}</span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Tracked ROI Preview Modal */}
      <TrackedROIPreviewModal
        isOpen={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        loading={previewLoading}
        error={previewError}
        previewData={previewData}
      />

      {/* Calibration Panel Drawer if Enabled */}
      {calibration.enabled && (
        <div style={{ marginTop: 16 }}>
          <CalibrationPanel
            calibration={calibration}
            onChange={setCalibration}
          />
        </div>
      )}

      {/* ====================================================================
          RESULTS SECTIONS (BELOW WORKSTATION)
          ==================================================================== */}
      {result && (
        <div className="cdl-temporal-results-wrapper">
          <div className="cdl-temporal-chart-card">
            <div className="cdl-temporal-chart-header">
              <div>
                <h3 className="cdl-temporal-chart-title">Temporal Analysis Results</h3>
                <p style={{ margin: "2px 0 0", fontSize: 13, color: "#64748b" }}>
                  Processed <strong>{result.frame_count} frames</strong> ({result.pair_count} consecutive differential pairs)
                </p>
              </div>
              {result.analysis_id && (
                <Link
                  to={`/explorer/${result.analysis_id}`}
                  className="cdl-btn-view-study"
                >
                  🔭 Open Explorer →
                </Link>
              )}
            </div>

            {/* ROI Tracking Warning if present */}
            {result.tracking_warning && (
              <div className="cdl-alert-banner cdl-alert-error" style={{ margin: "12px 0" }}>
                <span>⚠️ {result.tracking_warning}</span>
              </div>
            )}

            {/* ROI vs Full Image Comparison (if ROI analyzed) */}
            {result.roi_metrics && (
              <div style={{ margin: "16px 0" }}>
                <ROIComparisonView result={result} />
              </div>
            )}

            {/* Tracked ROI Keyframe Overlays */}
            {result.tracking_previews && (
              <div style={{ margin: "16px 0" }}>
                <TrackedROIKeyframeGallery
                  trackingPreviews={result.tracking_previews}
                  trackingPath={result.tracking_path}
                />
              </div>
            )}

            {/* Tracked ROI Trajectory & Confidence Chart */}
            {result.tracking_path && (
              <div style={{ margin: "16px 0" }}>
                <TrackingTrajectoryChart
                  trackingPath={result.tracking_path}
                  trackingSummary={result.tracking_summary}
                />
              </div>
            )}

            {/* 8 Summary Metric Cards */}
            <SummaryCards
              meanDisplacement={result.displacement?.mean_displacement ?? fp?.D_mean}
              maxDisplacement={result.displacement?.max_displacement ?? fp?.D_max}
              meanPrincipalStrain={p1?.mean ?? fp?.epsilon_principal}
              maxPrincipalStrain={p1?.max ?? fp?.epsilon_max}
              motionCoherence={fp?.C}
              anisotropy={fp?.AI}
              strainEntropy={fp?.H}
              temporalStability={p1?.temporal_stability_index ?? fp?.TSI}
              calibration={result.calibration}
              physicalDisplacement={result.displacement?.physical_space}
            />

            {/* Deformation Over Time Line Chart */}
            <div style={{ marginTop: 24 }}>
              <h4 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "#0f172a" }}>
                Temporal Principal Strain Trajectories (E1 &amp; E2)
              </h4>
              <TemporalChart temporalData={result} />
            </div>

            {/* Sequence Deformation Fingerprint Radar */}
            {result.cardiac_deformation_fingerprint && (
              <div style={{ marginTop: 24 }}>
                <h4 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "#0f172a" }}>
                  Sequence Deformation Fingerprint
                </h4>
                <FingerprintChart
                  fingerprintData={result.cardiac_deformation_fingerprint}
                  fingerprint={fp}
                />
              </div>
            )}

            {/* Interpretation & Methodology Reference */}
            <div style={{ marginTop: 24 }}>
              <InterpretationPanel />
            </div>
            <div style={{ marginTop: 20 }}>
              <MethodologySection />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
