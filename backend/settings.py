from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
RUNTIME = Path(os.environ.get("GEODYSSEY_RUNTIME", ROOT / "runtime"))
BOUNDARY = DATA / "raw/boundary/thanjavur_boundary.geojson"
DEM = DATA / "raw/dem/output_SRTMGL1.tif"
SITES = DATA / "raw/osm/thanjavur_osm_alt.geojson"
DERIVED = DATA / "derived"
CRS = "EPSG:32644"
METHOD_VERSION = "terrain-screening-1.0"
