"""Physical plane reconstruction and explainable cross-borehole connection scores."""
import numpy as np
import pandas as pd

LINK_COLUMNS = ["source_id", "target_id", "source_borehole", "target_borehole", "distance_mm",
                "distance_score", "orientation_score", "roughness_score", "connection_score"]


def reconstruct(parameters, boreholes):
    required = {"fracture_id", "borehole_id", "amplitude_mm", "phase_rad", "center_depth_mm", "diameter_mm", "jrc"}
    missing = required - set(parameters.columns)
    if missing:
        raise ValueError(f"Parameter table missing columns: {sorted(missing)}")
    df = parameters.copy()
    if df.empty:
        raise ValueError("No fracture instances to reconstruct")
    if df.fracture_id.isna().any() or df.fracture_id.duplicated().any():
        raise ValueError("fracture_id must be nonempty and unique")
    df.borehole_id = df.borehole_id.astype(str)
    numeric = ["amplitude_mm", "phase_rad", "center_depth_mm", "diameter_mm", "jrc"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="raise")
    if not np.isfinite(df[numeric].to_numpy()).all():
        raise ValueError("Parameter values must be finite")
    if (df.diameter_mm <= 0).any() or (df.amplitude_mm < 0).any() or not df.jrc.between(0,20).all():
        raise ValueError("Diameter must be positive, amplitude nonnegative and JRC in [0,20]")
    if "azimuth_offset_rad" not in df:
        df["azimuth_offset_rad"] = 0.0
    df.azimuth_offset_rad = pd.to_numeric(df.azimuth_offset_rad, errors="raise")
    if not np.isfinite(df.azimuth_offset_rad.to_numpy()).all():
        raise ValueError("Azimuth offsets must be finite")
    centers = []
    for row in df.itertuples():
        if row.borehole_id not in boreholes:
            raise ValueError(f"Unknown borehole: {row.borehole_id}")
        hole = boreholes[row.borehole_id]
        if not 0 <= row.center_depth_mm <= hole["depth_mm"]:
            raise ValueError(f"Fracture outside borehole depth: {row.fracture_id}")
        centers.append(np.array(hole["mouth_mm"]) + [0,0,-row.center_depth_mm])
    df[["x_mm", "y_mm", "z_mm"]] = np.array(centers)
    phase = df.phase_rad.to_numpy() - df.azimuth_offset_rad.to_numpy()
    ratio = df.amplitude_mm.to_numpy() / (df.diameter_mm.to_numpy()/2)
    # Cylinder intersection: depth=C+R sin(theta+phase). World Z increases upward.
    normal = np.column_stack((ratio*np.sin(phase), ratio*np.cos(phase), np.ones(len(df))))
    normal /= np.linalg.norm(normal, axis=1)[:,None]
    df[["nx", "ny", "nz"]] = normal
    df["dip_deg"] = np.degrees(np.arctan(ratio))
    df["dip_direction_deg"] = np.degrees(np.mod(np.pi/2-phase, 2*np.pi))
    return df


def connection_scores(df, scale_mm=1500.0, weights=(0.5,0.3,0.2), max_distance_mm=None):
    if scale_mm <= 0 or len(weights) != 3 or min(weights) < 0 or not np.isclose(sum(weights), 1):
        raise ValueError("Use a positive distance scale and three nonnegative weights summing to one")
    if max_distance_mm is not None and max_distance_mm <= 0:
        raise ValueError("Maximum distance must be positive")
    ids, holes = df.fracture_id.to_numpy(), df.borehole_id.to_numpy()
    centers, normals = df[["x_mm","y_mm","z_mm"]].to_numpy(), df[["nx","ny","nz"]].to_numpy()
    jrc = df.jrc.to_numpy()
    rows = []
    for i in range(len(df)):
        candidates = np.flatnonzero((np.arange(len(df)) > i) & (holes != holes[i]))
        for j in candidates:
            distance = float(np.linalg.norm(centers[i]-centers[j]))
            if max_distance_mm is not None and distance > max_distance_mm:
                continue
            sd = float(np.exp(-(distance/scale_mm)**2))
            sa = float(np.clip(abs(normals[i]@normals[j]), 0, 1))
            sj = float(np.clip(1-abs(jrc[i]-jrc[j])/20, 0, 1))
            score = weights[0]*sd+weights[1]*sa+weights[2]*sj
            rows.append([ids[i],ids[j],holes[i],holes[j],distance,sd,sa,sj,score])
    return pd.DataFrame(rows, columns=LINK_COLUMNS).sort_values("connection_score", ascending=False)
