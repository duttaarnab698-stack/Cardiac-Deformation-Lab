"""
backend/app/services/fingerprint.py

Cardiac Deformation Fingerprint Service.

Combines displacement, strain, advanced deformation metrics, and optional
temporal stability measurements into a structured 10-dimensional fingerprint.

Conceptual fingerprint vector:
    F = [
        D_mean,             # 1. mean displacement
        D_max,              # 2. maximum displacement
        epsilon_mean,       # 3. representative mean strain
        epsilon_max,        # 4. representative maximum strain
        epsilon_principal,  # 5. representative principal strain
        AI,                 # 6. anisotropy index
        H,                  # 7. strain entropy
        G_epsilon,          # 8. strain gradient
        C,                  # 9. motion coherence
        TSI                 # 10. temporal stability index
    ]

IMPORTANT:
This deformation fingerprint is purely a mathematical and geometrical representation
of computed image-space deformation measurements. It is intended solely for research
and visualization in this prototype, and is NOT a clinical risk score, diagnostic tool,
or medical classifier.
"""

from typing import Any, Dict, List, Optional
import numpy as np


def _safe_float(val: Any) -> Optional[float]:
    """
    Safely convert a value to a Python float.
    Returns None if val is None, NaN, Inf, or unconvertible.
    """
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def create_cardiac_deformation_fingerprint(
    displacement_statistics: Dict[str, Any],
    strain_statistics: Dict[str, Any],
    advanced_metrics: Dict[str, Any],
    temporal_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Combine major calculated deformation measurements into one structured fingerprint.

    Extracts existing values without recomputing:
    - Displacement statistics: mean and max displacement
    - Strain statistics: mean strain, max strain, mean principal strain
    - Advanced metrics: anisotropy, entropy, gradient, motion coherence
    - Temporal metrics (optional): temporal stability index

    Parameters
    ----------
    displacement_statistics : dict
        Output from calculate_motion_statistics().
    strain_statistics : dict
        Output from calculate_strain_statistics().
    advanced_metrics : dict
        Output containing coherence, gradient, anisotropy, entropy, energy results.
    temporal_metrics : dict, optional
        Output from temporal strain analysis (e.g. analyze_temporal_strain()).
        If None or not provided, temporal_stability_index is set to None.

    Returns
    -------
    dict with keys:
        "fingerprint": dict with 10 scalar dimension names
        "vector": list of exactly 10 float values (or None if unavailable)
        "normalized_vector": list of 10 values min-max normalized to [0, 1] for visualization
        "summary": dict with dimensions (10), available count, missing count
    """
    # 1. Mean Displacement
    d_mean = _safe_float(
        displacement_statistics.get("mean_displacement")
        if "mean_displacement" in displacement_statistics
        else displacement_statistics.get("mean")
    )

    # 2. Max Displacement
    d_max = _safe_float(
        displacement_statistics.get("max_displacement")
        if "max_displacement" in displacement_statistics
        else displacement_statistics.get("max")
    )

    # 3. Representative Mean Strain (epsilon_mean)
    if "mean_strain" in strain_statistics:
        mean_strain = _safe_float(strain_statistics.get("mean_strain"))
    elif "mean_exx" in strain_statistics and "mean_eyy" in strain_statistics:
        m_exx = _safe_float(strain_statistics.get("mean_exx"))
        m_eyy = _safe_float(strain_statistics.get("mean_eyy"))
        if m_exx is not None and m_eyy is not None:
            mean_strain = float((m_exx + m_eyy) / 2.0)
        else:
            mean_strain = m_exx if m_exx is not None else m_eyy
    elif "mean_exx" in strain_statistics:
        mean_strain = _safe_float(strain_statistics.get("mean_exx"))
    elif "mean" in strain_statistics:
        mean_strain = _safe_float(strain_statistics.get("mean"))
    else:
        mean_strain = None

    # 4. Representative Maximum Strain (epsilon_max)
    if "max_strain" in strain_statistics:
        max_strain = _safe_float(strain_statistics.get("max_strain"))
    elif "max_exx" in strain_statistics and "max_eyy" in strain_statistics:
        mx_exx = _safe_float(strain_statistics.get("max_exx"))
        mx_eyy = _safe_float(strain_statistics.get("max_eyy"))
        if mx_exx is not None and mx_eyy is not None:
            max_strain = float(max(mx_exx, mx_eyy))
        else:
            max_strain = mx_exx if mx_exx is not None else mx_eyy
    elif "max_exx" in strain_statistics:
        max_strain = _safe_float(strain_statistics.get("max_exx"))
    elif "max" in strain_statistics:
        max_strain = _safe_float(strain_statistics.get("max"))
    else:
        max_strain = None

    # 5. Representative Principal Strain (epsilon_principal)
    if "mean_principal_strain" in strain_statistics:
        mean_principal_strain = _safe_float(strain_statistics.get("mean_principal_strain"))
    elif "mean_principal_strain_1" in strain_statistics:
        mean_principal_strain = _safe_float(strain_statistics.get("mean_principal_strain_1"))
    elif "principal_strain_1" in strain_statistics:
        p1 = strain_statistics.get("principal_strain_1")
        if isinstance(p1, dict):
            mean_principal_strain = _safe_float(p1.get("mean"))
        else:
            mean_principal_strain = _safe_float(p1)
    else:
        mean_principal_strain = None

    # 6. Anisotropy Index (AI)
    aniso_val = None
    if "anisotropy_index" in advanced_metrics:
        aniso_val = advanced_metrics.get("anisotropy_index")
    elif "anisotropy" in advanced_metrics:
        aniso = advanced_metrics.get("anisotropy")
        if isinstance(aniso, dict):
            aniso_val = aniso.get("mean") if "mean" in aniso else aniso.get("max")
        else:
            aniso_val = aniso
    elif "anisotropy_result" in advanced_metrics:
        aniso = advanced_metrics.get("anisotropy_result")
        if isinstance(aniso, dict):
            aniso_val = aniso.get("mean")
        else:
            aniso_val = aniso
    anisotropy_index = _safe_float(aniso_val)

    # 7. Strain Entropy (H)
    entropy_val = None
    if "strain_entropy" in advanced_metrics:
        ent = advanced_metrics.get("strain_entropy")
        if isinstance(ent, dict):
            entropy_val = ent.get("entropy")
        else:
            entropy_val = ent
    elif "entropy" in advanced_metrics:
        ent = advanced_metrics.get("entropy")
        if isinstance(ent, dict):
            entropy_val = ent.get("entropy")
        else:
            entropy_val = ent
    elif "entropy_result" in advanced_metrics:
        ent = advanced_metrics.get("entropy_result")
        if isinstance(ent, dict):
            entropy_val = ent.get("entropy")
        else:
            entropy_val = ent
    strain_entropy = _safe_float(entropy_val)

    # 8. Strain Gradient (G_epsilon)
    grad_val = None
    if "strain_gradient" in advanced_metrics:
        grd = advanced_metrics.get("strain_gradient")
        if isinstance(grd, dict):
            grad_val = grd.get("mean") if "mean" in grd else grd.get("max")
        else:
            grad_val = grd
    elif "gradient" in advanced_metrics:
        grd = advanced_metrics.get("gradient")
        if isinstance(grd, dict):
            grad_val = grd.get("mean")
        else:
            grad_val = grd
    elif "gradient_result" in advanced_metrics:
        grd = advanced_metrics.get("gradient_result")
        if isinstance(grd, dict):
            grad_val = grd.get("mean")
        else:
            grad_val = grd
    strain_gradient = _safe_float(grad_val)

    # 9. Motion Coherence (C)
    coh_val = None
    if "motion_coherence" in advanced_metrics:
        coh = advanced_metrics.get("motion_coherence")
        if isinstance(coh, dict):
            coh_val = coh.get("mean")
        else:
            coh_val = coh
    elif "coherence" in advanced_metrics:
        coh = advanced_metrics.get("coherence")
        if isinstance(coh, dict):
            coh_val = coh.get("mean")
        else:
            coh_val = coh
    elif "coherence_result" in advanced_metrics:
        coh = advanced_metrics.get("coherence_result")
        if isinstance(coh, dict):
            coh_val = coh.get("mean")
        else:
            coh_val = coh
    motion_coherence = _safe_float(coh_val)

    # 10. Temporal Stability Index (TSI)
    tsi_val = None
    if temporal_metrics is not None and isinstance(temporal_metrics, dict):
        if "temporal_stability_index" in temporal_metrics:
            tsi_val = temporal_metrics.get("temporal_stability_index")
        elif "summary" in temporal_metrics and isinstance(temporal_metrics["summary"], dict):
            tsi_val = temporal_metrics["summary"].get("temporal_stability_index")
        elif "principal_strain_1" in temporal_metrics and isinstance(temporal_metrics["principal_strain_1"], dict):
            p1 = temporal_metrics["principal_strain_1"]
            if "summary" in p1 and isinstance(p1["summary"], dict):
                tsi_val = p1["summary"].get("temporal_stability_index")
            else:
                tsi_val = p1.get("temporal_stability_index")
        elif "temporal_stability" in temporal_metrics and isinstance(temporal_metrics["temporal_stability"], dict):
            tsi_val = temporal_metrics["temporal_stability"].get("temporal_stability_index")
    temporal_stability_index = _safe_float(tsi_val)

    fingerprint = {
        "mean_displacement": d_mean,
        "max_displacement": d_max,
        "mean_strain": mean_strain,
        "max_strain": max_strain,
        "mean_principal_strain": mean_principal_strain,
        "anisotropy_index": anisotropy_index,
        "strain_entropy": strain_entropy,
        "strain_gradient": strain_gradient,
        "motion_coherence": motion_coherence,
        "temporal_stability_index": temporal_stability_index,
    }

    vector: List[Optional[float]] = [
        fingerprint["mean_displacement"],
        fingerprint["max_displacement"],
        fingerprint["mean_strain"],
        fingerprint["max_strain"],
        fingerprint["mean_principal_strain"],
        fingerprint["anisotropy_index"],
        fingerprint["strain_entropy"],
        fingerprint["strain_gradient"],
        fingerprint["motion_coherence"],
        fingerprint["temporal_stability_index"],
    ]

    # Safe per-analysis min-max normalization across available values
    valid_values = [v for v in vector if v is not None and np.isfinite(v)]
    if valid_values:
        min_v = min(valid_values)
        max_v = max(valid_values)
        span = max_v - min_v
        if span > 0:
            normalized_vector = [
                float((v - min_v) / span) if (v is not None and np.isfinite(v)) else None
                for v in vector
            ]
        else:
            # If all values are identical
            normalized_vector = [
                1.0 if (v is not None and np.isfinite(v) and v != 0) else (0.0 if (v is not None and np.isfinite(v)) else None)
                for v in vector
            ]
    else:
        normalized_vector = [None] * len(vector)

    available = sum(1 for v in vector if v is not None)
    missing = sum(1 for v in vector if v is None)

    summary = {
        "dimensions": 10,
        "available": available,
        "missing": missing,
    }

    return {
        "fingerprint": fingerprint,
        "vector": vector,
        "normalized_vector": normalized_vector,
        "summary": summary,
    }

