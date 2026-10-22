"""
backend/app/services/synthetic_data.py

Controllable Synthetic Cardiac Deformation Generator and Phantom Data Service
for the Cardiac Deformation Lab.

Generates:
1. Artificial myocardial-like ring phantoms with textured intensity patterns.
2. Controllable analytical deformations:
   - Translation
   - Radial expansion
   - Radial contraction
   - Circumferential deformation (torsion/twist)
   - Uniform scaling
   - Mild shear
   - Combined deformation
3. Exact mathematical ground-truth displacement fields u(x,y), v(x,y), magnitude.
4. Exact analytical / numerical ground-truth strain fields (exx, eyy, exy, principal 1 & 2,
   radial deformation, circumferential deformation).
5. Ground-truth myocardial ring region mask.
6. Multi-frame image sequences with progressive temporal deformation.

Strict research prototype rules:
- Clearly marked as synthetic/phantom data.
- Does not claim clinical validity or patient equivalence.
"""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

SYNTHETIC_DATA_DIR = Path("data/synthetic")
SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_DEFORMATION_MODES = [
    "translation",
    "radial_expansion",
    "radial_contraction",
    "circumferential_deformation",
    "uniform_scaling",
    "shear",
    "combined"
]


def validate_synthetic_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clamp synthetic phantom generation parameters.
    Ensures safe dimensions, valid deformation mode, and non-negative parameters.
    """
    width = int(config.get("width", 256))
    height = int(config.get("height", 256))
    width = max(64, min(1024, width))
    height = max(64, min(1024, height))

    center_x = float(config.get("center_x", width / 2.0))
    center_y = float(config.get("center_y", height / 2.0))

    inner_radius = float(config.get("inner_radius", 45.0))
    outer_radius = float(config.get("outer_radius", 75.0))

    # Clamp radii
    max_radius = min(width, height) / 2.0 - 5.0
    inner_radius = max(5.0, min(inner_radius, max_radius - 10.0))
    outer_radius = max(inner_radius + 5.0, min(outer_radius, max_radius))

    mode = str(config.get("deformation_mode", "radial_expansion")).lower().strip()
    if mode not in SUPPORTED_DEFORMATION_MODES:
        mode = "radial_expansion"

    strength = float(config.get("deformation_strength", 0.05))
    strength = max(0.001, min(0.30, strength))

    noise_level = float(config.get("noise_level", 0.0))
    noise_level = max(0.0, min(0.20, noise_level))

    blur_sigma = float(config.get("blur_sigma", 0.0))
    blur_sigma = max(0.0, min(5.0, blur_sigma))

    frame_count = int(config.get("frame_count", 5))
    frame_count = max(2, min(20, frame_count))

    return {
        "width": width,
        "height": height,
        "center_x": center_x,
        "center_y": center_y,
        "inner_radius": inner_radius,
        "outer_radius": outer_radius,
        "deformation_mode": mode,
        "deformation_strength": strength,
        "noise_level": noise_level,
        "blur_sigma": blur_sigma,
        "frame_count": frame_count
    }


def _render_phantom_intensity(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    cx: float,
    cy: float,
    r_in: float,
    r_out: float
) -> np.ndarray:
    """
    Evaluate continuous intensity pattern at given (x, y) coordinates.
    Produces an artificial myocardial ring with rich multi-frequency texture,
    dark blood pool cavity, and dark outer background.
    """
    dx = x_coords - cx
    dy = y_coords - cy
    r = np.sqrt(dx**2 + dy**2)

    # Multi-frequency textured pattern inside myocardium for robust optical flow tracking
    # Combines sinusoidal waves and spatial harmonics
    texture = (
        0.50
        + 0.22 * np.sin(0.18 * x_coords) * np.cos(0.15 * y_coords)
        + 0.15 * np.cos(0.32 * x_coords + 0.22 * y_coords)
        + 0.10 * np.sin(0.45 * x_coords - 0.28 * y_coords)
        + 0.08 * np.sin(0.12 * dx * dy / (r_out + 1.0))
    )

    # Sigmoid smoothing around ring boundaries for smooth gradients
    trans_w = 2.0
    w_inner = 1.0 / (1.0 + np.exp(-(r - r_in) / trans_w))
    w_outer = 1.0 / (1.0 + np.exp((r - r_out) / trans_w))
    ring_weight = w_inner * w_outer

    # Cavity (blood pool) intensity ~ 35, outer background ~ 25, myocardium ~ 130-225
    cavity_int = 35.0
    bg_int = 25.0
    cavity_weight = 1.0 - w_inner
    bg_weight = 1.0 - w_outer

    myo_int = 135.0 + 85.0 * texture

    # Total intensity blend
    intensity = ring_weight * myo_int + cavity_weight * cavity_int + bg_weight * bg_int
    return np.clip(intensity, 0.0, 255.0)


def _apply_noise_and_blur(img: np.ndarray, noise_level: float, blur_sigma: float) -> np.ndarray:
    """Apply optional additive Gaussian noise and Gaussian blur."""
    out = img.copy().astype(np.float32)

    if noise_level > 0.0:
        noise = np.random.normal(0.0, noise_level * 255.0, img.shape).astype(np.float32)
        out = np.clip(out + noise, 0.0, 255.0)

    if blur_sigma > 0.0:
        # Kernel size must be positive and odd
        ksize = int(math.ceil(blur_sigma * 3)) * 2 + 1
        out = cv2.GaussianBlur(out, (ksize, ksize), blur_sigma)

    return np.clip(out, 0, 255).astype(np.uint8)


def generate_reference_image(config: Dict[str, Any]) -> np.ndarray:
    """Generate the undeformed reference cardiac phantom image."""
    w, h = config["width"], config["height"]
    cx, cy = config["center_x"], config["center_y"]
    r_in, r_out = config["inner_radius"], config["outer_radius"]

    grid_y, grid_x = np.indices((h, w), dtype=np.float32)
    img_float = _render_phantom_intensity(grid_x, grid_y, cx, cy, r_in, r_out)
    return _apply_noise_and_blur(img_float, config["noise_level"], config["blur_sigma"])


def _get_affine_transform(
    mode: str,
    strength: float,
    cx: float,
    cy: float
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Compute affine transformation matrix A (2x2) and translation t (2,)
    such that point (x, y) moves to x' - c = A (x - c) + t.
    Returns: A, t, analytical_derivatives
    """
    if mode == "translation":
        # Pure translation: A = I, t = [strength * 10, strength * 5]
        A = np.eye(2, dtype=np.float64)
        t = np.array([strength * 10.0, strength * 5.0], dtype=np.float64)
        derivs = {"du_dx": 0.0, "du_dy": 0.0, "dv_dx": 0.0, "dv_dy": 0.0}

    elif mode == "radial_expansion":
        # x' - c = (1 + s)(x - c)
        s = strength
        A = np.array([[1.0 + s, 0.0], [0.0, 1.0 + s]], dtype=np.float64)
        t = np.zeros(2, dtype=np.float64)
        derivs = {"du_dx": s, "du_dy": 0.0, "dv_dx": 0.0, "dv_dy": s}

    elif mode == "radial_contraction":
        # x' - c = (1 - s)(x - c)
        s = strength
        A = np.array([[1.0 - s, 0.0], [0.0, 1.0 - s]], dtype=np.float64)
        t = np.zeros(2, dtype=np.float64)
        derivs = {"du_dx": -s, "du_dy": 0.0, "dv_dx": 0.0, "dv_dy": -s}

    elif mode == "circumferential_deformation":
        # Rotation around center by angle s radians
        s = strength
        cos_s = math.cos(s)
        sin_s = math.sin(s)
        A = np.array([[cos_s, -sin_s], [sin_s, cos_s]], dtype=np.float64)
        t = np.zeros(2, dtype=np.float64)
        derivs = {
            "du_dx": cos_s - 1.0,
            "du_dy": -sin_s,
            "dv_dx": sin_s,
            "dv_dy": cos_s - 1.0
        }

    elif mode == "uniform_scaling":
        s = strength
        A = np.array([[1.0 + s, 0.0], [0.0, 1.0 + s]], dtype=np.float64)
        t = np.zeros(2, dtype=np.float64)
        derivs = {"du_dx": s, "du_dy": 0.0, "dv_dx": 0.0, "dv_dy": s}

    elif mode == "shear":
        # Simple horizontal shear: x' = x + s(y - cy), y' = y
        s = strength
        A = np.array([[1.0, s], [0.0, 1.0]], dtype=np.float64)
        t = np.zeros(2, dtype=np.float64)
        derivs = {"du_dx": 0.0, "du_dy": s, "dv_dx": 0.0, "dv_dy": 0.0}

    elif mode == "combined":
        # Combined contraction + twist + translation
        s = strength
        s_rad = -0.5 * s
        s_rot = 0.4 * s
        cos_r = math.cos(s_rot)
        sin_r = math.sin(s_rot)
        M_rad = np.array([[1.0 + s_rad, 0.0], [0.0, 1.0 + s_rad]], dtype=np.float64)
        M_rot = np.array([[cos_r, -sin_r], [sin_r, cos_r]], dtype=np.float64)
        A = M_rot @ M_rad
        t = np.array([s * 3.0, s * 2.0], dtype=np.float64)
        derivs = {
            "du_dx": float(A[0, 0] - 1.0),
            "du_dy": float(A[0, 1]),
            "dv_dx": float(A[1, 0]),
            "dv_dy": float(A[1, 1] - 1.0)
        }
    else:
        A = np.eye(2, dtype=np.float64)
        t = np.zeros(2, dtype=np.float64)
        derivs = {"du_dx": 0.0, "du_dy": 0.0, "dv_dx": 0.0, "dv_dy": 0.0}

    return A, t, derivs


def generate_ground_truth_displacement(
    config: Dict[str, Any],
    scale_factor: float = 1.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate exact analytical ground-truth displacement fields u(x,y), v(x,y), and magnitude.
    Displacement is defined from reference frame to deformed frame:
        u(x, y) = x'(x, y) - x
        v(x, y) = y'(x, y) - y
    """
    w, h = config["width"], config["height"]
    cx, cy = config["center_x"], config["center_y"]
    mode = config["deformation_mode"]
    strength = config["deformation_strength"] * scale_factor

    A, t, _ = _get_affine_transform(mode, strength, cx, cy)

    grid_y, grid_x = np.indices((h, w), dtype=np.float64)
    dx = grid_x - cx
    dy = grid_y - cy

    # x' - cx = A00 dx + A01 dy + t0
    # y' - cy = A10 dx + A11 dy + t1
    x_prime = cx + A[0, 0] * dx + A[0, 1] * dy + t[0]
    y_prime = cy + A[1, 0] * dx + A[1, 1] * dy + t[1]

    u = (x_prime - grid_x).astype(np.float32)
    v = (y_prime - grid_y).astype(np.float32)
    mag = np.sqrt(u**2 + v**2).astype(np.float32)

    return u, v, mag


def generate_ground_truth_strain(
    config: Dict[str, Any],
    scale_factor: float = 1.0
) -> Dict[str, np.ndarray]:
    """
    Calculate exact analytical ground truth strain fields:
    exx, eyy, exy, principal_1, principal_2, radial, circumferential.
    """
    w, h = config["width"], config["height"]
    cx, cy = config["center_x"], config["center_y"]
    mode = config["deformation_mode"]
    strength = config["deformation_strength"] * scale_factor

    _, _, derivs = _get_affine_transform(mode, strength, cx, cy)

    du_dx = derivs["du_dx"]
    du_dy = derivs["du_dy"]
    dv_dx = derivs["dv_dx"]
    dv_dy = derivs["dv_dy"]

    # In-plane strain tensor components
    exx_val = du_dx
    eyy_val = dv_dy
    exy_val = 0.5 * (du_dy + dv_dx)

    exx = np.full((h, w), exx_val, dtype=np.float32)
    eyy = np.full((h, w), eyy_val, dtype=np.float32)
    exy = np.full((h, w), exy_val, dtype=np.float32)

    # Principal strains
    trace = exx_val + eyy_val
    diff = exx_val - eyy_val
    rad_term = math.sqrt((diff / 2.0)**2 + exy_val**2)

    p1_val = (trace / 2.0) + rad_term
    p2_val = (trace / 2.0) - rad_term

    p1 = np.full((h, w), p1_val, dtype=np.float32)
    p2 = np.full((h, w), p2_val, dtype=np.float32)

    # Radial and circumferential deformation components
    grid_y, grid_x = np.indices((h, w), dtype=np.float64)
    dx = grid_x - cx
    dy = grid_y - cy
    theta = np.arctan2(dy, dx)
    cos_t = np.cos(theta).astype(np.float32)
    sin_t = np.sin(theta).astype(np.float32)

    # Strain tensor transformation to polar coordinate basis
    # err = exx cos^2 + eyy sin^2 + 2 exy sin cos
    # ett = exx sin^2 + eyy cos^2 - 2 exy sin cos
    radial_strain = (
        exx * (cos_t**2) + eyy * (sin_t**2) + 2.0 * exy * sin_t * cos_t
    ).astype(np.float32)

    circumferential_strain = (
        exx * (sin_t**2) + eyy * (cos_t**2) - 2.0 * exy * sin_t * cos_t
    ).astype(np.float32)

    return {
        "exx": exx,
        "eyy": eyy,
        "exy": exy,
        "principal_1": p1,
        "principal_2": p2,
        "radial": radial_strain,
        "circumferential": circumferential_strain
    }


def generate_deformed_image(
    config: Dict[str, Any],
    scale_factor: float = 1.0
) -> np.ndarray:
    """
    Generate the deformed cardiac phantom image corresponding to the analytical transformation.
    Evaluates inverse coordinate mapping continuously from the continuous phantom equation.
    """
    w, h = config["width"], config["height"]
    cx, cy = config["center_x"], config["center_y"]
    r_in, r_out = config["inner_radius"], config["outer_radius"]
    mode = config["deformation_mode"]
    strength = config["deformation_strength"] * scale_factor

    A, t, _ = _get_affine_transform(mode, strength, cx, cy)

    # Inverse mapping: x - cx = A_inv (x' - cx - t)
    A_inv = np.linalg.inv(A)

    grid_y_prime, grid_x_prime = np.indices((h, w), dtype=np.float64)
    dx_prime = grid_x_prime - cx - t[0]
    dy_prime = grid_y_prime - cy - t[1]

    orig_x = cx + A_inv[0, 0] * dx_prime + A_inv[0, 1] * dy_prime
    orig_y = cy + A_inv[1, 0] * dx_prime + A_inv[1, 1] * dy_prime

    img_float = _render_phantom_intensity(orig_x, orig_y, cx, cy, r_in, r_out)
    return _apply_noise_and_blur(img_float, config["noise_level"], config["blur_sigma"])


def generate_image_sequence(config: Dict[str, Any]) -> List[np.ndarray]:
    """Generate a multi-frame image sequence with progressive deformation."""
    n_frames = config["frame_count"]
    frames = []

    for i in range(n_frames):
        alpha = float(i) / float(n_frames - 1) if n_frames > 1 else 0.0
        if i == 0:
            frame = generate_reference_image(config)
        else:
            frame = generate_deformed_image(config, scale_factor=alpha)
        frames.append(frame)

    return frames


def generate_synthetic_dataset(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construct an entire synthetic benchmark dataset including frames,
    ground-truth displacement, ground-truth strain, and myocardial mask.
    """
    valid_cfg = validate_synthetic_config(config)
    dataset_id = str(uuid.uuid4())

    # Generate sequence
    frames = generate_image_sequence(valid_cfg)

    # Compute ground truth between frame 0 (reference) and final frame (full deformation)
    u_gt, v_gt, mag_gt = generate_ground_truth_displacement(valid_cfg, scale_factor=1.0)
    strain_gt = generate_ground_truth_strain(valid_cfg, scale_factor=1.0)

    # Ground truth myocardial ring mask
    w, h = valid_cfg["width"], valid_cfg["height"]
    cx, cy = valid_cfg["center_x"], valid_cfg["center_y"]
    r_in, r_out = valid_cfg["inner_radius"], valid_cfg["outer_radius"]
    grid_y, grid_x = np.indices((h, w), dtype=np.float64)
    r = np.sqrt((grid_x - cx)**2 + (grid_y - cy)**2)
    myo_mask = ((r >= r_in) & (r <= r_out)).astype(np.uint8)

    # Metadata
    metadata = {
        "dataset_id": dataset_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_synthetic": True,
        "synthetic_label": "Synthetic / Phantom Data — Mathematical Benchmark",
        "config": valid_cfg,
        "frame_count": len(frames),
        "dimensions": {"width": w, "height": h},
        "ground_truth_summary": {
            "mean_displacement": float(np.mean(mag_gt)),
            "max_displacement": float(np.max(mag_gt)),
            "myo_mean_displacement": float(np.mean(mag_gt[myo_mask == 1])) if np.any(myo_mask == 1) else 0.0,
            "mean_principal_strain_1": float(np.mean(strain_gt["principal_1"])),
            "mean_principal_strain_2": float(np.mean(strain_gt["principal_2"])),
            "mean_radial_deformation": float(np.mean(strain_gt["radial"][myo_mask == 1])) if np.any(myo_mask == 1) else 0.0,
            "mean_circumferential_deformation": float(np.mean(strain_gt["circumferential"][myo_mask == 1])) if np.any(myo_mask == 1) else 0.0
        },
        "disclaimer": (
            "Synthetic data generated for computational benchmark purposes with exact mathematical ground truth. "
            "Does not represent patient data and does not establish clinical validity."
        )
    }

    return {
        "dataset_id": dataset_id,
        "metadata": metadata,
        "frames": frames,
        "ground_truth": {
            "displacement_u": u_gt,
            "displacement_v": v_gt,
            "displacement_magnitude": mag_gt,
            "strain_exx": strain_gt["exx"],
            "strain_eyy": strain_gt["eyy"],
            "strain_exy": strain_gt["exy"],
            "principal_strain_1": strain_gt["principal_1"],
            "principal_strain_2": strain_gt["principal_2"],
            "radial": strain_gt["radial"],
            "circumferential": strain_gt["circumferential"],
            "myocardial_mask": myo_mask
        }
    }


def save_synthetic_dataset(dataset_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist synthetic dataset to data/synthetic/dataset_<id>/.
    Saves PNG frames, metadata JSON, and ground-truth NumPy arrays.
    """
    dataset_id = dataset_data["dataset_id"]
    ds_dir = SYNTHETIC_DATA_DIR / f"dataset_{dataset_id}"
    ds_dir.mkdir(parents=True, exist_ok=True)
    gt_dir = ds_dir / "ground_truth"
    gt_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save PNG frames
    frame_paths = []
    frame_filenames = []
    for idx, frame in enumerate(dataset_data["frames"]):
        fn = f"frame_{idx:03d}.png"
        fpath = ds_dir / fn
        cv2.imwrite(str(fpath), frame)
        frame_paths.append(str(fpath))
        frame_filenames.append(fn)

    # 2. Save ground truth arrays
    gt = dataset_data["ground_truth"]
    np.save(str(gt_dir / "displacement_u.npy"), gt["displacement_u"])
    np.save(str(gt_dir / "displacement_v.npy"), gt["displacement_v"])
    np.save(str(gt_dir / "displacement_magnitude.npy"), gt["displacement_magnitude"])
    np.save(str(gt_dir / "strain_exx.npy"), gt["strain_exx"])
    np.save(str(gt_dir / "strain_eyy.npy"), gt["strain_eyy"])
    np.save(str(gt_dir / "strain_exy.npy"), gt["strain_exy"])
    np.save(str(gt_dir / "principal_strain_1.npy"), gt["principal_strain_1"])
    np.save(str(gt_dir / "principal_strain_2.npy"), gt["principal_strain_2"])
    np.save(str(gt_dir / "radial.npy"), gt["radial"])
    np.save(str(gt_dir / "circumferential.npy"), gt["circumferential"])
    np.save(str(gt_dir / "myocardial_mask.npy"), gt["myocardial_mask"])

    # 3. Save metadata
    meta = dataset_data["metadata"]
    meta["frame_filenames"] = frame_filenames
    meta["frame_urls"] = [f"/synthetic-data/dataset_{dataset_id}/{fn}" for fn in frame_filenames]
    meta_path = ds_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {
        "dataset_id": dataset_id,
        "dataset_dir": str(ds_dir),
        "frame_count": len(frame_filenames),
        "frames": meta["frame_urls"],
        "metadata": meta
    }


def get_synthetic_dataset_metadata(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata.json for a saved dataset."""
    ds_dir = SYNTHETIC_DATA_DIR / f"dataset_{dataset_id}"
    meta_path = ds_dir / "metadata.json"
    if not meta_path.exists():
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_synthetic_dataset(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Load frames, metadata, and ground truth arrays from disk."""
    ds_dir = SYNTHETIC_DATA_DIR / f"dataset_{dataset_id}"
    meta = get_synthetic_dataset_metadata(dataset_id)
    if not meta:
        return None

    # Load frames
    frames = []
    for fn in meta.get("frame_filenames", []):
        fpath = ds_dir / fn
        if fpath.exists():
            img = cv2.imread(str(fpath), cv2.IMREAD_GRAYSCALE)
            frames.append(img)

    # Load ground truth
    gt_dir = ds_dir / "ground_truth"
    try:
        gt = {
            "displacement_u": np.load(str(gt_dir / "displacement_u.npy")),
            "displacement_v": np.load(str(gt_dir / "displacement_v.npy")),
            "displacement_magnitude": np.load(str(gt_dir / "displacement_magnitude.npy")),
            "strain_exx": np.load(str(gt_dir / "strain_exx.npy")),
            "strain_eyy": np.load(str(gt_dir / "strain_eyy.npy")),
            "strain_exy": np.load(str(gt_dir / "strain_exy.npy")),
            "principal_strain_1": np.load(str(gt_dir / "principal_strain_1.npy")),
            "principal_strain_2": np.load(str(gt_dir / "principal_strain_2.npy")),
            "radial": np.load(str(gt_dir / "radial.npy")),
            "circumferential": np.load(str(gt_dir / "circumferential.npy")),
            "myocardial_mask": np.load(str(gt_dir / "myocardial_mask.npy"))
        }
    except Exception:
        gt = None

    return {
        "dataset_id": dataset_id,
        "metadata": meta,
        "frames": frames,
        "ground_truth": gt
    }

