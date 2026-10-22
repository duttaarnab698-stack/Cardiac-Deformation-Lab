import cv2
import numpy as np


def calculate_optical_flow(
    image1: np.ndarray,
    image2: np.ndarray
):
    """
    Calculate dense optical flow between two cardiac images.

    Returns:
        flow[..., 0] = horizontal displacement u
        flow[..., 1] = vertical displacement v
    """

    # Convert images to grayscale if necessary
    if len(image1.shape) == 3:
        image1 = cv2.cvtColor(
            image1,
            cv2.COLOR_BGR2GRAY
        )

    if len(image2.shape) == 3:
        image2 = cv2.cvtColor(
            image2,
            cv2.COLOR_BGR2GRAY
        )

    # Ensure same dimensions
    if image1.shape != image2.shape:
        image2 = cv2.resize(
            image2,
            (image1.shape[1], image1.shape[0])
        )

    flow = cv2.calcOpticalFlowFarneback(
        image1,
        image2,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0
    )

    return flow


def calculate_displacement_magnitude(flow: np.ndarray):
    """
    Calculate displacement magnitude:

        D(x,y) = sqrt(u² + v²)
    """

    u = flow[..., 0]
    v = flow[..., 1]

    magnitude = np.sqrt(
        u ** 2 + v ** 2
    )

    return magnitude


def calculate_motion_statistics(flow: np.ndarray):
    """
    Calculate basic displacement statistics.
    """

    magnitude = calculate_displacement_magnitude(flow)

    return {
        "mean_displacement": float(
            np.mean(magnitude)
        ),
        "max_displacement": float(
            np.max(magnitude)
        ),
        "min_displacement": float(
            np.min(magnitude)
        ),
        "std_displacement": float(
            np.std(magnitude)
        )
    }