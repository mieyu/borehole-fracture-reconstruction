"""Create deterministic synthetic borehole images and an analysis manifest."""
import argparse
from pathlib import Path
import cv2
import numpy as np
from borehole_fracture.io import write_image,write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path("outputs/demo_input"))
    a = p.parse_args()
    rng = np.random.default_rng(42)
    images,boreholes = [],[]
    for i in range(6):
        height,width = 512,256
        gray = np.clip(rng.normal(180,8,(height,width)),0,255).astype(np.uint8)
        gray = cv2.GaussianBlur(gray,(3,3),0)
        image = cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)
        x = np.arange(width)
        for center,amplitude,phase in [(140,20,.2+i*.05),(340,30,1+i*.05)]:
            y = center+amplitude*np.sin(2*np.pi*x/width+phase)+1.2*np.sin(18*np.pi*x/width)
            points = np.column_stack((x,np.rint(y))).astype(np.int32)
            cv2.polylines(image,[points],False,(45,45,45),3)
        bid,name = f"B{i+1:02d}",f"scan_{i+1:02d}"
        write_image(a.output/"images"/f"{name}.png",image)
        images.append({"image_id":name,"borehole_id":bid,"path":f"images/{name}.png",
                       "calibration":{"start_depth_mm":1000+i*20}})
        boreholes.append({"borehole_id":bid,"mouth_mm":[(i%3)*1000,(i//3)*1000,0],"depth_mm":7000})
    write_json(a.output/"manifest.json",{"calibration":{"diameter_mm":30,"interval_mm":1000},"images":images})
    write_json(a.output/"boreholes.json",{"boreholes":boreholes})
    print(a.output.resolve())


if __name__ == "__main__":
    main()
