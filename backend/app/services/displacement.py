import cv2
import numpy as np
from pathlib import Path


def create_displacement_heatmap(
    magnitude: np.ndarray,
    output_path: str
):
    """
    Create a color heatmap from displacement magnitude.
    """

    # Normalize displacement to 0-255
    normalized = cv2.normalize(
        magnitude,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    normalized = normalized.astype(np.uint8)

    # Apply color map
    heatmap = cv2.applyColorMap(
        normalized,
        cv2.COLORMAP_JET
    )

    # Create output directory
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save image
    success = cv2.imwrite(
        str(output_path),
        heatmap
    )

    if not success:
        raise ValueError(
            "Failed to save displacement heatmap"
        )

    return str(output_path)


def create_motion_vector_map(
    image: np.ndarray,
    flow: np.ndarray,
    output_path: str,
    step: int = 20
):
    """
    Draw optical-flow vectors on the original image.

    flow[..., 0] = horizontal displacement
    flow[..., 1] = vertical displacement
    """

    # Convert grayscale image to BGR
    if len(image.shape) == 2:
        visualization = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGR
        )
    else:
        visualization = image.copy()

    height, width = image.shape[:2]

    # Draw vectors at regular intervals
    for y in range(0, height, step):

        for x in range(0, width, step):

            u = flow[y, x, 0]
            v = flow[y, x, 1]

            start_point = (
                int(x),
                int(y)
            )

            end_point = (
                int(x + u),
                int(y + v)
            )

            cv2.arrowedLine(
                visualization,
                start_point,
                end_point,
                (0, 255, 0),
                1,
                tipLength=0.3
            )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    success = cv2.imwrite(
        str(output_path),
        visualization
    )

    if not success:
        raise ValueError(
            "Failed to save motion vector map"
        )

    return str(output_path)