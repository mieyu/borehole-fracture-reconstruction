"""Length-weighted Z2 and empirical JRC with raw and bounded values retained."""
import numpy as np
from .sampling import sample_profile, METHODS

ROUGHNESS_COLUMNS = ["fracture_id", "sampling_method", "sample_count", "detrended", "z2",
                     "jrc_raw", "jrc", "jrc_clipped", "profile_length_mm", "roughness_grade"]


def calculate(x, y):
    dx, dy = np.diff(x), np.diff(y)
    if len(dx) < 2 or np.any(dx <= 0):
        raise ValueError("Sample x coordinates must increase strictly")
    z2 = float(np.sqrt(np.sum((dy/dx)**2 * dx) / np.sum(dx)))
    raw = float(51.85*z2**0.6-10.37)
    bounded = float(np.clip(raw, 0, 20))
    grade = "smooth" if bounded < 6 else "moderate" if bounded < 14 else "rough"
    return {"z2": z2, "jrc_raw": raw, "jrc": bounded, "jrc_clipped": bool(raw < 0 or raw > 20),
            "profile_length_mm": float(np.sum(np.hypot(dx, dy))), "roughness_grade": grade}


def analyze_profile(fracture_id, profile, count=50, detrend=True):
    ordinate = profile.residual_mm.to_numpy() if detrend else profile.depth_mm.to_numpy()
    rows = []
    for method in METHODS:
        x, y = sample_profile(profile.x_mm.to_numpy(), ordinate, count, method)
        rows.append({"fracture_id": fracture_id, "sampling_method": method,
                     "sample_count": count, "detrended": detrend, **calculate(x,y)})
    return rows
