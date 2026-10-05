"""Extract exact matching OSM outlines from the existing PBF; no name guesses."""
import json
import osmium
from shapely import wkb
from shapely.geometry import mapping
from shapely.ops import transform
from pyproj import Transformer
from backend.heritage import profiles, atomic_json
from backend.catalog import checksum
from backend.settings import ROOT, DERIVED


class HeritageExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.factory = osmium.geom.WKBFactory()
        self.sites = {s['osm_id']: s for s in profiles()}
        # Retained temple relation was deduplicated against this mapped building.
        self.sites['way/120390896'] = self.sites['relation/6668806']
        self.found = {}
        self.projection = Transformer.from_crs(4326, 32644, always_xy=True).transform

    def area(self, obj):
        key = ('way/' if obj.from_way() else 'relation/') + str(obj.orig_id())
        if key not in self.sites:
            return
        try:
            geometry = wkb.loads(self.factory.create_multipolygon(obj), hex=True)
            s = self.sites[key]
            metric = transform(self.projection, geometry)
            cx, cy = self.projection(*s['coordinates'])
            rings = [[[round(x-cx, 2), round(y-cy, 2)] for x, y in polygon.exterior.coords] for polygon in metric.geoms]
            self.found[s['id']] = {'osm_id': key, 'rings_m': rings, 'geometry': mapping(geometry),
                'source': 'Supplied regional OSM PBF; ODbL', 'meaning': 'Contemporary mapped outline; may delimit a complex rather than a building',
                'url': 'https://www.openstreetmap.org/' + key}
        except (RuntimeError, ValueError):
            pass


if __name__ == '__main__':
    source = ROOT / 'southern-zone-260806.osm.pbf'
    extractor = HeritageExtractor()
    extractor.apply_file(str(source), locations=True, idx='flex_mem')
    digest = checksum(source)
    for entry in extractor.found.values():
        entry['source_sha256'] = digest
    atomic_json(DERIVED / 'heritage_footprints.json', extractor.found)
    print(json.dumps({'outlines': list(extractor.found), 'source_sha256': digest}))
