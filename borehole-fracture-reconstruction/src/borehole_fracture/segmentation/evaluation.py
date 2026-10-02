"""IoU and Dice evaluation using fracture pixels as the foreground class."""
import numpy as np


def metrics(predicted, reference):
    if predicted.shape != reference.shape:
        raise ValueError("Prediction and reference dimensions must match")
    intersection = np.logical_and(predicted, reference).sum()
    union = np.logical_or(predicted, reference).sum()
    total = predicted.sum() + reference.sum()
    return {"iou": float(intersection/union) if union else 1.0,
            "dice": float(2*intersection/total) if total else 1.0}
