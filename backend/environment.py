"""Versioned environmental context, raster exports and independent-reference checks.

These observations contextualise the terrain heuristic; they do not make it a
calibrated archaeological or groundwater model.
"""
import calendar
import hashlib
import json
import math
import shutil
from datetime import date
from pathlib import Path
from typing import Literal
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import reproject, calculate_default_transform
from PIL import Image
from pydantic import BaseModel, Field, ConfigDict, model_validator
from scipy.stats import rankdata
from .settings import RUNTIME, CRS
from .catalog import boundary, project, read_json, checksum
from .heritage import atomic_json, now

ENV = RUNTIME / 'environment'
NODATA = -9999.0
COMPARISON_VERSION = 'blocked-case-control-1'


def grid(resolution=250):
    region = project(boundary())
    x0,y0,x1,y1 = region.bounds
    left, top = math.floor(x0/resolution)*resolution, math.ceil(y1/resolution)*resolution
    width, height = math.ceil((x1-left)/resolution), math.ceil((top-y0)/resolution)
    transform = from_origin(left,top,resolution,resolution)
    inside = geometry_mask([region.__geo_interface__], (height,width), transform, invert=True)
    return {'width':width,'height':height,'transform':transform,'crs':CRS,'inside':inside}


def write_raster(path, values, g, names):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    arrays = values if isinstance(values, list) else [values]
    with rasterio.open(path,'w',driver='GTiff',width=g['width'],height=g['height'],count=len(arrays),
                       dtype='float32',crs=g['crs'],transform=g['transform'],nodata=NODATA,compress='deflate') as dst:
        for i,(value,name) in enumerate(zip(arrays,names),1):
            dst.write(np.where(g['inside'] & np.isfinite(value),value,NODATA).astype('float32'),i)
            dst.set_band_description(i,name)


def normalised_difference(a,b,valid):
    denominator = a+b
    mask = valid & np.isfinite(a) & np.isfinite(b) & (a >= 0) & (b >= 0) & (denominator > 1e-6)
    return np.divide(a-b,denominator,out=np.full(a.shape,np.nan,dtype='float32'),where=mask)


def monthly_rainfall(daily):
    """Never report an incomplete month's sum as a complete monthly total."""
    months = {}
    for day, value in sorted(daily.items()):
        month = day[:6]
        entry = months.setdefault(month,{'month':f'{month[:4]}-{month[4:]}','valid_days':0,'observed_sum_mm':0.0})
        if value is not None and np.isfinite(value) and value >= 0:
            entry['valid_days'] += 1; entry['observed_sum_mm'] += value
    for key,entry in months.items():
        expected = calendar.monthrange(int(key[:4]),int(key[4:]))[1]
        entry['expected_days'] = expected
        entry['coverage_percent'] = round(entry['valid_days']/expected*100,2)
        entry['observed_sum_mm'] = round(entry['observed_sum_mm'],2)
        entry['total_mm'] = entry['observed_sum_mm'] if entry['valid_days'] == expected else None
    return list(months.values())


def manifests():
    return [read_json(p) for p in sorted(ENV.glob('*/manifest.json')) if p.parent.name != 'raw']


def overview():
    datasets = manifests()
    field_path = ENV / 'field/records.json'
    history_path = ENV / 'history/imported.geojson'
    return {'datasets':datasets,'rainfall':read_json(ENV/'rainfall/series.json') if (ENV/'rainfall/series.json').exists() else None,
            'field_records':read_json(field_path) if field_path.exists() else [],
            'history_features':len(read_json(history_path)['features']) if history_path.exists() else 0,
            'job':read_json(ENV/'job.json') if (ENV/'job.json').exists() else None}


def layer_metadata(key,title,path,units,value_range,note):
    path = Path(path)
    with rasterio.open(path) as src:
        a = src.read(1,masked=True)
        g = grid()
        valid = (~np.ma.getmaskarray(a)) & g['inside']
        coverage = round(float(valid.sum()/g['inside'].sum()*100),2)
    return {'id':key,'title':title,'file':str(path.relative_to(ENV)).replace('\\','/'),'units':units,
            'range':value_range,'note':note,'coverage_percent':coverage,'sha256':checksum(path)}


def render_layer(path, png, limits, categorical=False):
    with rasterio.open(path) as src:
        t,w,h = calculate_default_transform(src.crs,'EPSG:4326',src.width,src.height,*src.bounds)
        a = np.full((h,w),NODATA,dtype='float32')
        reproject(rasterio.band(src,1),a,src_transform=src.transform,src_crs=src.crs,src_nodata=NODATA,
                  dst_crs='EPSG:4326',dst_transform=t,dst_nodata=NODATA,resampling=Resampling.nearest)
    valid = np.isfinite(a) & (a != NODATA)
    normalized = np.clip((np.where(valid,a,limits[0])-limits[0])/(limits[1]-limits[0]),0,1)
    low, high = np.array([225,204,146]),np.array([33,106,112])
    rgb = low[None,None,:]*(1-normalized[:,:,None])+high[None,None,:]*normalized[:,:,None]
    rgba = np.dstack([rgb.astype('uint8'),np.where(valid,210,0).astype('uint8')])
    if categorical:
        colors = {0:(0,0,0,0),1:(43,95,170,220),2:(56,167,82,220),3:(193,68,54,230),4:(111,175,214,220),
                  5:(140,195,84,220),6:(223,147,82,230),7:(93,105,173,220),8:(125,96,170,220),9:(150,120,120,220),10:(195,165,160,220)}
        for value,color in colors.items(): rgba[(a == value) & valid] = color
    Image.fromarray(rgba).save(png)
    west,south,east,north = rasterio.transform.array_bounds(h,w,t)
    return [[south,west],[north,east]]


def snapshot(output):
    """Freeze context for an analysis run so later downloads never change its evidence."""
    output = Path(output)
    data = {'created_at':now(),'datasets':manifests(),'layers':[],'seasonal_layers':[]}
    for dataset in data['datasets']:
        for layer in dataset.get('layers',[]):
            src = ENV / layer['file']
            if not src.is_file():
                raise ValueError(f'Published environmental layer is missing: {layer["id"]}. Refresh public data before creating a new run.')
            key = layer['id']
            tif, png = f'context_{key}.tif', f'context_{key}.png'
            shutil.copyfile(src,output/tif)
            if layer.get('sha256') and checksum(output/tif) != layer['sha256']:
                raise ValueError(f'Environmental layer {key} differs from its source manifest. Refresh public data before creating a new run.')
            bounds = render_layer(output/tif,output/png,layer['range'],key == 'transitions')
            data['layers'].append({**layer,'raster':tif,'image':png,'bounds':bounds})
        for quarter,season in enumerate(dataset.get('seasons',[]),1):
            for index in ('ndvi','ndwi'):
                src = ENV / season[f'{index}_file']
                name = f'context_{index}_q{quarter}.tif'
                shutil.copyfile(src,output/name)
                data['seasonal_layers'].append({'title':f'{index.upper()} · {season["label"]}',
                    'raster':name,'sha256':checksum(output/name),'coverage_percent':season['coverage_percent']})
    rainfall = ENV/'rainfall/series.json'
    if rainfall.exists():
        shutil.copyfile(rainfall,output/'rainfall.json')
        data['rainfall_sha256'] = checksum(rainfall)
    for source,name in [(ENV/'field/records.json','validation_records.json'),(ENV/'history/imported.geojson','historical_features.geojson')]:
        if source.exists(): shutil.copyfile(source,output/name)
    atomic_json(output/'environment.json',data)
    return data


class FieldRecord(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    id: str = Field(min_length=1,max_length=100)
    longitude: float = Field(ge=-180,le=180)
    latitude: float = Field(ge=-90,le=90)
    observed_on: date
    target: Literal['surface_water_presence','water_storage_suitability','archaeological_presence','infiltration_mm_h']
    value: float = Field(ge=0,le=100000)
    source: str = Field(min_length=8,max_length=1000)
    method: str = Field(min_length=8,max_length=1000)
    independence_statement: str = Field(min_length=15,max_length=2000)

    @model_validator(mode='after')
    def binary_or_rate(self):
        if self.target != 'infiltration_mm_h' and self.value not in (0,1):
            raise ValueError('Presence/suitability outcomes must be 0 or 1')
        if self.observed_on > date.today():
            raise ValueError('Observation date cannot be in the future')
        return self


def validate_records(records):
    from shapely.geometry import Point
    if not isinstance(records,list): raise ValueError('Expected a JSON array of field records')
    parsed = [FieldRecord.model_validate(r).model_dump(mode='json') for r in records]
    if not 1 <= len(parsed) <= 10000: raise ValueError('Supply 1–10,000 records')
    ids, locations = set(),set()
    for r in parsed:
        if not boundary().covers(Point(r['longitude'],r['latitude'])): raise ValueError(f"{r['id']}: outside district")
        key = (round(r['longitude'],6),round(r['latitude'],6),r['target'])
        if r['id'] in ids or key in locations: raise ValueError('Duplicate ID or location/target; select one independent observation')
        ids.add(r['id']); locations.add(key)
    return parsed


def metrics(scores,labels,threshold=.65):
    scores,labels = np.asarray(scores),np.asarray(labels,dtype=int)
    if len(scores) < 20 or len(np.unique(labels)) < 2:
        return {'status':'Insufficient comparison samples','samples':len(scores),'accuracy':None,'auc':None,
                'requirement':'At least 20 usable samples selected across spatial blocks and both outcome classes are required.'}
    predicted = scores >= threshold
    tp,tn = int(((predicted == 1)&(labels == 1)).sum()),int(((predicted == 0)&(labels == 0)).sum())
    fp,fn = int(((predicted == 1)&(labels == 0)).sum()),int(((predicted == 0)&(labels == 1)).sum())
    n1,n0 = int(labels.sum()),len(labels)-int(labels.sum())
    auc = (rankdata(scores)[labels == 1].sum()-n1*(n1+1)/2)/(n1*n0)
    return {'status':'Comparison available','samples':len(scores),'threshold':threshold,'confusion':{'tp':tp,'tn':tn,'fp':fp,'fn':fn},
            'accuracy':round((tp+tn)/len(scores),4),'balanced_accuracy':round((tp/n1+tn/n0)/2,4),
            'precision':round(tp/(tp+fp),4) if tp+fp else None,'recall':round(tp/n1,4),'auc':round(float(auc),4)}


def reference_cells(occurrence, valid, stride):
    """One reference per block, then balanced case/control sampling without scores.

    Persistent water is scarce, so a point lattice can miss every wet pixel.
    Water takes priority within each block; the closest eligible cell to the
    block centre is chosen. Dry-only blocks are deterministically subsampled.
    This is a case/control association check, not a prevalence estimate.
    """
    wet, dry = [], []
    for row in range(0, valid.shape[0], stride):
        for col in range(0, valid.shape[1], stride):
            values = occurrence[row:row+stride,col:col+stride]
            usable = valid[row:row+stride,col:col+stride]
            candidates = np.argwhere(usable & (values >= 90) & (values <= 100))
            destination = wet
            if not len(candidates):
                candidates = np.argwhere(usable & (values == 0))
                destination = dry
            if len(candidates):
                centre = (np.array(values.shape)-1)/2
                r,c = candidates[np.argmin(((candidates-centre)**2).sum(axis=1))]
                destination.append((row+int(r),col+int(c)))
    size = min(len(wet),len(dry))
    if not size:
        return wet+dry
    rng = np.random.default_rng(20251004)
    return sorted([wet[i] for i in rng.choice(len(wet),size,replace=False)] +
                  [dry[i] for i in rng.choice(len(dry),size,replace=False)])


def evaluate_run(output, target='surface_water_presence', source='satellite'):
    """Evaluate the untouched terrain score, never a score fitted to this reference."""
    output = Path(output)
    with rasterio.open(output/'terrain.tif') as terrain:
        scores = terrain.read(4); valid = np.isfinite(scores) & (scores != terrain.nodata)
        selected_scores,labels,points = [],[],[]
        if source == 'satellite':
            path = output/'context_occurrence.tif'
            if not path.exists(): return {'status':'Historical water reference unavailable','accuracy':None,'auc':None}
            with rasterio.open(path) as src:
                occurrence = np.full(scores.shape,NODATA,dtype='float32')
                reproject(rasterio.band(src,1),occurrence,src_transform=src.transform,src_crs=src.crs,
                    dst_transform=terrain.transform,dst_crs=terrain.crs,src_nodata=NODATA,dst_nodata=NODATA,resampling=Resampling.nearest)
            stride = max(1,round(2000/abs(terrain.transform.a)))
            for row,col in reference_cells(occurrence,valid,stride):
                value = occurrence[row,col]
                selected_scores.append(float(scores[row,col])); labels.append(int(value >= 90))
                x,y = terrain.xy(row,col)
                points.append({'x':x,'y':y,'observed':int(value>=90),'score':round(float(scores[row,col]),4)})
            note = 'Independent Landsat/JRC reference; one sample per approximately 2 km block, persistent water≥90% prioritized, dry=0%, intermediate occurrence excluded. Equal wet/dry blocks selected with a fixed seed without inspecting terrain scores. Case/control metrics (including precision) do not represent district prevalence. This tests surface-water association, not storage capacity or archaeology. Adjacent blocks can remain spatially correlated.'
        else:
            from pyproj import Transformer
            transform = Transformer.from_crs(4326,terrain.crs,always_xy=True)
            path = output/'validation_records.json'
            records = read_json(path) if path.exists() else []
            occupied = set()
            for r in sorted(records,key=lambda r:r['id']):
                if r['target'] != target: continue
                x,y = transform.transform(r['longitude'],r['latitude']); cell=(int(x//2000),int(y//2000))
                row,col = terrain.index(x,y)
                if cell in occupied or not(0<=row<terrain.height and 0<=col<terrain.width) or not valid[row,col]: continue
                occupied.add(cell); selected_scores.append(float(scores[row,col])); labels.append(int(r['value']))
                points.append({'x':x,'y':y,'observed':r['value'],'score':round(float(scores[row,col]),4),'id':r['id']})
            note = 'User-supplied outcome observations, one usable record per 2 km block. Provenance and independence are declared by the contributor, not independently certified. No model fitting uses these labels.'
    from pyproj import Transformer
    geographic=Transformer.from_crs(CRS,4326,always_xy=True)
    for p in points:
        p['longitude'],p['latitude']=geographic.transform(p['x'],p['y'])
    return {**metrics(selected_scores,labels),'method_version':COMPARISON_VERSION,'source':source,'target':target,'note':note,'points':points,'crs':CRS}


def freeze_comparisons(output):
    output = Path(output)
    results = {'satellite:surface_water_presence':evaluate_run(output)}
    for target in ('surface_water_presence','water_storage_suitability','archaeological_presence'):
        results[f'field:{target}'] = evaluate_run(output,target,'field')
    atomic_json(output/'comparisons.json',{'method_version':COMPARISON_VERSION,'results':results})
    return results['satellite:surface_water_presence']
