"""Connected-component instances, centerline extraction and parameter tables."""
import cv2
import numpy as np
from .fitting import fit_sinusoid

PARAMETER_COLUMNS = ["fracture_id", "image_id", "borehole_id", "amplitude_mm", "period_mm",
                     "phase_rad", "center_depth_mm", "diameter_mm", "azimuth_offset_rad",
                     "fit_r2", "rmse_mm", "coverage", "area_mm2", "profile_path"]
PROFILE_COLUMNS = ["x_mm", "depth_mm", "baseline_mm", "residual_mm"]


def characterize(mask, calibration, image_id, borehole_id, min_area=40, min_coverage=0.15):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    height, width = mask.shape
    sx, sy = calibration.circumference_mm / width, calibration.interval_mm / height
    records, profiles = [], {}
    serial = 0
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < min_area:
            continue
        rows, cols = np.where(labels == label)
        xs = np.unique(cols)
        if len(xs) < 12 or len(xs)/width < min_coverage:
            continue
        ys = np.array([np.median(rows[cols == x]) for x in xs])
        x_mm = xs*sx
        depth_mm = calibration.start_depth_mm + ys*sy
        fit = fit_sinusoid(x_mm, depth_mm, calibration.circumference_mm)
        serial += 1
        fid = f"{image_id}-F{serial:03d}"
        baseline = depth_mm - fit["residual"]
        profiles[fid] = np.column_stack((x_mm, depth_mm, baseline, fit["residual"]))
        records.append({"fracture_id": fid, "image_id": image_id, "borehole_id": borehole_id,
                        "amplitude_mm": fit["amplitude"], "period_mm": fit["period"],
                        "phase_rad": fit["phase"], "center_depth_mm": fit["center"],
                        "diameter_mm": calibration.diameter_mm,
                        "azimuth_offset_rad": calibration.azimuth_offset_rad,
                        "fit_r2": fit["fit_r2"], "rmse_mm": fit["rmse"],
                        "coverage": float(len(xs)/width),
                        "area_mm2": float(stats[label, cv2.CC_STAT_AREA]*sx*sy),
                        "profile_path": f"profiles/{fid}.csv"})
    return records, profiles
