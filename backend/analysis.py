"""Exploratory terrain screening. This is not a trained storage model."""
import json
import math
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask, rasterize, shapes
from rasterio.transform import from_origin, rowcol
from rasterio.warp import reproject, calculate_default_transform
from scipy.ndimage import uniform_filter, minimum_filter, distance_transform_edt
from PIL import Image
from shapely.geometry import mapping, shape
from .catalog import boundary, project, read_json, curated_sites, checksum, inventory, feature_collection
from .settings import DEM, BOUNDARY, SITES, DERIVED, CRS, METHOD_VERSION, ROOT

NODATA = -9999.0
LABELS = {1: "Low", 2: "Moderate", 3: "High", 4: "Insufficient data"}
COLORS = {0: (0, 0, 0, 0), 1: (224, 146, 111, 205), 2: (228, 192, 106, 210),
          3: (49, 137, 119, 215), 4: (132, 146, 162, 170)}


def terrain_indicators(elevation, resolution):
    """Use metre spacing and reject invalid neighbours before scoring."""
    finite = np.isfinite(elevation)
    valid = minimum_filter(finite.astype(np.uint8), size=3, mode="constant", cval=0).astype(bool)
    dy, dx = np.gradient(np.where(finite, elevation, 0.0), resolution, resolution)
    slope = np.degrees(np.arctan(np.hypot(dx, dy)))
    slope[~valid] = np.nan
    size = max(3, 2 * round(1000 / resolution) + 1)
    coverage = uniform_filter(finite.astype(float), size=size, mode="constant")
    mean = uniform_filter(np.where(finite, elevation, 0.0), size=size, mode="constant") / np.maximum(coverage, 1e-9)
    valid &= coverage >= 0.8
    relative = mean - elevation
    flatness = np.exp(-slope / 5.0)
    lower_position = np.clip(0.5 + relative / 10.0, 0.0, 1.0)
    return slope, relative, flatness, lower_position, valid


def classify(score, valid, inside):
    classes = np.zeros(score.shape, dtype=np.uint8)
    classes[inside] = 4
    classes[inside & valid & (score < 0.4)] = 1
    classes[inside & valid & (score >= 0.4) & (score < 0.65)] = 2
    classes[inside & valid & (score >= 0.65)] = 3
    return classes


def sample_value(array, row, col):
    if not (0 <= row < array.shape[0] and 0 <= col < array.shape[1]):
        return None
    value = float(array[row, col])
    return round(value, 4) if np.isfinite(value) and value != NODATA else None


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")


def execute(output, parameters, progress=lambda value, stage: None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    resolution = parameters["resolution_m"]
    weight = parameters["slope_weight"]
    region = project(boundary())
    minx, miny, maxx, maxy = region.bounds
    left = math.floor((minx - 1500) / resolution) * resolution
    top = math.ceil((maxy + 1500) / resolution) * resolution
    width = math.ceil((maxx + 1500 - left) / resolution)
    height = math.ceil((top - miny + 1500) / resolution)
    transform = from_origin(left, top, resolution, resolution)
    inside = geometry_mask([mapping(region)], out_shape=(height, width), transform=transform, invert=True)
    elevation = np.full((height, width), np.nan, dtype="float32")
    progress(15, "Reprojecting elevation to a metre grid")
    with rasterio.open(DEM) as source:
        if source.crs is None:
            raise ValueError("Elevation raster has no CRS")
        reproject(rasterio.band(source, 1), elevation, src_transform=source.transform, src_crs=source.crs,
                  src_nodata=source.nodata, dst_transform=transform, dst_crs=CRS, dst_nodata=np.nan,
                  resampling=Resampling.bilinear)
    progress(35, "Computing slope and local terrain position")
    slope, relative, flatness, lower, valid = terrain_indicators(elevation, resolution)
    valid &= inside
    if not valid.any():
        raise ValueError("No usable elevation cells overlap the district")
    score = weight * flatness + (1 - weight) * lower
    score[~valid] = np.nan
    classes = classify(score, valid, inside)
    decision = np.where(inside, 4, 0).astype("uint8")
    progress(50, "Measuring mapped water proximity and heritage context")
    water_path = DERIVED / "water.geojson"
    water_features = read_json(water_path)["features"] if water_path.exists() else []
    water_distance = np.full(elevation.shape, np.nan, dtype="float32")
    if water_features:
        water_mask = rasterize([(mapping(project(shape(f["geometry"]))), 1) for f in water_features],
                               out_shape=elevation.shape, transform=transform, all_touched=True, dtype="uint8")
        if water_mask.any():
            water_distance = distance_transform_edt(~water_mask.astype(bool), sampling=resolution).astype("float32")
            water_distance[~inside] = np.nan
    sites, exclusions = curated_sites()
    for feature in sites["features"]:
        point = project(shape(feature["geometry"]))
        row, col = rowcol(transform, point.x, point.y)
        feature["properties"].update({
            "elevation_m": sample_value(elevation, row, col), "slope_degrees": sample_value(slope, row, col),
            "water_distance_m": sample_value(water_distance, row, col), "terrain_score": sample_value(score, row, col),
            "terrain_zone": LABELS[int(classes[row, col])] if 0 <= row < height and 0 <= col < width and classes[row, col] else "Insufficient data",
        })
    progress(65, "Exporting aligned GeoTIFF and zone geometry")
    arrays = [elevation, slope, relative, score, water_distance, classes.astype(float), decision.astype(float)]
    descriptions = ["elevation_m", "slope_degrees", "relative_lower_position_m", "terrain_screening_score",
                    "distance_to_mapped_water_m", "terrain_zone_code", "evidence_assessment_code"]
    profile = dict(driver="GTiff", width=width, height=height, count=len(arrays), dtype="float32", crs=CRS,
                   transform=transform, nodata=NODATA, compress="deflate")
    with rasterio.open(output / "terrain.tif", "w", **profile) as dst:
        for index, (array, description) in enumerate(zip(arrays, descriptions), start=1):
            values = np.where(inside & np.isfinite(array), array, NODATA).astype("float32")
            dst.write(values, index)
            dst.set_band_description(index, description)
        dst.update_tags(method=METHOD_VERSION, confidence="exploratory; unvalidated", class_codes=json.dumps(LABELS))
    polygons = []
    for geom, code in shapes(classes, mask=inside, transform=transform):
        clipped = shape(geom).intersection(region)
        polygons.append({"type": "Feature", "geometry": mapping(project(clipped, inverse=True)), "properties": {
            "terrain_zone": LABELS[int(code)], "code": int(code), "evidence_assessment": "Insufficient data",
            "confidence": "Unvalidated terrain screening", "area_km2": round(clipped.area / 1e6, 5),
        }})
    write_json(output / "zones.geojson", feature_collection(polygons))
    write_json(output / "sites.geojson", sites)
    bounds = rasterio.transform.array_bounds(height, width, transform)
    geo_transform, geo_width, geo_height = calculate_default_transform(CRS, "EPSG:4326", width, height, *bounds)
    for name, data in [("overlay", classes), ("evidence", decision)]:
        geographic = np.zeros((geo_height, geo_width), dtype="uint8")
        reproject(data, geographic, src_transform=transform, src_crs=CRS, dst_transform=geo_transform,
                  dst_crs="EPSG:4326", src_nodata=0, dst_nodata=0, resampling=Resampling.nearest)
        rgba = np.zeros((*geographic.shape, 4), dtype="uint8")
        for code, color in COLORS.items():
            rgba[geographic == code] = color
        Image.fromarray(rgba).save(output / f"{name}.png")
    west, south, east, north = rasterio.transform.array_bounds(geo_height, geo_width, geo_transform)
    total = int(inside.sum())
    zone_counts = [{"name": LABELS[code], "code": code, "cells": int((classes == code).sum()),
                    "area_km2": round(float((classes == code).sum()) * resolution**2 / 1e6, 2),
                    "percent": round(float((classes == code).sum()) / total * 100, 2)} for code in (3, 2, 1, 4)]
    sensitivity = []
    for alternative in [0.4, 0.55, 0.7]:
        other = classify(alternative * flatness + (1-alternative) * lower, valid, inside)
        sensitivity.append({"slope_weight": alternative,
                            "changed_percent": round(float(((other != classes) & valid).sum()) / int(valid.sum()) * 100, 2)})
    site_scores = [f["properties"]["terrain_score"] for f in sites["features"] if f["properties"]["terrain_score"] is not None]
    paths = [BOUNDARY, DEM, SITES, Path(__file__), ROOT / 'backend/catalog.py', ROOT / 'backend/settings.py', ROOT / 'backend/environment.py', ROOT / 'backend/acquisition.py', ROOT / 'scripts/extract_osm.py'] + [p for p in [water_path, DERIVED / "landuse.geojson", DERIVED / "manifest.json", ROOT / 'requirements-lock.txt'] if p.exists()]
    provenance = [{"path": str(path.relative_to(ROOT)), "sha256": checksum(path), "bytes": path.stat().st_size} for path in paths]
    from .environment import snapshot, freeze_comparisons
    progress(85, "Snapshotting environmental evidence and independent reference comparison")
    environmental = snapshot(output)
    comparison = freeze_comparisons(output)
    summary = {
        "method": METHOD_VERSION, "region": "Thanjavur", "parameters": parameters,
        "district_area_km2": round(region.area / 1e6, 2), "grid_cells": total,
        "valid_cells": int(valid.sum()), "coverage_percent": round(float(valid.sum()) / total * 100, 2),
        "zones": zone_counts, "overlay_bounds": [[south, west], [north, east]],
        "heritage_sites": len(sites["features"]), "excluded_sites": exclusions,
        "water_features": len(water_features), "sensitivity": sensitivity,
        "settlement_context": {"sites_with_terrain": len(site_scores),
            "mean_site_score": round(float(np.mean(site_scores)), 3) if site_scores else None,
            "mean_district_score": round(float(np.mean(score[valid])), 3),
            "interpretation": "Descriptive association only. OSM records are not independent, dated settlement observations; no predictive accuracy is claimed."},
        "evidence_assessment": "Insufficient data",
        "environment": environmental,
        "surface_water_comparison": {k:v for k,v in comparison.items() if k != 'points'},
        "missing_evidence": [*([] if any(d['id']=='rainfall' for d in environmental['datasets']) else ['Dated rainfall']),
                             *([] if any(d['id']=='satellite' for d in environmental['datasets']) else ['Dated satellite bands']),
                             "Measured soil permeability and infiltration", "Dated palaeochannel / archaeological field evidence", "Independent storage-outcome field validation"],
        "limitations": [
            "High, moderate and low refer only to an analyst-defined terrain proxy, not measured storage capacity or a probability.",
            "SRTM-labelled input is not a current-condition observation; local vertical datum and source provenance require confirmation.",
            "A low-lying flat cell can be coastal, drained, urbanised or unsuitable; hydrological connectivity and infiltration are not modelled.",
            "OSM water distance uses rasterised geometry and is approximate to one grid cell; incomplete mapping can overestimate distance.",
            "No historical/current fusion, trained archaeological prediction, TWI or flow routing is implemented. Surface-water reference comparisons do not validate storage or archaeological predictions.",
            "Cell areas use centre-in-boundary inclusion; vector exports clip the edge exactly, so areas may differ slightly.",
        ],
        "formula": f"{weight:g} × exp(-slope_degrees / 5) + {1-weight:g} × clip(0.5 + (neighbourhood_mean_elevation - elevation) / 10, 0, 1)",
        "thresholds": {"low": "score < 0.40", "moderate": "0.40 ≤ score < 0.65", "high": "score ≥ 0.65", "insufficient": "No valid DEM or insufficient neighbourhood coverage"},
        "datasets": inventory(), "provenance": provenance,
        "validation": {"status": "Not validated", "accuracy": None, "auc": None, "note": "No labelled water-storage outcome dataset supplied."},
    }
    write_json(output / "report.json", summary)
    progress(95, "Saving provenance and result summary")
    return summary
