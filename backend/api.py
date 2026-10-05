import logging
import os
import threading
import uuid
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import rasterio
from pyproj import Transformer
from . import database as db
from .settings import ROOT, RUNTIME, CRS, DERIVED
from .catalog import inventory, boundary, mapping, curated_sites, feature_collection, read_json
from shapely.geometry import shape
from .analysis import execute, LABELS, NODATA
from .heritage_api import router as heritage_router
from .heritage import prewarm
from .environment_api import router as environment_router
from .environment_api import acquire_lock
from . import environment

log = logging.getLogger(__name__)
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    db.save_datasets(inventory())
    job_path=environment.ENV/'job.json'
    if job_path.exists() and read_json(job_path).get('status') in ('queued','running'):
        from .heritage import atomic_json, now
        atomic_json(job_path,{**read_json(job_path),'status':'failed','stage':'Interrupted by server restart; retry acquisition','finished_at':now()})
    prewarm()
    app.state.executor = ThreadPoolExecutor(max_workers=1)
    yield
    app.state.executor.shutdown(wait=True)


app = FastAPI(title="GeoDyssey", version="1.0.0", lifespan=lifespan)
app.include_router(heritage_router)
app.include_router(environment_router)


class RunParameters(BaseModel):
    resolution_m: Literal[100, 250, 500] = 250
    slope_weight: float = Field(default=0.55, ge=0.1, le=0.9)


def require_run(run_id, completed=False):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if completed and run["status"] != "completed":
        raise HTTPException(409, "This run has not completed successfully")
    return run


def worker(run_id, parameters):
    try:
        db.update_run(run_id, status="running", stage="Validating inputs", progress=5)
        summary = execute(RUNTIME / "runs" / run_id, parameters,
                          lambda progress, stage: db.update_run(run_id, progress=progress, stage=stage))
        db.update_run(run_id, status="completed", progress=100, stage="Complete", finished_at=db.now(), summary=summary)
    except Exception as exc:
        log.exception("Run %s failed", run_id)
        db.update_run(run_id, status="failed", stage="Analysis failed", finished_at=db.now(), error=str(exc))


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "database": "SQLite", "region": "Thanjavur", "hosted_demo": os.environ.get("GEODYSSEY_HOSTED_DEMO") == "1"}


@app.get("/api/catalog")
def catalog():
    datasets = inventory()
    db.save_datasets(datasets)
    return {"datasets": datasets}


@app.get("/api/boundary")
def get_boundary():
    return feature_collection([{"type": "Feature", "geometry": mapping(boundary()), "properties": {"name": "Thanjavur"}}])


@app.get("/api/sites")
def sites():
    return curated_sites()[0]


@app.get("/api/runs")
def runs():
    return [{k: v for k, v in run.items() if k != "summary"} for run in db.list_runs()]


@lru_cache(maxsize=4)
def map_layer(name, modified):
    data = read_json(DERIVED / f"{name}.geojson")
    for feature in data["features"]:
        feature["geometry"] = mapping(shape(feature["geometry"]).simplify(0.0001, preserve_topology=True))
    return data


@app.get("/api/layers/{name}")
def layer(name: str):
    if name not in ("water", "landuse"):
        raise HTTPException(404, "Unknown layer")
    path = DERIVED / f"{name}.geojson"
    if not path.exists():
        raise HTTPException(404, "Layer unavailable. Run the OSM extraction script first.")
    return map_layer(name, path.stat().st_mtime_ns)


@app.post("/api/runs", status_code=202)
def start_run(parameters: RunParameters):
    with lock:
        if not acquire_lock.acquire(blocking=False):
            raise HTTPException(409, "Wait for environmental acquisition to finish before snapshotting a new run")
        try:
            if any(run["status"] in ("queued", "running") for run in db.list_runs()):
                raise HTTPException(409, "An analysis is already running")
            run_id = uuid.uuid4().hex
            db.create_run(run_id, parameters.model_dump())
            app.state.executor.submit(worker, run_id, parameters.model_dump())
        finally:
            acquire_lock.release()
    return db.get_run(run_id)


@app.get("/api/runs/{run_id}")
def run_status(run_id: str):
    return require_run(run_id)


ARTIFACTS = {"report.json": "application/json", "zones.geojson": "application/geo+json",
    "terrain.tif": "image/tiff", "overlay.png": "image/png", "evidence.png": "image/png", "sites.geojson": "application/geo+json"}


@app.get("/api/runs/{run_id}/artifacts/{name}")
def artifact(run_id: str, name: str):
    require_run(run_id, completed=True)
    extra = {'environment.json':'application/json','comparisons.json':'application/json','rainfall.json':'application/json','validation_records.json':'application/json','historical_features.geojson':'application/geo+json'}
    for key in ('clay','infiltration','ndvi','ndwi','occurrence','transitions'):
        extra[f'context_{key}.tif']='image/tiff'
        extra[f'context_{key}.png']='image/png'
    for index in ('ndvi','ndwi'):
        for quarter in range(1,5): extra[f'context_{index}_q{quarter}.tif']='image/tiff'
    allowed = {**ARTIFACTS,**extra}
    if name not in allowed:
        raise HTTPException(404, "Artifact not found")
    path = RUNTIME / "runs" / run_id / name
    if not path.exists():
        raise HTTPException(404, "Artifact file is missing")
    return FileResponse(path, media_type=allowed[name],
                        filename=name if name in ("terrain.tif", "zones.geojson", "report.json") else None)


@app.get("/api/runs/{run_id}/cell")
def cell(run_id: str, lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180)):
    require_run(run_id, completed=True)
    x, y = Transformer.from_crs("EPSG:4326", CRS, always_xy=True).transform(lng, lat)
    with rasterio.open(RUNTIME / "runs" / run_id / "terrain.tif") as source:
        row, col = source.index(x, y)
        if not (0 <= row < source.height and 0 <= col < source.width):
            raise HTTPException(404, "Location is outside the study area")
        values = source.read(window=((row, row+1), (col, col+1)))[:, 0, 0]
        if values[5] == NODATA:
            raise HTTPException(404, "Location is outside the study area")
        result = {name: None if value == NODATA else round(float(value), 4)
                  for name, value in zip(source.descriptions, values)}
    result.update(lat=lat, lng=lng, terrain_zone=LABELS[int(values[5])], evidence_assessment="Insufficient data")
    result['environment'] = {}
    snapshot_path = RUNTIME / 'runs' / run_id / 'environment.json'
    if snapshot_path.exists():
        for layer in read_json(snapshot_path)['layers']:
            with rasterio.open(RUNTIME / 'runs' / run_id / layer['raster']) as context:
                sample = next(context.sample([(x,y)],masked=True))[0]
                result['environment'][layer['id']] = {'value':None if bool(getattr(sample,'mask',False)) or float(sample)==NODATA else round(float(sample),4),
                    'units':layer['units'],'title':layer['title']}
    return result


dist = ROOT / "frontend/dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(dist / "index.html")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(dist / "favicon.svg")
