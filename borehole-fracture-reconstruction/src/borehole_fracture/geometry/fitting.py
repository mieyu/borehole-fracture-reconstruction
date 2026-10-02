"""Fixed-circumference robust sinusoidal fit with physical coordinates."""
import numpy as np
from scipy.optimize import least_squares


def fit_sinusoid(x, y, period):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or not np.isfinite(x).all() or not np.isfinite(y).all() or period <= 0:
        raise ValueError("Fit needs at least three finite samples and a positive period")
    theta = 2*np.pi*x/period
    design = np.column_stack((np.sin(theta), np.cos(theta), np.ones(len(x))))
    if np.linalg.matrix_rank(design) < 3:
        raise ValueError("Profile does not span enough distinct circumferential positions")
    initial = np.linalg.lstsq(design, y, rcond=None)[0]
    scale = max(float(np.median(np.abs(y-design@initial))), 0.01)
    result = least_squares(lambda coefficients: design@coefficients-y, initial,
                           loss="soft_l1", f_scale=scale)
    a, b, c = result.x
    residual = y - design@result.x
    sst = np.sum((y-y.mean())**2)
    return {"amplitude": float(np.hypot(a,b)), "period": float(period),
            "phase": float(np.arctan2(b,a) % (2*np.pi)), "center": float(c),
            "fit_r2": float(1-np.sum(residual**2)/sst) if sst > 1e-12 else 0.0,
            "rmse": float(np.sqrt(np.mean(residual**2))), "residual": residual}
