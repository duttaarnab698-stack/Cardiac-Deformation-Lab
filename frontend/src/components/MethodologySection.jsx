export default function MethodologySection() {
  return (
    <section id="section-methodology" className="methodology-card">
      <div className="methodology-header">
        <span className="methodology-badge">TECHNICAL REFERENCE</span>
        <h3>Methodology, Image Coordinate Framework &amp; Units</h3>
      </div>

      <div className="methodology-grid">
        <div className="methodology-item">
          <h4>📏 Units of Measurement &amp; Spatial Calibration</h4>
          <p>
            <strong>Displacement is measured in pixels by default.</strong> When spatial calibration is provided, displacement can be expressed in physical distance units (e.g., millimeters or centimeters).
            Calibration values must come from the imaging system or acquisition metadata. Incorrect calibration can produce incorrect physical measurements.
          </p>
        </div>

        <div className="methodology-item">
          <h4>📐 Continuum Strain Formulation</h4>
          <p>
            <strong>Strain is dimensionless and does not require spatial unit conversion.</strong> Components represent relative spatial gradient differentials derived under infinitesimal deformation continuum assumptions (&part;u/&part;x, &part;v/&part;y).
          </p>
        </div>

        <div className="methodology-item">
          <h4>🎯 Motion Estimation Principle</h4>
          <p>
            <strong>Optical Flow</strong> calculates <em>apparent pixel motion</em> based on spatial-temporal brightness constancy.
            Values represent projection in 2D image coordinates and depend directly on image contrast, SNR, acquisition frame rate, and speckle tracking stability.
          </p>
        </div>

        <div className="methodology-item">
          <h4>⏱️ Multi-Frame Temporal Dynamics</h4>
          <p>
            <strong>Temporal Stability Index (TSI)</strong> evaluates trajectory consistency across 3 or more sequential cine frames.
            Displacement-related physical metrics use spatial calibration if supplied, while temporal strain metrics remain strictly dimensionless.
          </p>
        </div>

        <div className="methodology-item">
          <h4>🔲 Region of Interest (ROI) &amp; Masking Scope</h4>
          <p>
            <strong>ROI analysis is optional and user-demarcated.</strong> Supported geometries (Rectangle, Ellipse, Polygon) define a binary mask \(M(x, y)\). Deformation metrics inside the mask isolate regional continuum strain and kinematics. An ROI is <em>not an automated or clinically validated anatomical segmentation</em> and implies no diagnostic claim. The user may select either <strong>Fixed ROI</strong> (static coordinates) or <strong>Tracked ROI</strong> (motion-translated coordinates).
          </p>
        </div>

        <div className="methodology-item">
          <h4>📍 Automatic ROI Tracking &amp; Limitations</h4>
          <p>
            <strong>Tracked ROI utilizes rigid 2D optical flow translation.</strong> In tracked mode, the user-defined ROI mask is translated frame-to-frame by median motion vectors \((dx, dy)\) with IQR outlier rejection. A tracking confidence score (\(0.0 - 1.0\)) measures vector coherence, outlier retention, and pixel coverage. <em>Crucial scientific limitation:</em> Tracking applies rigid 2D translation without non-rigid contour deformation or out-of-plane tracking compensation. It is an algorithmic estimation intended for exploratory research visualization, NOT anatomical segmentation or clinical diagnosis.
          </p>
        </div>

        <div className="methodology-item">
          <h4>🛡️ Automated Computational Quality Control (QC)</h4>
          <p>
            <strong>Technical validation and numerical integrity assessment.</strong> The Quality Control layer evaluates measurable technical properties of the input data and computed motion/deformation fields (image contrast/sharpness, optical flow stability, strain infinitesimal bounds, and tracking continuity). It does not determine whether cardiac function is normal or abnormal. Quality scores should not be interpreted as clinical measurements.
          </p>
        </div>
      </div>

      <div className="methodology-footer-notice">
        <span className="info-icon">ℹ️</span>
        <p>
          Calculations are performed strictly in 2D image plane space. Out-of-plane cardiac through-plane motion is not modeled in standard 2D view frames. Never invent or assume pixel spacing without vendor metadata.
        </p>
      </div>
    </section>
  );
}

