import json
import re
import threading
from datetime import date
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from shapely.geometry import shape
from shapely.errors import ShapelyError
from . import environment as e, acquisition, database as db
from .catalog import boundary, read_json
from .heritage import atomic_json, now
from .settings import RUNTIME

router=APIRouter(prefix='/api/environment')
acquire_lock=threading.Lock()


class AcquisitionRequest(BaseModel):
    kinds: list[Literal['rainfall','soil','satellite','history']] = Field(default=['rainfall','soil','satellite','history'],min_length=1,max_length=4)
    start_year: int = Field(default=2024,ge=1984)
    end_year: int = Field(default=2025,ge=1984)

    @model_validator(mode='after')
    def years(self):
        if not self.start_year <= self.end_year < date.today().year or self.end_year-self.start_year > 5:
            raise ValueError('Choose up to six complete years ending before the current year')
        if len(set(self.kinds)) != len(self.kinds): raise ValueError('Duplicate source kinds')
        if 'satellite' in self.kinds and self.end_year < 2017: raise ValueError('Sentinel-2 L2A requires 2017 or later')
        return self


@router.get('')
def current(): return e.overview()


@router.post('/acquire',status_code=202)
def start_acquisition(data:AcquisitionRequest):
    if not acquire_lock.acquire(blocking=False): raise HTTPException(409,'Data acquisition is already running')
    def worker():
        try: acquisition.run(data.kinds,data.start_year,data.end_year)
        finally: acquire_lock.release()
    try:
        if any(r['status'] in ('queued','running') for r in db.list_runs()):
            raise HTTPException(409,'Wait for the active analysis before acquiring data')
        atomic_json(e.ENV/'job.json',{'status':'queued','stage':'Queued','progress':0,'started_at':now()})
        threading.Thread(target=worker,daemon=True).start()
    except Exception:
        acquire_lock.release()
        raise
    return {'status':'queued'}


@router.get('/layer/{key}')
def layer(key:str):
    for dataset in e.manifests():
        for info in dataset.get('layers',[]):
            if info['id']==key:
                png=e.ENV/str(info['file']).replace('.tif','.png')
                bounds=e.render_layer(e.ENV/info['file'],png,info['range'],key=='transitions')
                return {**info,'bounds':bounds,'image_url':f'/api/environment/image/{key}'}
    raise HTTPException(404,'Layer not acquired')


@router.get('/image/{key}')
def image(key:str):
    for dataset in e.manifests():
        for info in dataset.get('layers',[]):
            if info['id']==key:
                png=e.ENV/str(info['file']).replace('.tif','.png')
                if not png.exists(): e.render_layer(e.ENV/info['file'],png,info['range'],key=='transitions')
                return FileResponse(png,media_type='image/png')
    raise HTTPException(404,'Layer not acquired')


@router.get('/season/{year}/{quarter}/{index}')
def season(year:int,quarter:int,index:str):
    if index not in ('ndvi','ndwi') or quarter not in (1,2,3,4): raise HTTPException(404,'Unknown seasonal layer')
    manifest=e.ENV/'satellite/manifest.json'
    seasons=read_json(manifest).get('seasons',[]) if manifest.exists() else []
    match=next((s for s in seasons if s['label']==f'{year} Q{quarter}'),None)
    if not match: raise HTTPException(404,'Season not acquired')
    path=e.ENV/match[f'{index}_file']
    if not path.exists(): raise HTTPException(404,'Season file unavailable')
    png=path.with_suffix('.png')
    e.render_layer(path,png,[-1,1])
    return FileResponse(png,media_type='image/png')


@router.put('/field-records')
async def import_records(request:Request):
    body=await bounded_json(request)
    try: records=e.validate_records(body)
    except (ValueError,TypeError) as exc: raise HTTPException(422,str(exc))
    # Append/upsert explicit observations, preserving earlier records and rejecting collisions.
    path=e.ENV/'field/records.json'
    existing=read_json(path) if path.exists() else []
    merged={r['id']:r for r in existing}; merged.update({r['id']:r for r in records})
    try: checked=e.validate_records(list(merged.values()))
    except ValueError as exc: raise HTTPException(422,str(exc))
    atomic_json(path,checked)
    return {'imported':len(records),'total':len(checked),'note':'Create a new analysis to snapshot and evaluate these observations.'}


async def bounded_json(request):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>5*1024*1024: raise HTTPException(413,'JSON exceeds 5 MiB')
    try: return json.loads(data)
    except (ValueError,UnicodeDecodeError): raise HTTPException(422,'Invalid JSON')


@router.put('/historical-features')
async def import_history(request:Request):
    body=await bounded_json(request)
    try:
        if not isinstance(body,dict) or body.get('type')!='FeatureCollection': raise ValueError('Expected a WGS84 GeoJSON FeatureCollection')
        features=body.get('features',[])
        if not isinstance(features,list) or not 1<=len(features)<=1000: raise ValueError('Supply 1–1,000 features')
        for feature in features:
            if not isinstance(feature,dict) or feature.get('type')!='Feature' or not isinstance(feature.get('geometry'),dict) or not isinstance(feature.get('properties'),dict):
                raise ValueError('Each GeoJSON feature requires geometry and properties objects')
            geo=shape(feature['geometry']); props=feature.get('properties',{})
            if not geo.is_valid or geo.is_empty or not boundary().covers(geo): raise ValueError('Geometry must be valid and inside Thanjavur in WGS84')
            if not all(isinstance(props.get(k),str) and props[k].strip() for k in ('title','source','period','interpretation')):
                raise ValueError('Each feature needs title, source, period and interpretation strings')
            if props.get('confidence') not in ('documented','candidate','field verified'): raise ValueError('Confidence must be documented, candidate, or field verified')
        path=e.ENV/'history/imported.geojson'
        previous=read_json(path)['features'] if path.exists() else []
        atomic_json(path,{'type':'FeatureCollection','features':previous+features})
    except (ValueError,TypeError,KeyError,IndexError,ShapelyError) as exc: raise HTTPException(422,str(exc))
    return {'imported':len(features),'note':'Source-declared interpretations; dates are not independently certified.'}


@router.get('/historical-features')
def historical_features():
    path=e.ENV/'history/imported.geojson'
    return read_json(path) if path.exists() else {'type':'FeatureCollection','features':[]}


@router.get('/validation/{run_id}')
def validation(run_id:str,target:Literal['surface_water_presence','water_storage_suitability','archaeological_presence']='surface_water_presence',source:Literal['satellite','field']='satellite'):
    run=db.get_run(run_id)
    if not run: raise HTTPException(404,'Run not found')
    if run['status']!='completed': raise HTTPException(409,'Choose a completed run')
    if source=='satellite' and target!='surface_water_presence': raise HTTPException(422,'Satellite reference supports surface-water presence only')
    path=RUNTIME/'runs'/run_id/'comparisons.json'
    if not path.exists():
        return {'status':'Create a new run to freeze reference comparisons','samples':0,'accuracy':None,'auc':None,
                'note':'This older run predates versioned comparisons. Its original report is preserved.'}
    return read_json(path)['results'][f'{source}:{target}']
