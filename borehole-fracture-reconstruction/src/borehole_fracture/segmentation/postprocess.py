"""Morphological repair followed by Hough-supported sinusoidal continuity repair."""
import cv2
import numpy as np
from ..geometry.fitting import fit_sinusoid


def enhance(mask, max_gap=9, min_span_fraction=0.25):
    raw = mask.astype(np.uint8) * 255
    repaired = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, np.ones((3, max_gap), np.uint8))
    edges = cv2.Canny(repaired, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=15,
                           minLineLength=max(10, mask.shape[1]//20), maxLineGap=max_gap)
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            # Only bridge nearby pixels on detected edges; avoid painting unsupported long lines.
            if abs(x2-x1) >= abs(y2-y1) and max(abs(x2-x1), abs(y2-y1)) <= max_gap*4:
                cv2.line(repaired, (x1, y1), (x2, y2), 255, 1)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(repaired, 8)
    height, width = mask.shape
    for label in range(1, count):
        left, _, span, _, _ = stats[label]
        if span < width * min_span_fraction:
            continue
        ys, xs = np.where(labels == label)
        unique = np.unique(xs)
        profile = np.array([np.median(ys[xs == x]) for x in unique])
        if len(unique) < 12:
            continue
        fit = fit_sinusoid(unique / width, profile, period=1.0)
        if fit["fit_r2"] < 0.7:
            continue
        # Fit first, then bridge only small gaps in the observed span.
        support = np.zeros(width, bool)
        support[unique] = True
        for a, b in zip(unique[:-1], unique[1:]):
            if 1 < b-a <= max_gap:
                x = np.arange(a+1, b)
                y = np.rint(fit["amplitude"] * np.sin(2*np.pi*x/width + fit["phase"]) + fit["center"]).astype(int)
                repaired[np.clip(y, 0, height-1), x] = 255
    return repaired > 0
