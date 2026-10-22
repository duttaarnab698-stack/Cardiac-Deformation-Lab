"""
backend/app/services/metrics.py

Advanced image-space deformation metrics for cardiac motion analysis.

All functions operate on NumPy arrays derived from dense optical flow
or strain tensors. These are experimental research descriptors and
are NOT clinically validated diagnostic measurements.
"""

import numpy as np


# ---------------------------------------------------------------------------
# 1. Motion Coherence
# ---------------------------------------------------------------------------

def calculate_motion_coherence(flow: np.ndarray) -> dict:
    """
    Measure how consistently neighbouring motion vectors point in similar
    directions across the image.

    Strategy
    --------
    1. Separate flow into (u, v) components.
    2. Compute the vector magnitude at every pixel.
    3. Produce unit-normalised direction vectors, guarding against
       division by zero where the magnitude is zero.
    4. Estimate local directional similarity by computing the
       magnitude of the spatial gradient of each normalised component.
       Regions where the direction changes slowly (high coherence) have
       a small gradient magnitude; regions with chaotic direction changes
       have a large gradient magnitude.
    5. Convert gradient magnitude to a coherence score in [0, 1]:
           coherence = 1 / (1 + gradient_magnitude)

    Parameters
    ----------
    flow : np.ndarray, shape (H, W, 2)
        Dense optical flow array.
        flow[..., 0] = horizontal displacement u
        flow[..., 1] = vertical displacement v

    Returns
    -------
    dict with keys:
        "map"  : np.ndarray (H, W) – per-pixel coherence in [0, 1]
        "mean" : float – mean coherence across the image
    """

    u = flow[..., 0].astype(np.float64)
    v = flow[..., 1].astype(np.float64)

    magnitude = np.sqrt(u ** 2 + v ** 2)

    # Safe normalisation: zero-magnitude vectors get direction (0, 0)
    epsilon = np.finfo(np.float64).tiny
    denom = np.maximum(magnitude, epsilon)

    u_norm = u / denom
    v_norm = v / denom

    # Gradient of each normalised component (both spatial axes)
    du_dy, du_dx = np.gradient(u_norm)
    dv_dy, dv_dx = np.gradient(v_norm)

    # Magnitude of direction-change across neighbours
    direction_gradient = np.sqrt(
        du_dx ** 2 + du_dy ** 2 +
        dv_dx ** 2 + dv_dy ** 2
    )

    # Map to [0, 1]: large gradient → low coherence
    coherence_map = 1.0 / (1.0 + direction_gradient)

    # Clip to handle any residual numerical noise
    coherence_map = np.clip(coherence_map, 0.0, 1.0)

    return {
        "map":  coherence_map,
        "mean": float(np.mean(coherence_map))
    }


# ---------------------------------------------------------------------------
# 2. Strain Gradient
# ---------------------------------------------------------------------------

def calculate_strain_gradient(
    principal_strain: np.ndarray
) -> dict:
    """
    Calculate the spatial gradient magnitude of the principal strain field.

    High values indicate regions where strain changes sharply in space,
    which may correspond to boundaries between contracting and non-
    contracting tissue segments in apparent-motion analysis.

    The gradient magnitude at each pixel is:

        G(x, y) = sqrt(dx² + dy²)

    where dx and dy are the partial spatial derivatives of the strain
    field computed via NumPy's central-difference gradient.

    Parameters
    ----------
    principal_strain : np.ndarray, shape (H, W)
        A 2-D principal strain field (e.g. principal_strain_1).

    Returns
    -------
    dict with keys:
        "map"  : np.ndarray (H, W) – gradient magnitude at every pixel
        "mean" : float – spatial mean of the gradient magnitude
        "max"  : float – spatial maximum of the gradient magnitude
    """

    dy, dx = np.gradient(principal_strain.astype(np.float64))

    gradient_magnitude = np.sqrt(dx ** 2 + dy ** 2)

    # Guard against NaN/Inf from pathological inputs
    gradient_magnitude = np.nan_to_num(
        gradient_magnitude,
        nan=0.0, posinf=0.0, neginf=0.0
    )

    return {
        "map":  gradient_magnitude,
        "mean": float(np.mean(gradient_magnitude)),
        "max":  float(np.max(gradient_magnitude))
    }


# ---------------------------------------------------------------------------
# 3. Strain Anisotropy
# ---------------------------------------------------------------------------

def calculate_strain_anisotropy(
    principal_strain_1: np.ndarray,
    principal_strain_2: np.ndarray
) -> dict:
    """
    Quantify how different the two principal strains are at each pixel.

    Isotropic deformation (equal stretching in all directions) gives a
    value near 0; strongly directional deformation gives a value near 1.

    The anisotropy index at each pixel is:

        A(x, y) = |e1 - e2| / (|e1| + |e2| + ε)

    where ε is a small constant that prevents division by zero when both
    principal strains are zero (rigid-body region or background).

    Parameters
    ----------
    principal_strain_1 : np.ndarray, shape (H, W)
        Maximum principal strain field.
    principal_strain_2 : np.ndarray, shape (H, W)
        Minimum principal strain field.

    Returns
    -------
    dict with keys:
        "map"  : np.ndarray (H, W) – anisotropy index in [0, 1)
        "mean" : float – mean anisotropy across the image
        "max"  : float – maximum anisotropy in the image
    """

    e1 = principal_strain_1.astype(np.float64)
    e2 = principal_strain_2.astype(np.float64)

    epsilon = 1e-12

    numerator   = np.abs(e1 - e2)
    denominator = np.abs(e1) + np.abs(e2) + epsilon

    anisotropy = numerator / denominator

    # Clip to valid range and sanitise
    anisotropy = np.clip(
        np.nan_to_num(anisotropy, nan=0.0, posinf=0.0, neginf=0.0),
        0.0, 1.0
    )

    return {
        "map":  anisotropy,
        "mean": float(np.mean(anisotropy)),
        "max":  float(np.max(anisotropy))
    }

calculate_anisotropy = calculate_strain_anisotropy


# ---------------------------------------------------------------------------
# 4. Strain Entropy
# ---------------------------------------------------------------------------

def calculate_strain_entropy(
    principal_strain: np.ndarray,
    num_bins: int = 256
) -> dict:
    """
    Estimate the Shannon entropy of the principal strain value distribution.

    Entropy quantifies the complexity of the strain field:
    - A uniform strain field has low entropy (all pixels are similar).
    - A highly heterogeneous strain field has higher entropy.

    Shannon entropy:

        H = -Σ p_i · log₂(p_i)   (summing over non-zero bins)

    Parameters
    ----------
    principal_strain : np.ndarray, shape (H, W)
        A 2-D principal strain field.
    num_bins : int, optional
        Number of histogram bins used to estimate the distribution.
        Default is 256.

    Returns
    -------
    dict with keys:
        "entropy"   : float – Shannon entropy in bits
        "histogram" : np.ndarray (num_bins,) – raw histogram counts
    """

    flat = principal_strain.astype(np.float64).ravel()

    # Exclude NaN/Inf before histogram
    flat = flat[np.isfinite(flat)]

    if flat.size == 0:
        return {
            "entropy":   0.0,
            "histogram": np.zeros(num_bins, dtype=np.int64)
        }

    histogram, _ = np.histogram(flat, bins=num_bins)

    # Convert counts to probabilities
    total = histogram.sum()
    probabilities = histogram / float(total) if total > 0 else histogram

    # Keep only non-zero probabilities (log2(0) is undefined)
    nonzero = probabilities[probabilities > 0]

    entropy = float(-np.sum(nonzero * np.log2(nonzero)))

    return {
        "entropy":   entropy,
        "histogram": histogram
    }


# ---------------------------------------------------------------------------
# 5. Deformation Energy
# ---------------------------------------------------------------------------

def calculate_deformation_energy(
    exx: np.ndarray,
    eyy: np.ndarray,
    exy: np.ndarray
) -> dict:
    """
    Compute a deformation-energy proxy from the strain tensor components.

    This is a strain-energy density approximation that weights the shear
    component by 2 (consistent with the symmetry of the off-diagonal term):

        W(x, y) = 0.5 · (exx² + eyy² + 2 · exy²)

    This is NOT a physically calibrated elastic strain-energy density
    (which requires material stiffness constants). It is an image-space
    proxy that highlights regions of large apparent deformation.

    Parameters
    ----------
    exx : np.ndarray, shape (H, W)
        Normal strain in the x direction.
    eyy : np.ndarray, shape (H, W)
        Normal strain in the y direction.
    exy : np.ndarray, shape (H, W)
        Shear strain component.

    Returns
    -------
    dict with keys:
        "map"  : np.ndarray (H, W) – energy density at every pixel
        "mean" : float – mean energy density
        "max"  : float – peak energy density
    """

    exx = exx.astype(np.float64)
    eyy = eyy.astype(np.float64)
    exy = exy.astype(np.float64)

    energy_density = 0.5 * (exx ** 2 + eyy ** 2 + 2.0 * exy ** 2)

    # Sanitise (should not be needed for well-formed flow, but be safe)
    energy_density = np.nan_to_num(
        energy_density,
        nan=0.0, posinf=0.0, neginf=0.0
    )

    return {
        "map":  energy_density,
        "mean": float(np.mean(energy_density)),
        "max":  float(np.max(energy_density))
    }


# ---------------------------------------------------------------------------
# 6. Generic Metric Heatmap Helper
# ---------------------------------------------------------------------------

import cv2
from pathlib import Path


def create_metric_heatmap(
    metric_map: np.ndarray,
    output_path: str
) -> str:
    """
    Convert any 2-D metric map into a JET-colormap heatmap and save it.

    Safe against NaN/Inf values: they are replaced with zero before
    normalisation so the colormap range is always finite.

    Steps
    -----
    1. Replace NaN/Inf with 0.
    2. Normalise to [0, 255] using cv2.normalize (NORM_MINMAX).
    3. Cast to uint8.
    4. Apply cv2.COLORMAP_JET.
    5. Create the output directory if it does not exist.
    6. Write the image with cv2.imwrite.

    Parameters
    ----------
    metric_map  : np.ndarray, shape (H, W)
        The 2-D metric array to visualise (any dtype).
    output_path : str
        Destination file path (including filename and extension).

    Returns
    -------
    str : the saved output path.

    Raises
    ------
    ValueError if cv2.imwrite fails.
    """

    # Sanitise: replace any NaN/Inf with 0
    safe_map = np.nan_to_num(
        metric_map.astype(np.float64),
        nan=0.0, posinf=0.0, neginf=0.0
    )

    # Normalise to 0-255
    normalized = cv2.normalize(
        safe_map,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    ).astype(np.uint8)

    # Apply colormap
    heatmap = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

    # Ensure output directory exists
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Save
    success = cv2.imwrite(str(out), heatmap)
    if not success:
        raise ValueError(
            f"Failed to save metric heatmap to {out}"
        )

    return str(out)

# ---------------------------------------------------------------------------
# 7. Radial & Circumferential Deformation
# ---------------------------------------------------------------------------

def calculate_radial_circumferential_deformation(
    flow: np.ndarray,
    center_x: float = None,
    center_y: float = None
) -> dict:
    """
    Decompose the optical-flow displacement field into radial and
    circumferential (tangential) components relative to a reference centre.

    This is an image-space geometric approximation intended for research
    purposes. It is NOT a clinically validated measure of myocardial
    radial or circumferential strain.

    Coordinate convention
    ---------------------
    For every pixel (x, y) the displacement vector (u, v) is projected
    onto two orthogonal unit vectors:

    Radial unit vector   er = (dx, dy) / (r + ε)
    Tangential unit vector et = (-dy/r, dx/r)  ← 90° counter-clockwise from er

    where  dx = x − cx,  dy = y − cy,  r = √(dx² + dy²)

    Projections:
        radial_displacement          = u·er_x + v·er_y
        circumferential_displacement = u·et_x + v·et_y

    Positive radial   → displacement away from centre (expansion).
    Negative radial   → displacement toward centre (contraction).
    Sign of circum.   → encodes rotation direction.

    Parameters
    ----------
    flow : np.ndarray, shape (H, W, 2)
        Dense optical flow. flow[..., 0] = u, flow[..., 1] = v.
    center_x : float, optional
        Horizontal (column) coordinate of the reference centre.
        Defaults to width / 2.
    center_y : float, optional
        Vertical (row) coordinate of the reference centre.
        Defaults to height / 2.

    Returns
    -------
    dict with keys:
        "radial_map"              : np.ndarray (H, W) – signed radial displacement
        "circumferential_map"     : np.ndarray (H, W) – signed circumferential displacement
        "radial_mean"             : float
        "radial_max"              : float
        "radial_min"              : float
        "circumferential_mean"    : float
        "circumferential_max"     : float
        "circumferential_min"     : float
    """

    u = flow[..., 0].astype(np.float64)
    v = flow[..., 1].astype(np.float64)

    height, width = u.shape

    # Default centre: image centroid
    if center_x is None:
        center_x = width / 2.0
    if center_y is None:
        center_y = height / 2.0

    # Build pixel-coordinate grids
    xs = np.arange(width,  dtype=np.float64)   # shape (W,)
    ys = np.arange(height, dtype=np.float64)   # shape (H,)
    xx, yy = np.meshgrid(xs, ys)               # both shape (H, W)

    dx = xx - center_x   # relative x
    dy = yy - center_y   # relative y

    r = np.sqrt(dx ** 2 + dy ** 2)

    # Prevent division by zero at the exact centre pixel
    epsilon = np.finfo(np.float64).tiny
    r_safe = r + epsilon

    # Radial unit vector
    er_x = dx / r_safe
    er_y = dy / r_safe

    # Tangential unit vector (90° counter-clockwise from radial)
    et_x = -er_y
    et_y =  er_x

    # Project displacement
    radial_displacement          = u * er_x + v * er_y
    circumferential_displacement = u * et_x + v * et_y

    return {
        "radial_map":           radial_displacement,
        "circumferential_map":  circumferential_displacement,
        "radial_mean":          float(np.mean(radial_displacement)),
        "radial_max":           float(np.max(radial_displacement)),
        "radial_min":           float(np.min(radial_displacement)),
        "circumferential_mean": float(np.mean(circumferential_displacement)),
        "circumferential_max":  float(np.max(circumferential_displacement)),
        "circumferential_min":  float(np.min(circumferential_displacement))
    }


# ---------------------------------------------------------------------------
# 8. Signed Metric Heatmap (preserves direction)
# ---------------------------------------------------------------------------

def create_signed_metric_heatmap(
    metric_map: np.ndarray,
    output_path: str
) -> str:
    """
    Save a signed 2-D metric field as a JET-colormap heatmap, preserving
    the sign of the values in the colour encoding.

    Unlike ``create_metric_heatmap``, this function does NOT take the
    absolute value before normalisation. The full signed range
    [min, max] is linearly mapped to [0, 255] so that:

    - The most negative value → deep blue (JET low end)
    - Zero (mid-range)        → green
    - The most positive value → deep red (JET high end)

    This is important for radial and circumferential deformation maps
    where the sign conveys expansion vs. contraction / rotation direction.

    Parameters
    ----------
    metric_map  : np.ndarray, shape (H, W)
        Signed 2-D metric array (any float dtype).
    output_path : str
        Destination file path.

    Returns
    -------
    str : the saved output path.

    Raises
    ------
    ValueError if cv2.imwrite fails.
    """

    # Replace NaN / Inf before any arithmetic
    safe_map = np.nan_to_num(
        metric_map.astype(np.float64),
        nan=0.0, posinf=0.0, neginf=0.0
    )

    # Normalise the full signed range → [0, 255]
    # cv2.NORM_MINMAX maps [min, max] → [alpha, beta]
    normalized = cv2.normalize(
        safe_map,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    ).astype(np.uint8)

    # Apply JET: blue = low (contraction/negative), red = high (expansion/positive)
    heatmap = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

    # Ensure output directory exists
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    success = cv2.imwrite(str(out), heatmap)
    if not success:
        raise ValueError(
            f"Failed to save signed metric heatmap to {out}"
        )

    return str(out)

# ---------------------------------------------------------------------------
# 9. Temporal Stability Analysis
# ---------------------------------------------------------------------------

def calculate_temporal_stability(
    metric_sequence
) -> dict:
    """
    Measure the temporal consistency of a scalar metric across multiple
    cardiac frames.

    Given a sequence of the same metric measured at consecutive time points
    (e.g. mean principal strain per frame), this function quantifies how
    stable that metric is over time.

    Definitions
    -----------
    mean_value  = mean(sequence)
    std_value   = standard deviation(sequence)

    coefficient_of_variation (CV) = std / (|mean| + ε)
        Normalised measure of dispersion; ε prevents division by zero.

    temporal_stability_index (TSI) = 1 / (1 + CV)
        Maps CV ∈ [0, ∞) → TSI ∈ (0, 1].
        TSI → 1  : highly stable (little frame-to-frame variation).
        TSI → 0  : highly variable.

    These are mathematical descriptors of signal consistency and are NOT
    clinically validated cardiac stability measures.

    Parameters
    ----------
    metric_sequence : list or np.ndarray
        1-D collection of scalar metric values, one per frame / frame pair.

    Returns
    -------
    dict with keys:
        "mean"                     : float
        "std"                      : float
        "coefficient_of_variation" : float
        "temporal_stability_index" : float

    Returns zeros for empty, all-NaN, or degenerate inputs.
    """

    seq = np.asarray(metric_sequence, dtype=np.float64).ravel()

    # Remove NaN / Inf
    seq = seq[np.isfinite(seq)]

    if seq.size == 0:
        return {
            "mean":                     0.0,
            "std":                      0.0,
            "coefficient_of_variation": 0.0,
            "temporal_stability_index": 1.0   # trivially stable (no data)
        }

    mean_value = float(np.mean(seq))
    std_value  = float(np.std(seq, ddof=0))

    epsilon = 1e-12
    cv  = std_value / (abs(mean_value) + epsilon)
    tsi = 1.0 / (1.0 + cv)

    return {
        "mean":                     mean_value,
        "std":                      std_value,
        "coefficient_of_variation": float(cv),
        "temporal_stability_index": float(tsi)
    }


def calculate_temporal_metric_summary(
    metric_sequence
) -> dict:
    """
    Produce a concise statistical summary of a scalar metric sequence,
    including a temporal stability index.

    Combines basic descriptive statistics (mean, std, min, max) with
    the temporal stability index from ``calculate_temporal_stability``.

    Parameters
    ----------
    metric_sequence : list or np.ndarray
        1-D collection of scalar values, one per frame / frame pair.

    Returns
    -------
    dict with keys:
        "mean"                   : float
        "std"                    : float
        "min"                    : float
        "max"                    : float
        "temporal_stability_index" : float
    """

    seq = np.asarray(metric_sequence, dtype=np.float64).ravel()
    seq = seq[np.isfinite(seq)]

    if seq.size == 0:
        return {
            "mean":                    0.0,
            "std":                     0.0,
            "min":                     0.0,
            "max":                     0.0,
            "temporal_stability_index": 1.0
        }

    stability = calculate_temporal_stability(seq)

    return {
        "mean":                    float(np.mean(seq)),
        "std":                     float(np.std(seq, ddof=0)),
        "min":                     float(np.min(seq)),
        "max":                     float(np.max(seq)),
        "temporal_stability_index": stability["temporal_stability_index"]
    }
