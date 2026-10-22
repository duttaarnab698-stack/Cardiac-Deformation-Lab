import cv2
import numpy as np
from pathlib import Path


def load_image(image_path: str):
    """
    Load an image from disk using OpenCV.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Unable to read image")

    return image


def preprocess_image(image: np.ndarray):
    """
    Basic preprocessing for cardiac image analysis.

    Steps:
    1. Convert BGR image to grayscale
    2. Normalize intensity
    3. Apply Gaussian smoothing
    """

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Normalize intensity to 0-255
    normalized = cv2.normalize(
        gray,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    # Reduce image noise
    smoothed = cv2.GaussianBlur(
        normalized,
        (5, 5),
        0
    )

    return smoothed


def save_processed_image(
    image: np.ndarray,
    output_path: str
):
    """
    Save processed image to disk.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    success = cv2.imwrite(
        str(output_path),
        image
    )

    if not success:
        raise ValueError("Failed to save processed image")

    return str(output_path)