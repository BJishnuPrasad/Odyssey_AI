"""
src/processing/process_osm.py
------------------------------
Reprojects all four OSM GeoJSON layers (buildings, waterways, roads, landuse)
from WGS-84 to UTC 44N (EPSG:32644) and clips them to the Thanjavur boundary.

Reads  → data/raw/osm/*.geojson  OR  data/processed/osm/*.geojson
Writes → data/processed/osm/thanjavur_{layer}.geojson

Run
---
    python -m src.processing.process_osm
"""

from __future__ import annotations

import pathlib
import geopandas as gpd

from src.utils.config import cfg
from src.utils.logger import get_logger

log = get_logger(__name__)

LAYERS = {
    "buildings": cfg.files.buildings,
    "waterways": cfg.files.waterways,
    "roads":     cfg.files.roads,
    "landuse":   cfg.files.landuse,
}

TARGET_CRS = cfg.project.crs
OUT_DIR    = pathlib.Path(cfg.paths.processed.osm)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def process_layer(name: str, path: str) -> None:
    dest = OUT_DIR / f"thanjavur_{name}.geojson"

    # If the file was already placed in processed/ by extract_osm, use it in place.
    src_path = pathlib.Path(path)
    if not src_path.exists():
        log.warning("Layer '%s' not found at %s — skipping.", name, src_path)
        return

    log.info("Processing OSM layer: %s", name)
    gdf = gpd.read_file(src_path)

    # ── CRS fix ───────────────────────────────────────────────────────────────
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs(TARGET_CRS)

    # ── Clip to boundary ──────────────────────────────────────────────────────
    boundary = gpd.read_file(cfg.files.boundary).to_crs(TARGET_CRS)
    gdf = gpd.clip(gdf, boundary)

    # ── Save ──────────────────────────────────────────────────────────────────
    gdf.to_file(dest, driver="GeoJSON")
    log.info("  → %s  (%d features)", dest, len(gdf))


def run() -> None:
    for name, path in LAYERS.items():
        process_layer(name, path)
    log.info("OSM processing complete.")


if __name__ == "__main__":
    run()
