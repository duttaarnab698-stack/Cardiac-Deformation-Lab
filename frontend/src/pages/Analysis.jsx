import { useState } from "react";
import { Link } from "react-router-dom";
import AnalysisPanel from "../components/AnalysisPanel";
import TemporalAnalysis from "../components/TemporalAnalysis";
import "./Analysis.css";

export default function Analysis() {
  // Input Modes: "single" (Single Image Pair) | "sequence" (Image Sequence) | "video" (Video)
  const [inputMode, setInputMode] = useState("single");

  return (
    <div className="cdl-analysis-page">
      {/* 1. PAGE HEADER & BREADCRUMB */}
      <section className="cdl-analysis-header-wrap" aria-label="Page Header">
        <div>
          <div className="cdl-analysis-breadcrumb">
            <Link to="/" className="bc-home">
              <span>🔬</span>
              <span>Workspace</span>
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Analysis</span>
          </div>

          <h1 className="cdl-analysis-title">Cardiac Deformation Analysis</h1>
          <p className="cdl-analysis-subtitle">
            Configure image-based motion estimation, displacement mapping, and Green-Lagrangian strain tensors.
          </p>
        </div>
      </section>

      {/* 2. VISUAL WORKFLOW INDICATOR */}
      <section className="cdl-workflow-indicator-bar" aria-label="Analysis Pipeline Workflow">
        <div className="cdl-workflow-step completed">
          <div className="cdl-workflow-badge">01</div>
          <span className="cdl-workflow-label">INPUT</span>
        </div>
        <span className="cdl-workflow-arrow">➔</span>

        <div className="cdl-workflow-step active">
          <div className="cdl-workflow-badge">02</div>
          <span className="cdl-workflow-label">CONFIGURE</span>
        </div>
        <span className="cdl-workflow-arrow">➔</span>

        <div className="cdl-workflow-step">
          <div className="cdl-workflow-badge">03</div>
          <span className="cdl-workflow-label">ROI MASK</span>
        </div>
        <span className="cdl-workflow-arrow">➔</span>

        <div className="cdl-workflow-step">
          <div className="cdl-workflow-badge">04</div>
          <span className="cdl-workflow-label">ANALYZE</span>
        </div>
        <span className="cdl-workflow-arrow">➔</span>

        <div className="cdl-workflow-step">
          <div className="cdl-workflow-badge">05</div>
          <span className="cdl-workflow-label">RESULTS</span>
        </div>
      </section>

      {/* 3. INPUT MODE SELECTOR BAR */}
      <section className="cdl-mode-bar" aria-label="Analysis Modality">
        <span className="cdl-mode-label">Analysis Modality:</span>
        <div className="cdl-mode-pills">
          <button
            type="button"
            className={`cdl-mode-btn ${inputMode === "single" ? "active" : ""}`}
            onClick={() => setInputMode("single")}
          >
            <span>🔬</span>
            <span>Single Pair Differential</span>
          </button>
          <button
            type="button"
            className={`cdl-mode-btn ${inputMode === "sequence" ? "active" : ""}`}
            onClick={() => setInputMode("sequence")}
          >
            <span>🖼️</span>
            <span>Temporal Image Sequence</span>
          </button>
          <button
            type="button"
            className={`cdl-mode-btn ${inputMode === "video" ? "active" : ""}`}
            onClick={() => setInputMode("video")}
          >
            <span>🎬</span>
            <span>Cine Video Recording</span>
          </button>
        </div>
      </section>

      {/* 4. RENDER WORKSPACE ACCORDING TO SELECTED MODALITY */}
      {inputMode === "single" && <AnalysisPanel />}
      {inputMode === "sequence" && <TemporalAnalysis initialMode="sequence" />}
      {inputMode === "video" && <TemporalAnalysis initialMode="video" />}
    </div>
  );
}
