import { useState } from "react";
import { getOutputUrl } from "../services/api";
import ImageViewerModal from "./ImageViewerModal";

function VisualizationCard({ title, path, description, onExpand }) {
  const url = getOutputUrl(path);
  const [loading, setLoading] = useState(Boolean(url));
  const [hasError, setHasError] = useState(!url);

  return (
    <div className="vis-card">
      <div className="vis-card-header">
        <div className="vis-card-titles">
          <h4 className="vis-title">{title}</h4>
          <p className="vis-desc">{description}</p>
        </div>
        {url && !hasError && (
          <button
            className="vis-expand-btn"
            onClick={() => onExpand({ title, url, description })}
            title="Expand to Fullscreen View"
            aria-label={`Expand ${title}`}
          >
            ⛶
          </button>
        )}
      </div>

      <div
        className="vis-image-wrapper"
        onClick={() => {
          if (url && !hasError) {
            onExpand({ title, url, description });
          }
        }}
      >
        {loading && (
          <div className="vis-placeholder loading">
            <span className="spinner"></span>
            <span>Loading image...</span>
          </div>
        )}

        {hasError ? (
          <div className="vis-placeholder error">
            <span className="vis-placeholder-icon">⚠️</span>
            <span>Visualization unavailable</span>
          </div>
        ) : (
          <img
            src={url}
            alt={title}
            className={`vis-image ${loading ? "hidden" : "visible"}`}
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setHasError(true);
            }}
          />
        )}

        {!hasError && !loading && (
          <div className="vis-hover-hint">
            <span>🔍 Click to expand</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnalysisMaps({ result, analysisData }) {
  const activeData = result || analysisData;
  const [modalState, setModalState] = useState({
    isOpen: false,
    imageSrc: null,
    title: "",
    description: "",
  });

  if (!activeData) return null;

  const outputs = activeData.outputs || {};
  const advOutputs = activeData.advanced_outputs || {};
  const cardiacOutputs = activeData.cardiac_deformation_outputs || {};

  const handleExpand = ({ title, url, description }) => {
    setModalState({
      isOpen: true,
      imageSrc: url,
      title,
      description,
    });
  };

  const handleCloseModal = () => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  };

  return (
    <div className="analysis-visualizations-container">
      {/* SECTION ROI — Region of Interest Overlay (if present) */}
      {outputs.roi_overlay && (
        <section id="section-roi" className="vis-section">
          <div className="vis-section-header">
            <div className="vis-section-badge">ROI Geometry</div>
            <h3 className="vis-section-title">Region of Interest Overlay</h3>
            <p className="vis-section-subtitle">
              User-defined region ({activeData.analysis_scope?.roi_type || "Geometric"} ROI) with boundary contours (yellow) and active mask overlay ({activeData.analysis_scope?.pixel_count?.toLocaleString() || "active"} pixels).
            </p>
          </div>
          <div className="vis-grid">
            <VisualizationCard
              title={`ROI Boundary Overlay (${activeData.analysis_scope?.roi_type || "Custom"})`}
              path={outputs.roi_overlay}
              description="Active ROI boundary contour (yellow) and tinted mask overlay on reference frame."
              onExpand={handleExpand}
            />
          </div>
        </section>
      )}

      {/* SECTION A — Motion Analysis */}
      <section id="section-motion" className="vis-section">
        <div className="vis-section-header">
          <div className="vis-section-badge">Section A</div>
          <h3 className="vis-section-title">Motion Analysis</h3>
          <p className="vis-section-subtitle">
            Dense Farnebäck optical flow vector fields and spatial displacement magnitude maps.
          </p>
        </div>
        <div className="vis-grid">
          <VisualizationCard
            title={activeData.calibration?.enabled ? `Displacement Heatmap (${activeData.calibration?.unit || "mm"})` : "Displacement Heatmap (Pixels)"}
            path={outputs.displacement_heatmap || activeData.heatmap}
            description={
              activeData.calibration?.enabled
                ? `Physical displacement map normalized across the spatial domain (calibrated in ${activeData.calibration?.unit || "mm"}).`
                : "Spatial distribution of apparent displacement magnitude across the cardiac frame pair (pixel units)."
            }
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Motion Vector Map"
            path={outputs.motion_vector_map || activeData.motion_vector_map}
            description="Dense 2D displacement vectors superimposed over the reference image frame."
            onExpand={handleExpand}
          />
        </div>
      </section>

      {/* SECTION B — Strain Analysis */}
      <section id="section-strain" className="vis-section">
        <div className="vis-section-header">
          <div className="vis-section-badge">Section B</div>
          <h3 className="vis-section-title">Strain Analysis</h3>
          <p className="vis-section-subtitle">
            Small-deformation continuum strain tensor fields and maximum principal deformation components.
          </p>
        </div>
        <div className="vis-grid">
          <VisualizationCard
            title="Exx Normal Strain"
            path={outputs.exx_heatmap}
            description="Horizontal normal strain (du/dx) representing apparent lateral shortening or elongation."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Eyy Normal Strain"
            path={outputs.eyy_heatmap}
            description="Vertical normal strain (dv/dy) representing apparent longitudinal deformation."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Exy Shear Strain"
            path={outputs.exy_heatmap}
            description="Shear strain (0.5*(du/dy + dv/dx)) representing apparent in-plane angular distortion."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Principal Strain (Major)"
            path={outputs.principal_strain_heatmap}
            description="Maximum eigenvalue field of the strain tensor highlighting dominant deformation magnitude."
            onExpand={handleExpand}
          />
        </div>
      </section>

      {/* SECTION C — Directional Deformation */}
      <section id="section-directional" className="vis-section">
        <div className="vis-section-header">
          <div className="vis-section-badge">Section C</div>
          <h3 className="vis-section-title">Directional Deformation</h3>
          <p className="vis-section-subtitle">
            Principal strain orientation axes and geometric projections along ventricular coordinate vectors.
          </p>
        </div>
        <div className="vis-grid">
          <VisualizationCard
            title="Principal Direction Map"
            path={outputs.principal_direction_map}
            description="Estimated eigenvectors depicting the primary orientation axis of principal strain."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Radial Deformation"
            path={cardiacOutputs.radial_map}
            description="Motion projection along radial axes extending outwards from the ventricular centroid."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Circumferential Deformation"
            path={cardiacOutputs.circumferential_map}
            description="Motion projection along circumferential tangential axes orthogonal to radial vectors."
            onExpand={handleExpand}
          />
        </div>
      </section>

      {/* SECTION D — Advanced Metrics */}
      <section id="section-advanced" className="vis-section">
        <div className="vis-section-header">
          <div className="vis-section-badge">Section D</div>
          <h3 className="vis-section-title">Advanced Metrics</h3>
          <p className="vis-section-subtitle">
            Second-order mathematical consistency descriptors, tissue anisotropy, and strain energy densities.
          </p>
        </div>
        <div className="vis-grid">
          <VisualizationCard
            title="Motion Coherence"
            path={advOutputs.motion_coherence_map}
            description="Local vector consistency measuring alignment between neighboring displacement vectors."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Strain Gradient"
            path={advOutputs.strain_gradient_map}
            description="Spatial rate of change of principal strain fields across regional tissue boundaries."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Strain Anisotropy"
            path={advOutputs.anisotropy_map}
            description="Directional preference index (|e1 - e2| / (|e1| + |e2|)) of local deformation."
            onExpand={handleExpand}
          />
          <VisualizationCard
            title="Deformation Energy"
            path={advOutputs.deformation_energy_map}
            description="Surrogate strain energy density highlighting regions of concentrated mechanical work."
            onExpand={handleExpand}
          />
        </div>
      </section>

      {/* Reusable Image Viewer Modal */}
      <ImageViewerModal
        isOpen={modalState.isOpen}
        imageSrc={modalState.imageSrc}
        title={modalState.title}
        description={modalState.description}
        onClose={handleCloseModal}
      />
    </div>
  );
}
