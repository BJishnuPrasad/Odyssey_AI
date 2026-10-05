"""Acquire bounded SoilGrids WCS rasters, sample actual site coordinates, cache provenance.

No account required. Run explicitly; page views never make environmental API calls.
The 30 small district subsets are retained for reproducibility and resumable acquisition.
"""
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import numpy as np
import rasterio
from rasterio.warp import transform
from pyproj import Transformer
from backend import heritage as h

PROPERTIES = {'sand': ('sand_pct', 10), 'silt': ('silt_pct', 10), 'clay': ('clay_pct', 10),
              'bdod': ('bulk_density_g_cm3', 100), 'soc': ('organic_carbon_g_kg', 10)}
SOIL_CRS = '+proj=igh +datum=WGS84 +units=m +no_defs'


def acquire(prop, top, bottom, sites, folder):
    coverage = f'{prop}_{top}-{bottom}cm_mean'
    path = folder / f'{coverage}.tif'
    projection = Transformer.from_crs(4326, SOIL_CRS, always_xy=True)
    xy = [projection.transform(*s['coordinates']) for s in sites]
    xs, ys = zip(*xy)
    left, right = math.floor((min(xs)-500)/250)*250, math.ceil((max(xs)+500)/250)*250
    bottom_y, top_y = math.floor((min(ys)-500)/250)*250, math.ceil((max(ys)+500)/250)*250
    params = [('map', f'/map/{prop}.map'), ('SERVICE', 'WCS'), ('VERSION', '2.0.1'),
              ('REQUEST', 'GetCoverage'), ('COVERAGEID', coverage), ('FORMAT', 'image/tiff'),
              ('SUBSET', f'X({left},{right})'), ('SUBSET', f'Y({bottom_y},{top_y})')]
    url = str(httpx.URL('https://maps.isric.org/mapserv', params=params))
    if not path.exists():
        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        if 'tiff' not in response.headers.get('content-type', ''):
            raise ValueError(f'{coverage}: service returned non-raster data')
        temporary = path.with_suffix('.part')
        temporary.write_bytes(response.content)
        with rasterio.open(temporary) as raster:
            if raster.width*raster.height > 2_000_000 or abs(raster.transform.a-250) > 2:
                raise ValueError('Unexpected raster extent or CRS')
        temporary.replace(path)
    result = {}
    with rasterio.open(path) as raster:
        for s in sites:
            # Always transform using the returned raster CRS, not assumed pixel order.
            # WCS GeoTIFF may omit the custom EPSG:152160 CRS. DescribeCoverage
            # declares native Interrupted Goode Homolosine; ISRIC documents +proj=igh.
            x, y = transform('EPSG:4326', raster.crs or SOIL_CRS, [s['coordinates'][0]], [s['coordinates'][1]])
            value = next(raster.sample([(x[0], y[0])], masked=True))[0]
            if not np.ma.is_masked(value) and np.isfinite(value) and value > 0:
                result[s['id']] = round(float(value)/PROPERTIES[prop][1], 3)
    return {'coverage': coverage, 'path': str(path), 'url': url,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'values': result,
            'property': PROPERTIES[prop][0], 'top_cm': top, 'bottom_cm': bottom}


def main():
    sites = h.profiles()
    folder = h.RUNTIME / 'heritage' / 'soilgrids-wcs'
    folder.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(acquire, prop, a, b, sites, folder) for prop in PROPERTIES for a,b in h.DEPTHS]
        for f in as_completed(futures):
            try:
                item = f.result(); results.append(item)
                print(item['coverage'], len(item['values']), 'site values', flush=True)
            except Exception as exc:
                errors.append(str(exc)); print('UNAVAILABLE:', exc, flush=True)
    stamp = h.now()
    saved = []
    for s in sites:
        layers = []
        for a,b in h.DEPTHS:
            layer = {'top_cm': a, 'bottom_cm': b, 'label': 'SoilGrids modelled depth interval'}
            for item in results:
                if item['top_cm'] == a and s['id'] in item['values']:
                    layer[item['property']] = item['values'][s['id']]
            layers.append(layer)
        if not any(len(layer) > 3 for layer in layers):
            continue
        current = h.soil_profile(s['id'])
        if current['source_kind'] not in ('unavailable','soilgrids'):
            continue  # Do not overwrite user-supplied field logs.
        try:
            h.save_soil(s['id'], {'schema_version':1, 'site_id':s['id'], 'source_kind':'soilgrids',
                'source':'ISRIC SoilGrids 2.0 · WCS mean predictions · CC BY 4.0',
                'source_url':'https://docs.isric.org/globaldata/soilgrids/index.html',
                'retrieved_at':stamp, 'resolution_m':250, 'confidence':'model estimate',
                'caveat':'Regional model predictions, not archaeological strata or excavation results. Urban fill may differ. Prediction intervals were not acquired; no numerical confidence is claimed. Missing properties remain empty.', 'layers':layers})
            saved.append(s['id'])
        except ValueError as exc:
            errors.append(f"{s['id']}: {exc}")
    h.atomic_json(folder / 'manifest.json', {'retrieved_at':stamp, 'sources':results, 'errors':errors, 'saved_sites':saved,
        'unit_conversion':PROPERTIES, 'method':'Nearest native-grid cell at each OSM representative point; no interpolation'})
    print(json.dumps({'profiles_saved':len(saved), 'errors':errors}), flush=True)


if __name__ == '__main__':
    main()
