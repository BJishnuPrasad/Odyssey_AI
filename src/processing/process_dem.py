"""
src/processing/process_dem.py
------------------------------
Step 1 of the processing pipeline.

Reads  → data/raw/dem/output_SRTMGL1.tif
Writes → data/processed/dem/thanjavur_dem.tif   (clipped, reprojected)
         data/processed/dem/thanjavur_slope.tif  (slope in degrees)

Run
---
    python -m src.processing.process_dem
"""

from __future__ import annotations

import pathlib
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject
import richdem as rd

try:
    import richdem as rd
except ImportError:
    rd = None

from src.utils.config import cfg
from src.utils.logger import get_logger

log = get_logger(__name__)

OUT_DIR = pathlib.Path(cfg.paths.processed.dem)
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CRS = CRS.from_epsg(int(cfg.project.crs.split(":")[1]))


def clip_and_reproject() -> pathlib.Path:
    """Clip raw DEM to Thanjavur boundary and reproject to UTM 44N."""
    boundary = gpd.read_file(cfg.files.boundary).to_crs(cfg.project.geographic_crs)
    geoms = [geom.__geo_interface__ for geom in boundary.geometry]

    src_path  = pathlib.Path(cfg.files.raw_dem)
    dest_path = OUT_DIR / "thanjavur_dem.tif"

    log.info("Clipping & reprojecting DEM …")
    with rasterio.open(src_path) as src:
        out_img, out_transform = mask(src, geoms, crop=True)
        out_meta = src.meta.copy()

    # Reproject clipped image to UTM
    transform, width, height = calculate_default_transform(
        src.crs, TARGET_CRS, out_img.shape[-1], out_img.shape[-2],
        *rasterio.transform.array_bounds(out_img.shape[-2], out_img.shape[-1], out_transform)
    )
    out_meta.update({
        "crs": TARGET_CRS,
        "transform": transform,
        "width": width,
        "height": height,
        "driver": "GTiff",
        "compress": "lzw",
        "nodata": -9999,
    })

    data_reproj = np.empty((1, height, width), dtype=np.float32)
    reproject(
        source=out_img,
        destination=data_reproj,
        src_transform=out_transform,
        src_crs=src.crs,
        dst_transform=transform,
        dst_crs=TARGET_CRS,
        resampling=Resampling.bilinear,
    )

    with rasterio.open(dest_path, "w", **out_meta) as dst:
        dst.write(data_reproj)

    log.info("DEM written → %s", dest_path)
    return dest_path


def compute_slope(dem_path: pathlib.Path) -> pathlib.Path:
    """Compute slope (degrees) from the processed DEM using RichDEM (or NumPy fallback)."""
    dest_path = OUT_DIR / "thanjavur_slope.tif"
    log.info("Computing slope …")

    with rasterio.open(dem_path) as src:
        arr = src.read(1)
        profile = src.profile.copy()
        res_x, res_y = src.res

    slope_data = None
    if rd is not None:
        try:
            log.info("Using richdem to calculate slope...")
            arr_double = arr.astype(np.float64)
            dem_rd = rd.rdarray(arr_double, no_data=-9999)
            slope = rd.TerrainAttribute(dem_rd, attrib="slope_degrees")
            slope_data = slope.astype(np.float32)
        except Exception as e:
            log.warning("richdem calculation failed: %s. Falling back to NumPy.", e)
            slope_data = None

    if slope_data is None:
        log.info("Using Horn's method (NumPy) to calculate slope...")
        # Horn's method
        z = np.pad(arr, pad_width=1, mode='edge')
        # dz/dx = ((z_tr + 2*z_mr + z_br) - (z_tl + 2*z_ml + z_bl)) / (8 * res_x)
        dz_dx = ((z[:-2, 2:] + 2*z[1:-1, 2:] + z[2:, 2:]) - 
                 (z[:-2, :-2] + 2*z[1:-1, :-2] + z[2:, :-2])) / (8.0 * res_x)
        # dz/dy = ((z_bl + 2*z_bc + z_br) - (z_tl + 2*z_tc + z_tr)) / (8 * res_y)
        dz_dy = ((z[2:, :-2] + 2*z[2:, 1:-1] + z[2:, 2:]) - 
                 (z[:-2, :-2] + 2*z[:-2, 1:-1] + z[:-2, 2:])) / (8.0 * res_y)
        slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
        slope_deg = np.degrees(slope_rad)
        # Preserve nodata or set to 0 where DEM is nodata
        slope_deg[arr == -9999] = -9999
        slope_data = slope_deg.astype(np.float32)

    profile.update(dtype=rasterio.float32, count=1, compress="lzw")
    with rasterio.open(dest_path, "w", **profile) as dst:
        dst.write(slope_data, 1)

    log.info("Slope written → %s", dest_path)
    return dest_path


def run() -> None:
    dem_path = clip_and_reproject()
    compute_slope(dem_path)
    log.info("DEM processing complete.")


if __name__ == "__main__":
    run()
