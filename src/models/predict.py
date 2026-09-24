"""
src/models/predict.py
---------------------
Loads trained model + scaler and generates a probability suitability map,
exported as both:
  outputs/exports/suitability_map.tif
  outputs/maps/suitability_map.png

Run
---
    python -m src.models.predict
"""

from __future__ import annotations

import pathlib
import pickle

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
from scipy.interpolate import griddata

from src.utils.config import cfg
from src.utils.logger import get_logger

log = get_logger(__name__)

FEATURE_COLS = ["elevation", "slope", "dist_water", "dist_road", "dist_building", "landuse_code"]

OUT_EXPORTS = pathlib.Path(cfg.paths.outputs.exports)
OUT_MAPS    = pathlib.Path(cfg.paths.outputs.maps)
OUT_EXPORTS.mkdir(parents=True, exist_ok=True)
OUT_MAPS.mkdir(parents=True, exist_ok=True)


def predict() -> None:
    # ── Load artefacts ────────────────────────────────────────────────────────
    with open(OUT_EXPORTS.parent.parent / "outputs/models/random_forest.pkl", "rb") as f:
        clf = pickle.load(f)
    with open(OUT_EXPORTS.parent.parent / "outputs/models/scaler.pkl", "rb") as f:
        scaler = pickle.load(f)

    # ── Load full feature table (including unlabelled rows) ───────────────────
    df = pd.read_csv(cfg.files.site_features).dropna(subset=FEATURE_COLS)
    X  = scaler.transform(df[FEATURE_COLS].values)

    log.info("Predicting suitability for %d points …", len(df))
    proba = clf.predict_proba(X)[:, 1]
    df["probability"] = proba

    # ── Interpolate to raster grid ────────────────────────────────────────────
    boundary = gpd.read_file(cfg.files.boundary).to_crs(cfg.project.crs)
    minx, miny, maxx, maxy = boundary.total_bounds

    res = 250  # metres
    grid_x, grid_y = np.mgrid[minx:maxx:res, miny:maxy:res]
    grid_z = griddata(
        points=df[["x", "y"]].values,
        values=proba,
        xi=(grid_x, grid_y),
        method="linear",
    )

    # ── Write GeoTIFF ─────────────────────────────────────────────────────────
    tif_path = OUT_EXPORTS / "suitability_map.tif"
    h, w = grid_z.shape
    transform = from_bounds(minx, miny, maxx, maxy, w, h)
    with rasterio.open(
        tif_path, "w", driver="GTiff",
        height=h, width=w, count=1, dtype="float32",
        crs=cfg.project.crs, transform=transform, compress="lzw",
    ) as dst:
        dst.write(grid_z.astype(np.float32), 1)
    log.info("Suitability GeoTIFF → %s", tif_path)

    # ── Quick-look PNG ────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(grid_z.T, origin="lower", cmap="RdYlGn",
                   extent=[minx, maxx, miny, maxy], vmin=0, vmax=1)
    boundary.boundary.plot(ax=ax, color="black", linewidth=0.8)
    plt.colorbar(im, ax=ax, label="Archaeological Site Suitability (probability)")
    ax.set_title("Thanjavur – Site Suitability Map", fontsize=14)
    ax.set_xlabel("Easting (m)"); ax.set_ylabel("Northing (m)")
    png_path = OUT_MAPS / "suitability_map.png"
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Suitability PNG → %s", png_path)


if __name__ == "__main__":
    predict()
