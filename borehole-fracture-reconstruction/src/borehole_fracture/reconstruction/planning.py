"""Finite-domain geometric uncertainty and greedy supplementary borehole selection."""
import numpy as np
import pandas as pd

PLANNING_COLUMNS = ["priority", "mouth_x_mm", "mouth_y_mm", "mouth_z_mm", "depth_mm", "uncertainty_reduction_sum_mm"]


def uncertainty_grid(fractures, boreholes, step_xy=250.0, step_depth=500.0):
    if step_xy <= 0 or step_depth <= 0:
        raise ValueError("Grid spacing must be positive")
    mouths = np.array([b["mouth_mm"] for b in boreholes.values()])
    if not np.allclose(mouths[:,2], mouths[0,2]):
        raise ValueError("Planning requires borehole mouths on a common elevation")
    xs = np.arange(mouths[:,0].min(), mouths[:,0].max()+1e-6, step_xy)
    ys = np.arange(mouths[:,1].min(), mouths[:,1].max()+1e-6, step_xy)
    depth = max(b["depth_mm"] for b in boreholes.values())
    zs = np.arange(0, depth+1e-6, step_depth)
    if len(xs)*len(ys)*len(zs) > 2_000_000:
        raise ValueError("Grid exceeds two million voxels; increase spacing")
    points = np.stack(np.meshgrid(xs,ys,mouths[0,2]-zs,indexing="ij"),axis=-1).reshape(-1,3)
    distance = np.full(len(points), np.inf)
    for row in fractures.itertuples():
        center, normal = np.array([row.x_mm,row.y_mm,row.z_mm]), np.array([row.nx,row.ny,row.nz])
        distance = np.minimum(distance, np.abs((points-center)@normal))
    result = pd.DataFrame(points,columns=["x_mm","y_mm","z_mm"])
    result["distance_to_nearest_plane_mm"] = distance
    return result, xs, ys


def recommend(fractures, boreholes, count=3, step_xy=250.0, step_depth=500.0, min_spacing_mm=250.0):
    if count < 1 or min_spacing_mm <= 0:
        raise ValueError("Candidate count and minimum spacing must be positive")
    grid, xs, ys = uncertainty_grid(fractures,boreholes,step_xy,step_depth)
    points = grid[["x_mm","y_mm","z_mm"]].to_numpy()
    distance = grid.distance_to_nearest_plane_mm.to_numpy().copy()
    existing = [b["mouth_mm"][:2] for b in boreholes.values()]
    elevation = next(iter(boreholes.values()))["mouth_mm"][2]
    depth = max(b["depth_mm"] for b in boreholes.values())
    rows = []
    for rank in range(1,count+1):
        best = None
        for x in xs:
            for y in ys:
                if any(np.hypot(x-a,y-b) < min_spacing_mm for a,b in existing):
                    continue
                proxy = np.hypot(points[:,0]-x,points[:,1]-y)
                gain = float(np.maximum(distance-proxy,0).sum())
                if best is None or gain > best[0]:
                    best = gain,float(x),float(y),proxy
        if best is None or best[0] <= 1e-9:
            break
        gain,x,y,proxy = best
        rows.append([rank,x,y,elevation,depth,gain])
        distance = np.minimum(distance,proxy)
        existing.append([x,y])
    return pd.DataFrame(rows,columns=PLANNING_COLUMNS),grid
