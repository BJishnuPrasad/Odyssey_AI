"""Extract actual water and land-use geometry from the supplied regional PBF.

Run from repository root: python -m scripts.extract_osm
No external API or account is required. Original inputs are never overwritten.
"""
import json
from datetime import datetime, timezone
import osmium
from shapely import wkb, make_valid
from shapely.geometry import mapping
from backend.catalog import boundary, checksum, feature_collection
from backend.settings import ROOT, DERIVED


class Extractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.factory = osmium.geom.WKBFactory()
        self.region = boundary()
        self.water, self.landuse = [], []
        self.invalid = 0

    def emit(self, obj, geometry, target, kind):
        try:
            geom = wkb.loads(geometry, hex=True)
            if not geom.intersects(self.region):
                return
            geom = make_valid(geom).intersection(self.region)
            if geom.is_empty:
                return
            tags = dict(obj.tags)
            target.append({"type": "Feature", "geometry": mapping(geom), "properties": {
                "osm_id": str(obj.id), "name": tags.get("name:en", tags.get("name", "")),
                "kind": kind, "landuse": tags.get("landuse"), "natural": tags.get("natural"),
                "water": tags.get("water"), "waterway": tags.get("waterway"),
            }})
        except (RuntimeError, ValueError):
            self.invalid += 1

    def way(self, obj):
        if obj.tags.get("waterway") in ("river", "stream", "canal", "drain", "ditch"):
            try:
                self.emit(obj, self.factory.create_linestring(obj), self.water, "channel")
            except (RuntimeError, osmium.InvalidLocationError):
                self.invalid += 1

    def area(self, obj):
        water = obj.tags.get("natural") in ("water", "wetland") or obj.tags.get("landuse") in ("reservoir", "basin") or obj.tags.get("waterway") == "riverbank"
        landuse = obj.tags.get("landuse") is not None
        if not (water or landuse):
            return
        try:
            geometry = self.factory.create_multipolygon(obj)
            if water:
                self.emit(obj, geometry, self.water, "waterbody")
            if landuse:
                self.emit(obj, geometry, self.landuse, "landuse")
        except (RuntimeError, osmium.InvalidLocationError):
            self.invalid += 1


def main():
    source = ROOT / "southern-zone-260806.osm.pbf"
    if not source.exists() or source.stat().st_size < 1000:
        raise SystemExit("OSM PBF is missing or still a Git LFS pointer. Run git lfs pull first.")
    with osmium.io.Reader(str(source)) as reader:
        timestamp = reader.header().get("osmosis_replication_timestamp") or None
    DERIVED.mkdir(parents=True, exist_ok=True)
    handler = Extractor()
    print("Reading regional PBF and assembling water/land-use polygons...", flush=True)
    handler.apply_file(str(source), locations=True, idx="flex_mem")
    for key, features in [("water", handler.water), ("landuse", handler.landuse)]:
        path = DERIVED / f"{key}.geojson"
        path.write_text(json.dumps(feature_collection(features), ensure_ascii=False), encoding="utf-8")
        print(f"{key}: {len(features)} district features", flush=True)
    manifest = {"source": source.name, "source_sha256": checksum(source), "source_timestamp": timestamp,
                "extracted_at": datetime.now(timezone.utc).isoformat(), "invalid_geometries": handler.invalid,
                "water_features": len(handler.water), "landuse_features": len(handler.landuse),
                "attribution": "OpenStreetMap contributors, ODbL", "method": "district intersection; water-specific tags; assembled multipolygons"}
    (DERIVED / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
