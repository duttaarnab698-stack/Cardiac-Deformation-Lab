import cv2
import numpy as np
from pathlib import Path


def calculate_strain_tensor(flow: np.ndarray):
    """
    Calculate the small-deformation strain tensor from optical flow.

    flow[..., 0] = u displacement in x direction
    flow[..., 1] = v displacement in y direction
    """

    u = flow[..., 0]
    v = flow[..., 1]

    du_dy, du_dx = np.gradient(u)
    dv_dy, dv_dx = np.gradient(v)

    exx = du_dx
    eyy = dv_dy
    exy = 0.5 * (du_dy + dv_dx)

    return exx, eyy, exy


def calculate_principal_strains(exx, eyy, exy):
    """
    Calculate principal strains from the 2D strain tensor.
    """

    trace = exx + eyy
    difference = exx - eyy

    radius = np.sqrt(
        (difference / 2.0) ** 2 + exy ** 2
    )

    principal_1 = (trace / 2.0) + radius
    principal_2 = (trace / 2.0) - radius

    return principal_1, principal_2


def calculate_strain_statistics(
    exx,
    eyy,
    exy,
    principal_1,
    principal_2
):
    """
    Calculate basic statistics of strain fields.
    """

    return {
        "mean_exx": float(np.mean(exx)),
        "mean_eyy": float(np.mean(eyy)),
        "mean_exy": float(np.mean(exy)),

        "max_exx": float(np.max(exx)),
        "max_eyy": float(np.max(eyy)),
        "max_exy": float(np.max(exy)),

        "mean_principal_strain_1": float(np.mean(principal_1)),
        "mean_principal_strain_2": float(np.mean(principal_2)),

        "max_principal_strain_1": float(np.max(principal_1)),
        "min_principal_strain_1": float(np.min(principal_1)),

        "max_principal_strain_2": float(np.max(principal_2)),
        "min_principal_strain_2": float(np.min(principal_2)),
    }


def create_strain_heatmap(
    strain: np.ndarray,
    output_path: str
):
    """
    Create a color heatmap from a strain field.

    Uses absolute strain values so that both tension and
    compression produce visible contrast.
    """

    # Use absolute values for visualization
    abs_strain = np.abs(strain)

    # Normalize to 0-255
    normalized = cv2.normalize(
        abs_strain,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    normalized = normalized.astype(np.uint8)

    # Apply JET colormap
    heatmap = cv2.applyColorMap(
        normalized,
        cv2.COLORMAP_JET
    )

    # Create output directory if needed
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save image
    success = cv2.imwrite(str(output_path), heatmap)

    if not success:
        raise ValueError(
            f"Failed to save strain heatmap to {output_path}"
        )

    return str(output_path)


def create_principal_strain_heatmap(
    principal_strain: np.ndarray,
    output_path: str
):
    """
    Create a color heatmap from a principal strain field.

    Uses absolute values so the magnitude of principal
    extension/compression is clearly visible.
    """

    # Use absolute values for visualization
    abs_strain = np.abs(principal_strain)

    # Normalize to 0-255
    normalized = cv2.normalize(
        abs_strain,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    normalized = normalized.astype(np.uint8)

    # Apply JET colormap
    heatmap = cv2.applyColorMap(
        normalized,
        cv2.COLORMAP_JET
    )

    # Create output directory if needed
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save image
    success = cv2.imwrite(str(output_path), heatmap)

    if not success:
        raise ValueError(
            f"Failed to save principal strain heatmap to {output_path}"
        )

    return str(output_path)




def calculate_principal_strain_direction(exx, eyy, exy):
    """
    Calculate the orientation angle of the maximum principal strain
    at each pixel using the standard 2D strain tensor formula:

        theta = 0.5 * arctan2(2 * exy, exx - eyy)

    Returns:
        theta : np.ndarray
            Angle in radians, shape matching exx/eyy/exy.
            Range: [-pi/2, pi/2]
    """

    theta = 0.5 * np.arctan2(
        2.0 * exy,
        exx - eyy
    )

    return theta


def create_principal_direction_map(
    image: np.ndarray,
    principal_strain: np.ndarray,
    theta: np.ndarray,
    output_path: str,
    step: int = 20
):
    """
    Draw principal strain direction arrows on the original image.

    At each sampled grid point the arrow direction is given by theta
    and its length is scaled by the local principal strain magnitude,
    capped to avoid excessively long arrows.

    Args:
        image           : original BGR or grayscale image (background).
        principal_strain: 2-D array of principal strain magnitudes.
        theta           : 2-D array of principal direction angles (radians).
        output_path     : destination file path.
        step            : grid spacing in pixels between sampled points.

    Returns:
        str: saved output path.
    """

    # Convert grayscale to BGR so colored arrows are visible
    if len(image.shape) == 2:
        visualization = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        visualization = image.copy()

    height, width = image.shape[:2]

    # Compute a per-image scale factor so the longest arrow
    # spans at most (step - 2) pixels — keeps the map readable
    max_magnitude = float(np.max(np.abs(principal_strain)))
    max_arrow_length = step - 2  # pixels

    if max_magnitude > 0:
        scale = max_arrow_length / max_magnitude
    else:
        scale = 0.0

    # Draw one arrow per grid cell
    for y in range(0, height, step):
        for x in range(0, width, step):

            angle     = float(theta[y, x])
            magnitude = float(np.abs(principal_strain[y, x]))

            arrow_length = magnitude * scale

            dx = np.cos(angle) * arrow_length
            dy = np.sin(angle) * arrow_length

            start_point = (int(x), int(y))
            end_point   = (
                int(x + dx),
                int(y + dy)
            )

            # Skip degenerate zero-length arrows
            if start_point == end_point:
                continue

            cv2.arrowedLine(
                visualization,
                start_point,
                end_point,
                (0, 255, 255),   # yellow arrows for visibility
                1,
                tipLength=0.3
            )

    # Save visualization
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = cv2.imwrite(str(output_path), visualization)

    if not success:
        raise ValueError(
            f"Failed to save principal direction map to {output_path}"
        )

    return str(output_path)