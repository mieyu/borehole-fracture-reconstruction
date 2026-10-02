"""CLI with named requirements and a complete analysis pipeline."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="borehole-fracture",description="Borehole fracture identification, characterization and 3D reconstruction")
    subs = parser.add_subparsers(dest="command",required=True)
    p = subs.add_parser("segment",help="Identify fracture pixels and enhance continuity")
    p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--model",type=Path);p.add_argument("--threshold",type=float,default=.5)
    p = subs.add_parser("characterize",help="Cluster fractures and fit physical geometric parameters")
    p.add_argument("manifest",type=Path);p.add_argument("--masks",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p = subs.add_parser("roughness",help="Calculate JRC and compare sampling strategies")
    p.add_argument("parameters",type=Path);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--samples",type=int,default=50);p.add_argument("--keep-trend",action="store_true")
    p = subs.add_parser("reconstruct",help="Build a fracture network and rank exploration positions")
    p.add_argument("parameters",type=Path);p.add_argument("--boreholes",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--threshold",type=float,default=.75)
    p.add_argument("--distance-scale",type=float,default=1500.);p.add_argument("--max-distance",type=float)
    p.add_argument("--count",type=int,default=3);p.add_argument("--grid-xy",type=float,default=250.)
    p.add_argument("--grid-depth",type=float,default=500.);p.add_argument("--min-spacing",type=float,default=250.)
    p = subs.add_parser("run",help="Analyze borehole images through all four capabilities")
    p.add_argument("manifest",type=Path);p.add_argument("--boreholes",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--model",type=Path)
    p.add_argument("--samples",type=int,default=50)
    p = subs.add_parser("train",help="Train U-Net with source-group separation and paired augmentation")
    p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--epochs",type=int,default=100);p.add_argument("--batch-size",type=int,default=4)
    p.add_argument("--height",type=int,default=512);p.add_argument("--width",type=int,default=256)
    p.add_argument("--seed",type=int,default=42)
    p = subs.add_parser("evaluate",help="Evaluate fracture masks with foreground IoU and Dice")
    p.add_argument("predictions",type=Path);p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a = parser.parse_args()
    try:
        if a.command == "train":
            from .segmentation.training import train
            train(a.manifest,a.output,a.epochs,a.batch_size,a.height,a.width,a.seed)
        elif a.command == "evaluate":
            from .io import read_mask,write_table
            from .segmentation.evaluation import metrics
            rows = [{"image_id":p.stem,**metrics(read_mask(p),read_mask(a.reference/p.name))}
                    for p in sorted(a.predictions.glob("*.png")) if not p.name.startswith(".")]
            if not rows:
                raise ValueError("Prediction directory contains no PNG masks")
            write_table(a.output,rows)
        else:
            from . import workflows as w
            if a.command == "segment":w.segment_manifest(a.manifest,a.output,a.model,a.threshold)
            elif a.command == "characterize":w.characterize_manifest(a.manifest,a.masks,a.output)
            elif a.command == "roughness":w.analyze_roughness(a.parameters,a.output,a.samples,not a.keep_trend)
            elif a.command == "reconstruct":w.reconstruct_network(a.parameters,a.boreholes,a.output,a.threshold,
                    a.distance_scale,a.count,a.grid_xy,a.grid_depth,a.min_spacing,a.max_distance)
            elif a.command == "run":w.run_pipeline(a.manifest,a.boreholes,a.output,a.model,a.samples)
    except (ValueError,FileNotFoundError,KeyError) as error:
        parser.error(str(error))
    print(f"Saved: {a.output.resolve()}")
