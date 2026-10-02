"""Unicode-safe image I/O and auditable tabular outputs."""
from pathlib import Path
import json
import cv2
import numpy as np
import pandas as pd


def read_image(path, grayscale=False):
    image = cv2.imdecode(np.fromfile(Path(path), dtype=np.uint8),
                         cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot decode image: {path}")
    return image


def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix, image)
    if not ok:
        raise ValueError(f"Cannot encode image: {path}")
    encoded.tofile(path)


def read_mask(path):
    """On disk, fracture pixels are black. Internally, True always means fracture."""
    return read_image(path, grayscale=True) < 128


def write_mask(path, mask):
    write_image(path, np.where(mask, 0, 255).astype(np.uint8))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_table(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, columns=columns)
    df.to_csv(path, index=False, encoding="utf-8-sig")
