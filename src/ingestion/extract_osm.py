"""
src/ingestion/extract_osm.py
----------------------------
Extracts OSM layers (buildings, waterways, roads, landuse) from the
southern-zone PBF file and saves them as GeoJSON in data/processed/osm/.

Requires: osmium-tool  OR  pyrosm  (pip install pyrosm)

Run
---
    python -m src.ingestion.extract_osm
"""

from __future__ import annotations

import pathlib
import geopandas as gpd
import pandas as pd

from src.utils.config import cfg
from src.utils.logger import get_logger

log = get_logger(__name__)


def extract_all() -> None:
    out_dir = pathlib.Path(cfg.paths.processed.osm)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Pyrosm Extraction (if available) ──────────────────────────────────────
    try:
        import pyrosm
        pbf_path = str(pathlib.Path(cfg.paths.root) / cfg.osm.pbf_source)

        # Clip to Thanjavur boundary to keep files small
        boundary = gpd.read_file(cfg.files.boundary).to_crs(cfg.project.geographic_crs)
        bbox = tuple(boundary.total_bounds)  # (minx, miny, maxx, maxy)

        log.info("Loading OSM PBF from %s (bbox=%s)", pbf_path, bbox)
        osm = pyrosm.OSM(pbf_path, bounding_box=bbox)

        # Buildings
        log.info("Extracting buildings …")
        buildings = osm.get_buildings()
        if buildings is not None:
            dest = out_dir / "thanjavur_buildings.geojson"
            buildings.to_file(dest, driver="GeoJSON")
            log.info("  → %s  (%d features)", dest, len(buildings))

        # Waterways
        log.info("Extracting waterways / water bodies …")
        try:
            natural = osm.get_natural()
            waterways = osm.get_waterways()
            water = gpd.pd.concat([natural, waterways], ignore_index=True) if natural is not None else waterways
        except Exception:
            water = osm.get_waterways()
        if water is not None:
            dest = out_dir / "thanjavur_waterways.geojson"
            water.to_file(dest, driver="GeoJSON")
            log.info("  → %s  (%d features)", dest, len(water))

        # Roads
        log.info("Extracting road network …")
        roads = osm.get_network(network_type="driving")
        if roads is not None:
            dest = out_dir / "thanjavur_roads.geojson"
            roads.to_file(dest, driver="GeoJSON")
            log.info("  → %s  (%d features)", dest, len(roads))

        # Landuse
        log.info("Extracting landuse …")
        landuse = osm.get_landuse()
        if landuse is not None:
            dest = out_dir / "thanjavur_landuse.geojson"
            landuse.to_file(dest, driver="GeoJSON")
            log.info("  → %s  (%d features)", dest, len(landuse))

        log.info("OSM extraction via pyrosm complete.")
        return
    except Exception as e:
        log.warning("pyrosm extraction failed or not installed: %s. Falling back to parsing GeoJSON.", e)

    # ── GeoPandas/GeoJSON Fallback ────────────────────────────────────────────
    # Look for raw/osm/thanjavur_osm_full.geojson or Data/export.geojson
    raw_paths = [
        "Data/raw/osm/thanjavur_osm_full.geojson",
        "Data/export.geojson",
        "data/raw/osm/thanjavur_osm_full.geojson",
        "data/export.geojson"
    ]
    raw_geojson = None
    for p in raw_paths:
        if pathlib.Path(p).exists():
            raw_geojson = p
            break
            
    if raw_geojson is None:
        log.error("OSM raw GeoJSON file not found. Checked: %s", raw_paths)
        raise FileNotFoundError("Raw OSM GeoJSON not found.")

    log.info("Loading raw OSM GeoJSON from %s (approx 40MB) …", raw_geojson)
    gdf = gpd.read_file(raw_geojson)
    log.info("Loaded %d OSM entities.", len(gdf))

    # Clip to boundary
    boundary = gpd.read_file(cfg.files.boundary).to_crs(gdf.crs)
    gdf = gpd.clip(gdf, boundary).reset_index(drop=True)

    # 1. Buildings
    log.info("Filtering buildings …")
    if "building" in gdf.columns:
        buildings = gdf[gdf["building"].notna() & (gdf["building"] != "no")]
        if len(buildings) > 0:
            dest = out_dir / "thanjavur_buildings.geojson"
            buildings.to_file(dest, driver="GeoJSON")
            log.info("  → %s  (%d features)", dest, len(buildings))
    else:
        log.warning("Property 'building' not found in raw GeoJSON, skipping buildings layer.")

    # 2. Waterways
    log.info("Filtering waterways and water areas …")
    water_mask = pd.Series([False] * len(gdf))
    if "waterway" in gdf.columns:
        water_mask = water_mask | gdf["waterway"].notna()
    if "natural" in gdf.columns:
        water_mask = water_mask | gdf["natural"].isin(["water", "wetland"])
    water = gdf[water_mask]
    if len(water) > 0:
        dest = out_dir / "thanjavur_waterways.geojson"
        water.to_file(dest, driver="GeoJSON")
        log.info("  → %s  (%d features)", dest, len(water))

    # 3. Roads
    log.info("Filtering roads …")
    if "highway" in gdf.columns:
        roads = gdf[gdf["highway"].notna() & (~gdf["highway"].isin(["platform", "footway", "cycleway", "pedestrian"]))]
        if len(roads) > 0:
            dest = out_dir / "thanjavur_roads.geojson"
            roads.to_file(dest, driver="GeoJSON")
            log.info("  → %s  (%d features)", dest, len(roads))

    # 4. Landuse
    log.info("Filtering landuse / parks / natural …")
    landuse_mask = pd.Series([False] * len(gdf))
    if "landuse" in gdf.columns:
        landuse_mask = landuse_mask | gdf["landuse"].notna()
    if "leisure" in gdf.columns:
        landuse_mask = landuse_mask | gdf["leisure"].notna()
    if "natural" in gdf.columns:
        landuse_mask = landuse_mask | gdf["natural"].notna()
    landuse = gdf[landuse_mask]
    if len(landuse) > 0:
        dest = out_dir / "thanjavur_landuse.geojson"
        landuse.to_file(dest, driver="GeoJSON")
        log.info("  → %s  (%d features)", dest, len(landuse))

    log.info("OSM extraction complete.")


if __name__ == "__main__":
    extract_all()
