"""Standalone figures for fracture networks and spatial uncertainty."""
from pathlib import Path
import numpy as np


def render(fractures, links, grid, boreholes, output, threshold=0.75):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    fig = plt.figure(figsize=(11,9))
    ax = fig.add_subplot(111,projection="3d")
    for bid,hole in boreholes.items():
        x,y,z = hole["mouth_mm"]
        ax.plot([x,x],[y,y],[z,z-hole["depth_mm"]],"--",color="gray")
        ax.text(x,y,z,bid)
    for row in fractures.itertuples():
        center,n = np.array([row.x_mm,row.y_mm,row.z_mm]),np.array([row.nx,row.ny,row.nz])
        reference = [0,0,1] if abs(n[2]) < .9 else [1,0,0]
        u = np.cross(n,reference);u /= np.linalg.norm(u)
        v = np.cross(n,u)
        theta = np.linspace(0,2*np.pi,32)
        ring = center+150*(np.cos(theta)[:,None]*u+np.sin(theta)[:,None]*v)
        ax.plot(*ring.T,color="#276da8",alpha=.6,linewidth=.8)
    centers = fractures.set_index("fracture_id")[["x_mm","y_mm","z_mm"]]
    for row in links[links.connection_score >= threshold].itertuples():
        pair = np.vstack((centers.loc[row.source_id],centers.loc[row.target_id]))
        ax.plot(*pair.T,color="#de5b46",alpha=.65,linewidth=row.connection_score*2)
    ax.set(xlabel="X / mm",ylabel="Y / mm",zlabel="Z / mm",title="Fracture network and connection scores")
    fig.tight_layout();fig.savefig(output/"fracture_network_3d.png",dpi=180);plt.close(fig)
    heat = grid.groupby(["y_mm","x_mm"]).distance_to_nearest_plane_mm.mean().unstack()
    fig,ax = plt.subplots(figsize=(9,5))
    # pcolormesh also handles one-row or one-column domains without singular extents.
    im = ax.pcolormesh(heat.columns,heat.index,heat.to_numpy(),shading="nearest",cmap="viridis")
    for bid,hole in boreholes.items():
        x,y,_ = hole["mouth_mm"]
        ax.scatter(x,y,c="white",edgecolors="black")
        ax.annotate(bid,(x,y),xytext=(3,3),textcoords="offset points")
    ax.set(xlabel="X / mm",ylabel="Y / mm",title="Mean geometric uncertainty over depth")
    fig.colorbar(im,ax=ax,label="Distance to nearest fracture plane / mm")
    fig.tight_layout();fig.savefig(output/"uncertainty_map.png",dpi=180);plt.close(fig)
