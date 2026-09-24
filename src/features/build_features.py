"""
src/features/build_features.py
-------------------------------
Builds the ML feature table that is saved to
    data/processed/features/site_features.csv

Each row = one candidate point / grid cell.
Columns (features):
  elevation        – metres (from DEM)
  slope            – degrees
  dist_water       – distance to nearest waterway (m)
  dist_road        – distance to nearest road (m)
  dist_building    – distance to nearest building (m)
  landuse_code     – dominant landuse category (label-encoded)
  ndvi             – optional, from Sentinel-2
  label            – 1 = known site, 0 = background (if ground truth supplied)

Run
---
    python -m src.features.build_features
"""

from __future__ import annotations

import pathlib
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.sample import sample_gen

from src.utils.config import cfg
from src.utils.logger import get_logger

warnings.filterwarnings("ignore", category=FutureWarning)
log = get_logger(__name__)

TARGET_CRS = cfg.project.crs
OUT_DIR    = pathlib.Path(cfg.paths.processed.features)
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _sample_raster(raster_path: str, points_gdf: gpd.GeoDataFrame) -> np.ndarray:
    """Return a 1-D array of raster values sampled at each point."""
    coords = [(geom.x, geom.y) for geom in points_gdf.geometry]
    with rasterio.open(raster_path) as src:
        values = [v[0] for v in src.sample(coords)]
    return np.array(values, dtype=np.float32)


def _distance_to_layer(points_gdf: gpd.GeoDataFrame, layer_path: str) -> np.ndarray:
    """Return Euclidean distance (m) from each point to the nearest feature."""
    layer = gpd.read_file(layer_path).to_crs(TARGET_CRS)
    merged = layer.geometry.unary_union
    return points_gdf.geometry.distance(merged).values.astype(np.float32)


def _encode_landuse(points_gdf: gpd.GeoDataFrame, landuse_path: str) -> np.ndarray:
    """Spatial join to assign dominant landuse code to each point."""
    landuse = gpd.read_file(landuse_path).to_crs(TARGET_CRS)
    if "landuse" not in landuse.columns:
        landuse["landuse"] = landuse.get("leisure", landuse.get("natural", "unknown"))
    joined = gpd.sjoin(points_gdf[["geometry"]], landuse[["geometry", "landuse"]],
                       how="left", predicate="within")
    codes  = pd.Categorical(joined["landuse"]).codes.astype(np.int16)
    return codes


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def build(sample_spacing_m: float = 250.0) -> pd.DataFrame:
    """
    Create a regular grid of sample points across Thanjavur, extract features
    from each layer, and return (and save) the feature DataFrame.

    Parameters
    ----------
    sample_spacing_m : float
        Grid spacing in metres.  250 m ≈ 240 k points across Thanjavur district.
    """
    log.info("Loading boundary …")
    boundary = gpd.read_file(cfg.files.boundary).to_crs(TARGET_CRS)

    # ── Build point grid ──────────────────────────────────────────────────────
    log.info("Creating %.0f m sample grid …", sample_spacing_m)
    minx, miny, maxx, maxy = boundary.total_bounds
    xs = np.arange(minx, maxx, sample_spacing_m)
    ys = np.arange(miny, maxy, sample_spacing_m)
    xv, yv = np.meshgrid(xs, ys)
    from shapely.geometry import Point
    pts = [Point(x, y) for x, y in zip(xv.ravel(), yv.ravel())]
    points_gdf = gpd.GeoDataFrame(geometry=pts, crs=TARGET_CRS)

    # ── Clip to boundary ──────────────────────────────────────────────────────
    points_gdf = gpd.clip(points_gdf, boundary).reset_index(drop=True)
    log.info("  %d sample points inside boundary.", len(points_gdf))

    # ── Extract features ──────────────────────────────────────────────────────
    df = pd.DataFrame()
    df["x"] = points_gdf.geometry.x
    df["y"] = points_gdf.geometry.y

    log.info("Sampling DEM …")
    df["elevation"] = _sample_raster(cfg.files.dem_processed, points_gdf)

    log.info("Sampling slope …")
    df["slope"] = _sample_raster(cfg.files.slope, points_gdf)

    log.info("Computing distance to waterways …")
    df["dist_water"] = _distance_to_layer(points_gdf, cfg.files.waterways)

    log.info("Computing distance to roads …")
    df["dist_road"] = _distance_to_layer(points_gdf, cfg.files.roads)

    log.info("Computing distance to buildings …")
    df["dist_building"] = _distance_to_layer(points_gdf, cfg.files.buildings)

    log.info("Encoding landuse …")
    df["landuse_code"] = _encode_landuse(points_gdf, cfg.files.landuse)

    # ── Label Generation from Known Archaeological Sites ──────────────────────
    log.info("Generating labels from known archaeological sites …")
    known_sites_paths = [
        "Data/raw/osm/thanjavur_osm_alt.geojson",
        "Data/export (1).geojson",
        "data/raw/osm/thanjavur_osm_alt.geojson",
        "data/export (1).geojson"
    ]
    known_gdf = None
    for p in known_sites_paths:
        if pathlib.Path(p).exists():
            known_gdf = gpd.read_file(p).to_crs(TARGET_CRS)
            break

    df["label"] = -1
    if known_gdf is not None:
        log.info("Loaded %d known archaeological sites.", len(known_gdf))
        merged_sites = known_gdf.geometry.unary_union
        dists = points_gdf.geometry.distance(merged_sites).values
        
        # Buffer of 750 meters around any archaeological site -> label = 1
        pos_mask = dists <= 750.0
        df.loc[pos_mask, "label"] = 1
        num_pos = pos_mask.sum()
        log.info("Found %d positive candidate grid cells.", num_pos)
        
        # Background points further than 3000 meters -> label = 0 (pseudo-absences)
        neg_candidate_mask = dists >= 3000.0
        if num_pos > 0:
            neg_indices = np.where(neg_candidate_mask)[0]
            np.random.seed(42)
            np.random.shuffle(neg_indices)
            # Sample 10x negatives for class balance
            num_neg = min(len(neg_indices), num_pos * 10)
            neg_selected = neg_indices[:num_neg]
            df.loc[neg_selected, "label"] = 0
            log.info("Labelled %d negative cells (1:10 ratio)", num_neg)
        else:
            log.warning("No positive cells found inside the boundary for labeling.")
    else:
        log.warning("Known archaeological sites GeoJSON not found. Running with all labels as -1.")

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = pathlib.Path(cfg.files.site_features)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    log.info("Feature table saved → %s  (%d rows × %d cols)", out_path, len(df), len(df.columns))
    return df


if __name__ == "__main__":
    build()
