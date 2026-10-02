"""Shared physical calibration and file formats used by all four capabilities."""
from dataclasses import dataclass
from pathlib import Path
import json
import math


@dataclass(frozen=True)
class Calibration:
    diameter_mm: float = 30.0
    interval_mm: float = 500.0
    start_depth_mm: float = 0.0
    azimuth_offset_rad: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.diameter_mm, self.interval_mm,
                                              self.start_depth_mm, self.azimuth_offset_rad)):
            raise ValueError("Calibration values must be finite")
        if self.diameter_mm <= 0 or self.interval_mm <= 0 or self.start_depth_mm < 0:
            raise ValueError("Diameter/interval must be positive; start depth must be nonnegative")

    @property
    def circumference_mm(self):
        return math.pi * self.diameter_mm


def load_manifest(path):
    """Resolve image paths relative to a manifest; allow per-image calibration."""
    path = Path(path).resolve()
    obj = json.loads(path.read_text(encoding="utf-8"))
    common = obj.get("calibration", {})
    rows, identifiers = [], set()
    for item in obj.get("images", []):
        image_id = str(item["image_id"])
        if not image_id or image_id in identifiers or Path(image_id).name != image_id or image_id in (".", ".."):
            raise ValueError("image_id must be a unique, nonempty filename-safe identifier")
        identifiers.add(image_id)
        image = (path.parent / item["path"]).resolve()
        if not image.is_file():
            raise FileNotFoundError(image)
        rows.append({"image_id": image_id, "borehole_id": str(item["borehole_id"]),
                     "path": image, "calibration": Calibration(**(common | item.get("calibration", {})))})
    if not rows:
        raise ValueError("Manifest must contain at least one image")
    return rows


def load_boreholes(path):
    """All mouths use a right-handed Z-up world coordinate system; depth is positive downward."""
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    result = {}
    for row in obj["boreholes"]:
        bid = str(row["borehole_id"])
        xyz = [float(v) for v in row["mouth_mm"]]
        depth = float(row["depth_mm"])
        if bid in result or not bid or len(xyz) != 3 or depth <= 0 or not all(map(math.isfinite, xyz + [depth])):
            raise ValueError("Boreholes need unique IDs, three finite mouth coordinates and positive depth")
        result[bid] = {"mouth_mm": xyz, "depth_mm": depth}
    if not result:
        raise ValueError("At least one borehole is required")
    return result
