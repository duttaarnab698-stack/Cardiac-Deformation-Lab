import { Link } from "react-router-dom";
import TemporalAnalysis from "../components/TemporalAnalysis";
import "./TemporalAnalysis.css";

export default function TemporalAnalysisPage() {
  return (
    <div className="cdl-temporal-page">
      {/* 1. PAGE HEADER & BREADCRUMB */}
      <section className="cdl-temporal-header-wrap" aria-label="Page Header">
        <div>
          <div className="cdl-temporal-breadcrumb">
            <Link to="/" className="bc-home">
              <span>🔬</span>
              <span>Workspace</span>
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Temporal Analysis</span>
          </div>

          <h1 className="cdl-temporal-title">Temporal Deformation Analysis</h1>
          <p className="cdl-temporal-subtitle">
            Track cardiac motion, spatial displacement trajectories, and Green-Lagrangian strain tensors across consecutive frames and cycles.
          </p>
        </div>
      </section>

      {/* 2. VISUAL WORKFLOW INDICATOR */}
      <section className="cdl-temporal-workflow-bar" aria-label="Temporal Pipeline Workflow">
        <div className="cdl-temporal-step completed">
          <div className="cdl-temporal-step-badge">01</div>
          <span className="cdl-temporal-step-label">SELECT SEQUENCE</span>
        </div>
        <span className="cdl-temporal-arrow">➔</span>

        <div className="cdl-temporal-step active">
          <div className="cdl-temporal-step-badge">02</div>
          <span className="cdl-temporal-step-label">REVIEW FRAMES</span>
        </div>
        <span className="cdl-temporal-arrow">➔</span>

        <div className="cdl-temporal-step">
          <div className="cdl-temporal-step-badge">03</div>
          <span className="cdl-temporal-step-label">ANALYZE MOTION</span>
        </div>
        <span className="cdl-temporal-arrow">➔</span>

        <div className="cdl-temporal-step">
          <div className="cdl-temporal-step-badge">04</div>
          <span className="cdl-temporal-step-label">ANALYZE STRAIN</span>
        </div>
        <span className="cdl-temporal-arrow">➔</span>

        <div className="cdl-temporal-step">
          <div className="cdl-temporal-step-badge">05</div>
          <span className="cdl-temporal-step-label">REVIEW RESULTS</span>
        </div>
      </section>

      {/* 3. TEMPORAL WORKSTATION COMPONENT */}
      <TemporalAnalysis />
    </div>
  );
}
