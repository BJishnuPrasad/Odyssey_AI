import hashlib
import json
from functools import lru_cache
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer
from .settings import BOUNDARY, DEM, SITES, DERIVED, ROOT, CRS, RUNTIME


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def boundary():
    return unary_union([shape(f["geometry"]) for f in read_json(BOUNDARY)["features"]])


def project(geometry, inverse=False):
    source, target = (CRS, "EPSG:4326") if inverse else ("EPSG:4326", CRS)
    return transform(Transformer.from_crs(source, target, always_xy=True).transform, geometry)


def feature_collection(features):
    return {"type": "FeatureCollection", "features": features}


def curated_sites():
    """Retain contextual OSM records; do not turn monuments into training labels."""
    retained, excluded = [], []
    for feature in read_json(SITES)["features"]:
        props = feature.get("properties", {})
        point = shape(feature["geometry"]).representative_point()
        reason = None
        if props.get("type") == "site":
            reason = "Multi-site relation centre is not a surveyed location"
        elif not boundary().covers(point):
            reason = "Outside district boundary"
        else:
            for previous in retained:
                pp = previous["properties"]
                same_entity = props.get("wikidata") and props.get("wikidata") == pp.get("wikidata")
                same_name = props.get("name", "").casefold() == pp.get("name", "").casefold()
                distance = project(point).distance(project(shape(previous["geometry"])))
                if same_entity or (same_name and distance < 150):
                    reason = "Duplicate entity or same named location within 150 m"
                    break
        record = {"type": "Feature", "geometry": mapping(point), "properties": {
            "name": props.get("name:en") or props.get("name", "Unnamed heritage record"),
            "osm_id": props.get("@id", feature.get("id")), "wikidata": props.get("wikidata"),
            "category": props.get("historic", props.get("heritage", "heritage")),
            "location_quality": "OSM representative point; not field verified",
            "source": "OpenStreetMap / supplied repository",
        }}
        if reason:
            excluded.append({"name": record["properties"]["name"], "reason": reason})
        else:
            retained.append(record)
    return feature_collection(retained), excluded


def inventory():
    extraction = read_json(DERIVED / "manifest.json") if (DERIVED / "manifest.json").exists() else {}
    specs = [
        ("boundary", "District boundary", BOUNDARY, "Context", "Supplied administrative boundary; source vintage unverified."),
        ("dem", "SRTM elevation", DEM, "Context", "SRTM-labelled raster; metre elevations assumed. Coverage is checked per run."),
        ("heritage", "Heritage inventory", SITES, "Historical context", "OSM monuments and heritage records, not a dated settlement inventory."),
        ("water", "Water bodies & channels", DERIVED / "water.geojson", "Recent mapping", "Extracted from supplied OSM PBF; not a seasonal water observation."),
        ("landuse", "Land use", DERIVED / "landuse.geojson", "Recent mapping", "OSM coverage is incomplete; not a satellite classification."),
    ]
    datasets = []
    for key, title, path, timescale, note in specs:
        exists = path.exists()
        count = None
        if exists and path.suffix == ".geojson":
            count = len(read_json(path)["features"])
        datasets.append({"id": key, "name": title, "status": "available" if exists and count != 0 else "missing",
                         "timescale": timescale, "note": note, "features": count,
                         "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size if exists else 0,
                         "observed_at": extraction.get("source_timestamp") if key in ("water", "landuse") else None})
    for key, title, timescale, note in [
        ("rainfall", "Rainfall time series", "Short term", "No dated rainfall observations supplied."),
        ("soil", "District soil & infiltration", "Context", "No district infiltration or storage observations supplied. Site-level SoilGrids profiles are separate educational context."),
        ("satellite", "NDVI / NDWI time series", "Short term", "Acquisition scripts are not imagery; no usable satellite bands supplied."),
        ("history", "Palaeochannels & historical maps", "Long term", "No georeferenced historical landscape evidence supplied."),
        ("validation", "Independent validation sites", "Validation", "No surveyed storage outcomes or independent archaeological labels supplied."),
    ]:
        manifest_path = RUNTIME / 'environment' / key / 'manifest.json'
        manifest = read_json(manifest_path) if manifest_path.exists() else None
        if manifest:
            datasets.append({'id':key,'name':manifest['title'],'status':manifest['status'],'timescale':timescale,
                'note':manifest['note'],'features':manifest['records'],'path':f'runtime/environment/{key}/manifest.json',
                'bytes':manifest_path.stat().st_size,'observed_at':manifest.get('observed_at')})
        elif key == 'validation' and (RUNTIME/'environment/history/manifest.json').exists():
            field_path = RUNTIME/'environment/field/records.json'
            datasets.append({'id':key,'name':'Independent reference & field validation','status':'partial','timescale':timescale,
                'note':'JRC/Landsat surface-water reference comparison is available. Storage and archaeological validation require independently observed outcomes; import and evaluation tools are ready.',
                'features':len(read_json(field_path)) if field_path.exists() else 0,'path':'runtime/environment/field/records.json',
                'bytes':field_path.stat().st_size if field_path.exists() else 0,'observed_at':None})
        else:
            datasets.append({"id": key, "name": title, "status": "missing", "timescale": timescale,
                             "note": note, "features": None, "path": None, "bytes": 0, "observed_at": None})
    profile_paths = list((RUNTIME / "heritage").glob("*/soil.json"))
    datasets.append({"id": "heritage_soil", "name": "Heritage soil profiles", "status": "available" if profile_paths else "missing",
        "timescale": "Site context", "note": "Cached soil profiles for the heritage viewer. Model estimates are not measured stratigraphy and do not change terrain scores.",
        "features": len(profile_paths), "path": "runtime/heritage/<site-id>/soil.json", "bytes": sum(p.stat().st_size for p in profile_paths), "observed_at": None})
    return datasets
