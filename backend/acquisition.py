"""Explicit bounded acquisition of public datasets; all outputs retain provenance."""
import calendar
import json
import math
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import reproject
from pyproj import Transformer
from shapely.geometry import shape
from . import environment as e
from .catalog import boundary, checksum
from .heritage import atomic_json, now


def product_folder(folder):
    """Publish a manifest only after all products in this generation succeed."""
    result=folder/'products'/uuid.uuid4().hex
    result.mkdir(parents=True,exist_ok=True)
    return result


def get_json(url, params=None):
    with httpx.Client(timeout=60,follow_redirects=True) as client:
        response = client.get(url,params=params); response.raise_for_status(); return response.json()


def local_band(path,g,crs=None,nodata=None):
    with rasterio.open(path) as src:
        result = np.full((g['height'],g['width']),np.nan,dtype='float32')
        # An untagged WCS dataset band causes GDAL to use its missing dataset CRS;
        # an ndarray lets the explicitly documented native CRS take effect.
        source = rasterio.band(src,1) if src.crs else src.read(1)
        reproject(source,result,src_transform=src.transform,src_crs=src.crs or crs,
                  src_nodata=src.nodata if nodata is None else nodata,dst_transform=g['transform'],dst_crs=g['crs'],
                  dst_nodata=np.nan,resampling=Resampling.nearest)
    result[~g['inside']] = np.nan
    return result


def rain(start_year,end_year,progress):
    folder = e.ENV/'rainfall'; folder.mkdir(parents=True,exist_ok=True)
    # Representative native-resolution cells, not a fictitious fine-scale rainfall surface.
    points = [(79.0,10.5),(79.0,11.0),(79.625,10.5),(79.625,11.0)]
    series,sources = [],[]
    for i,(lng,lat) in enumerate(points):
        progress(f'Rainfall cell {i+1}/{len(points)}')
        params = {'parameters':'PRECTOTCORR','community':'AG','longitude':lng,'latitude':lat,
                  'start':f'{start_year}0101','end':f'{end_year}1231','format':'JSON','time-standard':'UTC'}
        url = 'https://power.larc.nasa.gov/api/temporal/daily/point'
        path = folder/f'raw_{lng}_{lat}_{start_year}_{end_year}.json'
        if not path.exists(): atomic_json(path,get_json(url,params))
        payload = json.loads(path.read_text(encoding='utf-8'))
        values = payload['properties']['parameter']['PRECTOTCORR']
        daily = {day:float(v) if v is not None and float(v)>=0 else None for day,v in values.items()}
        months = e.monthly_rainfall(daily)
        series.append({'id':f'{lng}_{lat}','longitude':lng,'latitude':lat,'months':months,
                       'daily':[{'date':f'{d[:4]}-{d[4:6]}-{d[6:]}','mm':v} for d,v in sorted(daily.items())]})
        sources.append({'url':str(httpx.URL(url,params=params)),'sha256':checksum(path),'header':payload.get('header'),
                        'parameters':payload.get('parameters')})
    data = {'source':'NASA POWER · PRECTOTCORR','start_year':start_year,'end_year':end_year,'series':series,
            'note':'Bias-corrected reanalysis precipitation at coarse meteorological grid cells (approximately 0.5° × 0.625°), not local rain-gauge observations. UTC daily totals; incomplete months are not totalled.'}
    atomic_json(folder/'series.json',data)
    manifest = {'id':'rainfall','title':'Rainfall time series','status':'available','timescale':'Short term',
                'note':data['note'],'observed_at':f'{start_year}-01-01 / {end_year}-12-31','retrieved_at':now(),
                'records':sum(len(s['daily']) for s in series),'sources':sources,'layers':[]}
    atomic_json(folder/'manifest.json',manifest); return manifest


def soil(progress):
    folder = e.ENV/'soil'; folder.mkdir(parents=True,exist_ok=True)
    products = product_folder(folder)
    native = '+proj=igh +datum=WGS84 +units=m +no_defs'
    convert = Transformer.from_crs(4326,native,always_xy=True)
    xmin,ymin,xmax,ymax = boundary().bounds
    pts = [convert.transform(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    left = math.floor(min(p[0] for p in pts)/250)*250-500; right = math.ceil(max(p[0] for p in pts)/250)*250+500
    bottom = math.floor(min(p[1] for p in pts)/250)*250-500; top = math.ceil(max(p[1] for p in pts)/250)*250+500
    g = e.grid(); arrays,sources = {},[]
    # Surface soil for district screening. Six-depth site profiles remain available separately.
    for prop,divisor in [('sand',10),('silt',10),('clay',10),('bdod',100),('soc',10)]:
        progress(f'District soil: {prop}')
        coverage = f'{prop}_0-5cm_mean'; path = folder/f'{coverage}.tif'
        params = [('map',f'/map/{prop}.map'),('SERVICE','WCS'),('VERSION','2.0.1'),('REQUEST','GetCoverage'),
                  ('COVERAGEID',coverage),('FORMAT','image/tiff'),('SUBSET',f'X({left},{right})'),('SUBSET',f'Y({bottom},{top})')]
        url = str(httpx.URL('https://maps.isric.org/mapserv',params=params))
        if not path.exists():
            r = httpx.get(url,timeout=60); r.raise_for_status()
            if 'tiff' not in r.headers.get('content-type',''): raise ValueError('ISRIC returned non-raster response')
            temp = path.with_suffix('.part'); temp.write_bytes(r.content)
            with rasterio.open(temp) as check:
                if check.width*check.height > 4_000_000: raise ValueError('Soil response exceeds bounded district extent')
            temp.replace(path)
        arrays[prop] = local_band(path,g,native,nodata=0)/divisor
        sources.append({'coverage':coverage,'url':url,'sha256':checksum(path),'divisor':divisor,'native_crs':native})
    valid = np.isfinite(arrays['sand']) & np.isfinite(arrays['clay']) & np.isfinite(arrays['silt'])
    valid &= (abs(arrays['sand']+arrays['clay']+arrays['silt']-100) <= 5)
    if not valid.any(): raise ValueError('No physically valid soil texture cells; source is not marked available')
    # Transparent texture-only screening. It is deliberately NOT called Ksat or mm/h.
    proxy = np.divide(arrays['sand'],arrays['sand']+arrays['clay'],out=np.full(valid.shape,np.nan),
                      where=valid & ((arrays['sand']+arrays['clay'])>0))
    e.write_raster(products/'clay.tif',np.where(valid,arrays['clay'],np.nan),g,['clay_pct_0_5cm'])
    e.write_raster(products/'infiltration.tif',proxy,g,['sand_fraction_of_sand_plus_clay'])
    e.write_raster(products/'properties.tif',[arrays[k] for k in ('sand','silt','clay','bdod','soc')],g,
                   ['sand_pct','silt_pct','clay_pct','bulk_density_g_cm3','organic_carbon_g_kg'])
    note = 'SoilGrids 250 m surface-soil predictions, 0–5 cm. Infiltration indicator = sand/(sand+clay), an uncalibrated texture proxy, not permeability, infiltration rate or storage capacity. Structure, compaction, roots and management are unobserved.'
    layers = [e.layer_metadata('clay','Surface soil clay',products/'clay.tif','%',[0,100],note),
              e.layer_metadata('infiltration','Texture infiltration indicator',products/'infiltration.tif','dimensionless',[0,1],note)]
    manifest = {'id':'soil','title':'Soil & infiltration screening','status':'available','timescale':'Context','note':note,
                'observed_at':'Model climatological context; not a dated field observation','retrieved_at':now(),
                'records':int(valid.sum()),'sources':sources,'layers':layers}
    atomic_json(folder/'manifest.json',manifest); return manifest


def remote_band(asset,g,folder,name):
    path = folder/f'{name}.tif'
    if path.exists(): return local_band(path,g)
    # Read bounded COG windows via reduced-resolution overviews, preserving nearest sampling.
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_TIMEOUT='60',GDAL_HTTP_MAX_RETRY='2',
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',VSI_CACHE=True):
        with rasterio.open(asset['href'],overview_level=2) as src:
            with WarpedVRT(src,crs=g['crs'],transform=g['transform'],width=g['width'],height=g['height'],
                           src_nodata=0,nodata=e.NODATA,resampling=Resampling.nearest,dtype='float32') as vrt:
                values = vrt.read(1,masked=True).filled(np.nan)
    values[~g['inside']] = np.nan
    e.write_raster(path,values,g,[name]); return values


def satellite(year,progress):
    folder = e.ENV/'satellite'; folder.mkdir(parents=True,exist_ok=True)
    products = product_folder(folder)
    g = e.grid(); seasons,sources,layers = [],[],[]
    region = boundary()
    for quarter in range(1,5):
        start_month,end_month = (quarter-1)*3+1,quarter*3
        start = f'{year}-{start_month:02d}-01'; end=f'{year}-{end_month:02d}-{calendar.monthrange(year,end_month)[1]}'
        progress(f'Sentinel-2: finding clear scenes for {year} Q{quarter}')
        query = {'collections':['sentinel-2-c1-l2a'],'bbox':list(region.bounds),
                 'datetime':f'{start}T00:00:00Z/{end}T23:59:59Z','limit':100}
        response=httpx.post('https://earth-search.aws.element84.com/v1/search',json=query,timeout=60)
        response.raise_for_status(); search=response.json()
        atomic_json(folder/f'search_{year}_q{quarter}.json',search)
        candidates = sorted(search.get('features',[]),key=lambda f:f['properties'].get('eo:cloud_cover',100))
        chosen = {}
        for item in candidates:
            p = item['properties']; tile = p.get('grid:code',item['id'].split('_')[1])
            if tile in chosen or p.get('eo:cloud_cover',100)>70: continue
            if shape(item['geometry']).intersection(region).area/region.area < .015: continue
            chosen[tile] = item
        ndvi,ndwi = np.full(g['inside'].shape,np.nan,dtype='float32'),np.full(g['inside'].shape,np.nan,dtype='float32')
        items = []
        for item in list(chosen.values())[:6]:
            progress(f"Sentinel-2 {year} Q{quarter}: {item['id']}")
            scene_folder = folder/item['id']; scene_folder.mkdir(exist_ok=True)
            try:
                assets=item['assets']; scl=remote_band(assets['scl'],g,scene_folder,'scl')
                # SCL 4 vegetation, 5 non-vegetated, 6 water; reject shadows/clouds/snow/uncertain.
                clear=np.isin(scl,[4,5,6])
                bands={}
                for name in ('red','green','nir'):
                    raw=remote_band(assets[name],g,scene_folder,name)
                    info=assets[name]['raster:bands'][0]
                    bands[name]=raw*info['scale']+info.get('offset',0)
                a=e.normalised_difference(bands['nir'],bands['red'],clear)
                b=e.normalised_difference(bands['green'],bands['nir'],clear)
                take = ~np.isfinite(ndvi)&np.isfinite(a)&np.isfinite(b)
                ndvi[take]=a[take]; ndwi[take]=b[take]
                record={'id':item['id'],'datetime':item['properties'].get('datetime'),'cloud_cover':item['properties'].get('eo:cloud_cover'),
                        'collection':item['collection'],'bands':{key:{'url':assets[key]['href'],'raster_bands':assets[key].get('raster:bands'),
                            'cached_sha256':checksum(scene_folder/f'{key}.tif')} for key in ('red','green','nir','scl')}}
                items.append(record); sources.append(record)
            except Exception as exc:
                items.append({'id':item['id'],'error':str(exc)[:500]})
        if not np.isfinite(ndvi).any(): raise ValueError(f'No usable clear pixels acquired for {year} Q{quarter}')
        for key,values in [('ndvi',ndvi),('ndwi',ndwi)]:
            path=products/f'{key}_{year}_q{quarter}.tif'; e.write_raster(path,values,g,[key])
            if quarter==4:
                latest=products/f'{key}.tif'; e.write_raster(latest,values,g,[key])
                layers.append(e.layer_metadata(key,f'{key.upper()} · {year} Q4',latest,'index',[-1,1],
                    'Representative clear-pixel mosaic; acquisition dates vary by tile. Not a quarterly mean or continuous monitoring.'))
        seasons.append({'label':f'{year} Q{quarter}','start':start,'end':end,'coverage_percent':round(float(np.isfinite(ndvi).sum()/g['inside'].sum()*100),2),
                        'ndvi_mean':round(float(np.nanmean(ndvi)),4),'ndwi_mean':round(float(np.nanmean(ndwi)),4),'scenes':items,
                        'ndvi_file':(products/f'ndvi_{year}_q{quarter}.tif').relative_to(e.ENV).as_posix(),
                        'ndwi_file':(products/f'ndwi_{year}_q{quarter}.tif').relative_to(e.ENV).as_posix()})
    manifest={'id':'satellite','title':'NDVI / NDWI seasonal observations','status':'available','timescale':'Short term','retrieved_at':now(),
              'observed_at':str(year),'records':len(sources),'sources':sources,'seasons':seasons,'layers':layers,
              'note':'Sentinel-2 Collection 1 L2A via Earth Search. Scale/offset from each asset; SCL 4/5/6 only. NDVI=(NIR−red)/(NIR+red), McFeeters NDWI=(green−NIR)/(green+NIR). 250 m nearest-sampled overview grid; not native 10 m maps. Four representative mosaics; clouds remain gaps.'}
    atomic_json(folder/'manifest.json',manifest); return manifest


def history(progress):
    folder=e.ENV/'history'; folder.mkdir(parents=True,exist_ok=True)
    products = product_folder(folder)
    g=e.grid(); sources,layers=[],[]
    # Pinned corrected v1.5; satellite-era history is never palaeochannel proof.
    for key in ('occurrence','transitions'):
        progress(f'Historical surface water: {key}, 1984–2024')
        url=f'https://s3.waw4-1.cloudferro.com/swift/v1/global-surface-water/download2024/Aggregated/VER1-5/{key}/{key}_70E_20N_v1_5_2024.tif'
        raw=folder/f'jrc_{key}_v1_5.tif'
        if not raw.exists():
            tmp=raw.with_suffix('.part')
            with httpx.stream('GET',url,timeout=120,follow_redirects=True) as response:
                response.raise_for_status()
                with tmp.open('wb') as out:
                    size=0
                    for chunk in response.iter_bytes():
                        size+=len(chunk)
                        if size > 250*1024*1024: raise ValueError('JRC tile exceeds 250 MiB limit')
                        out.write(chunk)
            tmp.replace(raw)
        values=local_band(raw,g,nodata=255)
        limit=100 if key=='occurrence' else 10
        values[(values<0)|(values>limit)]=np.nan
        path=products/f'{key}.tif'; e.write_raster(path,values,g,[key])
        layers.append(e.layer_metadata(key,'Water occurrence · 1984–2024' if key=='occurrence' else 'Historical water transitions',path,
                     '%' if key=='occurrence' else 'class',[0,limit], 'Landsat-derived JRC v1.5, 1984–2024. Source: EC JRC/Google. Satellite-era water change does not establish an ancient river course.'))
        sources.append({'url':url,'sha256':checksum(raw),'version':'JRC GSW 1.5','period':'1984–2024'})
    manifest={'id':'history','title':'Historical landscape & water change','status':'available','timescale':'Long term','retrieved_at':now(),
              'observed_at':'1984–2024','records':2,'sources':sources,'layers':layers,
              'note':'Georeferenced JRC historical water maps. Lost-water classes are leads for landscape investigation, not confirmed palaeochannels. Older maps and dated field evidence can be imported separately.'}
    atomic_json(folder/'manifest.json',manifest); return manifest


def run(kinds=('rainfall','soil','satellite','history'),start_year=2024,end_year=2025):
    e.ENV.mkdir(parents=True,exist_ok=True)
    state={'status':'running','started_at':now(),'stage':'Preparing acquisition','completed':[],'errors':{},'progress':0}
    def save(stage): state['stage']=stage; atomic_json(e.ENV/'job.json',state); print(stage,flush=True)
    save('Starting bounded public-data acquisition')
    try:
        for i,kind in enumerate(kinds):
            state['progress']=round(i/len(kinds)*100)
            try:
                if kind=='rainfall': rain(start_year,end_year,save)
                elif kind=='soil': soil(save)
                elif kind=='satellite': satellite(end_year,save)
                elif kind=='history': history(save)
                state['completed'].append(kind)
            except Exception as exc:
                state['errors'][kind]=str(exc)[:1000]
        state.update(status='completed' if not state['errors'] else 'partial' if state['completed'] else 'failed',progress=100,finished_at=now())
        save('Acquisition finished; inspect source coverage and any errors')
    except Exception as exc:
        state.update(status='failed',error=str(exc)); save('Acquisition failed')
    return state
