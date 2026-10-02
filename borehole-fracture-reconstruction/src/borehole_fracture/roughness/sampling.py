"""Uniform, adaptive and curvature-driven sampling of single-valued profiles."""
import numpy as np

METHODS = ("uniform", "adaptive", "curvature")


def sample_profile(x, y, count=50, method="uniform"):
    if count < 3 or method not in METHODS:
        raise ValueError("Need at least three samples and a supported sampling method")
    x, y = np.asarray(x, float), np.asarray(y, float)
    order = np.argsort(x)
    x, y = x[order], y[order]
    # Duplicate horizontal coordinates cannot define dy/dx: aggregate them first.
    unique = np.unique(x)
    y = np.array([np.mean(y[x == value]) for value in unique])
    x = unique
    if len(x) < 3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Profile needs three distinct finite x coordinates")
    if method == "uniform":
        query = np.linspace(x[0], x[-1], count)
    else:
        slope = np.gradient(y, x)
        indicator = np.abs(slope) if method == "adaptive" else np.abs(np.gradient(slope, x)) / (1+slope*slope)**1.5
        normalized = indicator / max(float(indicator.mean()), 1e-9)
        density = 1 + np.minimum(normalized, 10)
        cumulative = np.r_[0, np.cumsum(np.diff(x)*(density[1:]+density[:-1])/2)]
        query = np.interp(np.linspace(0, cumulative[-1], count), cumulative, x)
    return query, np.interp(query, x, y)
