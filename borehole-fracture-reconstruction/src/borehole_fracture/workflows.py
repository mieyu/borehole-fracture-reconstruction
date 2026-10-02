"""Shared orchestration for standalone capabilities and the complete image-to-network pipeline."""
from pathlib import Path
import numpy as np
import pandas as pd
from .contracts import load_manifest,load_boreholes
from .io import read_image,read_mask,write_mask,write_image,write_table,write_json
from .segmentation.detector import classical_mask,UNetPredictor
from .segmentation.postprocess import enhance
from .geometry.profiles import characterize,PARAMETER_COLUMNS,PROFILE_COLUMNS
from .roughness.jrc import analyze_profile,ROUGHNESS_COLUMNS
from .reconstruction.network import reconstruct,connection_scores
from .reconstruction.planning import recommend
from .reconstruction.visualization import render


def segment_manifest(manifest,output,model=None,threshold=.5):
    if not 0 < threshold < 1:
        raise ValueError("Segmentation threshold must lie strictly between zero and one")
    output = Path(output)
    predictor = UNetPredictor(model,threshold) if model else None
    records = []
    for item in load_manifest(manifest):
        image = read_image(item["path"])
        raw = predictor.predict(image) if predictor else classical_mask(image)
        repaired = enhance(raw)
        name = item["image_id"]
        write_mask(output/"raw"/f"{name}.png",raw)
        write_mask(output/"masks"/f"{name}.png",repaired)
        overlay = image.copy()
        overlay[repaired] = .4*overlay[repaired]+.6*np.array([70,90,230])
        write_image(output/"overlays"/f"{name}.png",overlay)
        records.append({"image_id":name,"height":image.shape[0],"width":image.shape[1],
                        "fracture_pixels":int(repaired.sum()),"backend":"unet" if model else "classical"})
    write_json(output/"segmentation.json",records)


def characterize_manifest(manifest,masks,output):
    output,masks = Path(output),Path(masks)
    records = []
    for item in load_manifest(manifest):
        mask = read_mask(masks/f"{item['image_id']}.png")
        image = read_image(item["path"])
        if mask.shape != image.shape[:2]:
            raise ValueError(f"Mask dimensions differ from source image: {item['image_id']}")
        instances,profiles = characterize(mask,item["calibration"],item["image_id"],item["borehole_id"])
        records.extend(instances)
        for fid,profile in profiles.items():
            write_table(output/"profiles"/f"{fid}.csv",profile,PROFILE_COLUMNS)
    write_table(output/"fracture_parameters.csv",records,PARAMETER_COLUMNS)
    return output/"fracture_parameters.csv"


def analyze_roughness(parameters,output,count=50,detrend=True,densities=(20,50,100,200)):
    parameters,output = Path(parameters),Path(output)
    df = pd.read_csv(parameters,dtype={"fracture_id":str,"borehole_id":str})
    rows,sensitivity = [],[]
    for row in df.itertuples():
        profile = pd.read_csv(parameters.parent/row.profile_path)
        rows.extend(analyze_profile(row.fracture_id,profile,count,detrend))
        for density in sorted(set(densities)):
            sensitivity.extend(analyze_profile(row.fracture_id,profile,density,detrend))
    result = pd.DataFrame(rows,columns=ROUGHNESS_COLUMNS)
    write_table(output/"sampling_comparison.csv",result)
    write_table(output/"density_sensitivity.csv",sensitivity,ROUGHNESS_COLUMNS)
    standard = result[result.sampling_method == "uniform"][["fracture_id","jrc","jrc_raw","z2","jrc_clipped"]]
    merged = df.merge(standard,on="fracture_id",how="left",validate="one_to_one")
    # Resolve copied profile paths relative to the new table, so individual stages remain composable.
    for source in df.itertuples():
        profile = pd.read_csv(parameters.parent/source.profile_path)
        write_table(output/source.profile_path,profile)
    write_table(output/"fracture_parameters_with_roughness.csv",merged)
    return output/"fracture_parameters_with_roughness.csv"


def reconstruct_network(parameters,boreholes,output,threshold=.75,scale_mm=1500.,
                        count=3,step_xy=250.,step_depth=500.,min_spacing_mm=250.,max_distance_mm=None):
    if not 0 <= threshold <= 1:
        raise ValueError("Connection threshold must lie in [0,1]")
    output = Path(output)
    holes = load_boreholes(boreholes)
    df = reconstruct(pd.read_csv(parameters,dtype={"borehole_id":str,"fracture_id":str}),holes)
    links = connection_scores(df,scale_mm=scale_mm,max_distance_mm=max_distance_mm)
    picks,grid = recommend(df,holes,count,step_xy,step_depth,min_spacing_mm)
    write_table(output/"fractures_3d.csv",df)
    write_table(output/"connections.csv",links)
    write_table(output/"high_score_connections.csv",links[links.connection_score >= threshold])
    write_table(output/"uncertainty_voxels.csv",grid)
    write_table(output/"highest_uncertainty_voxels.csv",grid.nlargest(100,"distance_to_nearest_plane_mm"))
    write_table(output/"recommended_boreholes.csv",picks)
    write_json(output/"summary.json",{"fractures":len(df),"cross_borehole_pairs":len(links),
                                    "high_score_connections":int((links.connection_score >= threshold).sum()),
                                    "recommended_boreholes":len(picks),"threshold":threshold,
                                    "distance_scale_mm":scale_mm,"world_coordinates":"right-handed Z-up; depth positive downward"})
    render(df,links,grid,holes,output,threshold)


def run_pipeline(manifest,boreholes,output,model=None,count=50):
    output = Path(output)
    segment_manifest(manifest,output/"segmentation",model)
    parameters = characterize_manifest(manifest,output/"segmentation"/"masks",output/"geometry")
    roughness = analyze_roughness(parameters,output/"roughness",count)
    reconstruct_network(roughness,boreholes,output/"reconstruction")
    write_json(output/"run.json",{"manifest":str(Path(manifest).resolve()),
                                  "boreholes":str(Path(boreholes).resolve()),
                                  "model":str(Path(model).resolve()) if model else None,
                                  "sample_count":count})
