"""Classical segmentation and optional tiled U-Net inference."""
import cv2
import numpy as np


def classical_mask(image, min_area=40):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    smooth = cv2.GaussianBlur(gray, (3, 3), 0)
    # Remove column-wise illumination bias before extracting locally dark ridges.
    corrected = np.clip(smooth.astype(float) - np.median(smooth, axis=0) + np.median(smooth), 0, 255).astype(np.uint8)
    contrast = cv2.morphologyEx(corrected, cv2.MORPH_BLACKHAT,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (3, 21)))
    _, binary = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 5), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    keep = np.zeros(count, dtype=bool)
    for i in range(1, count):
        _, _, width, height, area = stats[i]
        # Very thin, long vertical components are typical streak artefacts.
        keep[i] = area >= min_area and not (height > width * 15 and width < 8)
    return keep[labels]


class UNetPredictor:
    def __init__(self, model_path, threshold=0.5):
        import tensorflow as tf
        self.model = tf.keras.models.load_model(model_path, compile=False)
        _, self.height, self.width, channels = self.model.input_shape
        if channels != 3 or not self.height or not self.width:
            raise ValueError("U-Net needs a fixed H×W×3 input")
        self.threshold = threshold

    def predict(self, image):
        height, width = image.shape[:2]
        # Tile along depth. Each tile covers the same physical aspect ratio as the model input.
        tile_height = max(1, round(width * self.height / self.width))
        stride = max(1, tile_height // 2)
        score, weight = np.zeros((height, width), np.float32), np.zeros((height, width), np.float32)
        for top in range(0, height, stride):
            bottom = min(height, top + tile_height)
            tile = image[top:bottom]
            scale = min(self.width / width, self.height / tile.shape[0])
            rw, rh = max(1, round(width * scale)), max(1, round(tile.shape[0] * scale))
            canvas = np.zeros((self.height, self.width, 3), np.uint8)
            canvas[:rh, :rw] = cv2.resize(tile, (rw, rh))
            rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
            pred = self.model.predict(rgb[None], verbose=0)[0, :rh, :rw, 0]
            score[top:bottom] += cv2.resize(pred, (width, bottom-top))
            weight[top:bottom] += 1
            if bottom == height:
                break
        return score / np.maximum(weight, 1) >= self.threshold
