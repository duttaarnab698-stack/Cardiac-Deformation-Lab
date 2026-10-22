export default function InterpretationPanel() {
  return (
    <section id="section-interpretation" className="interpretation-card">
      <div className="interpretation-header">
        <span className="interpretation-badge">MATHEMATICAL FRAMEWORK</span>
        <h3>Analysis Interpretation Guide</h3>
      </div>

      <div className="interpretation-body">
        <p className="interpretation-lead">
          The values computed by the Cardiac Deformation Lab represent physical and geometrical properties
          of apparent 2D motion fields:
        </p>

        <ul className="interpretation-list">
          <li>
            <strong>Displacement Amplitude:</strong> Higher Euclidean displacement values indicate greater apparent image motion between the analyzed frames.
          </li>
          <li>
            <strong>Principal Strain:</strong> The maximum principal strain field (&epsilon;1) describes the dominant local spatial deformation component (orientation and magnitude of greatest expansion or compression).
          </li>
          <li>
            <strong>Motion Coherence:</strong> Summarizes the directional consistency of neighboring motion vectors within local 5x5 kernels; values close to 1.0 indicate smooth, uniform tissue translation or contraction.
          </li>
          <li>
            <strong>Strain Anisotropy:</strong> Measures the degree of directional preference (|&epsilon;1 - &epsilon;2| / (|&epsilon;1| + |&epsilon;2|)); higher values reflect pronounced directional stretching along a dominant axis.
          </li>
          <li>
            <strong>Temporal Stability Index (TSI):</strong> Quantifies frame-to-frame trajectory smoothness across the cardiac cycle, penalizing excessive temporal jitter or tracking artifacts.
          </li>
        </ul>

        <div className="interpretation-disclaimer-box">
          <span className="disclaimer-title">RESEARCH &amp; EDUCATIONAL USE ONLY:</span>
          <p>
            This interpretation describes image-space mathematical measurements and is intended for research/educational analysis.
            It is <strong>NOT</strong> a clinical diagnosis, medical risk classification, or assertion of cardiac pathology.
          </p>
        </div>
      </div>
    </section>
  );
}

