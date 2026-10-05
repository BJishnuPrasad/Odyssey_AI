import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from fastapi.testclient import TestClient
from backend import environment as e, api, database as db, heritage
from backend.acquisition import local_band


def test_rainfall_missing_days_and_leap_year():
    daily={f'202402{day:02d}':1 for day in range(1,30)}
    month=e.monthly_rainfall(daily)[0]
    assert month['total_mm']==29 and month['expected_days']==29
    daily['20240215']=-999
    month=e.monthly_rainfall(daily)[0]
    assert month['total_mm'] is None and month['valid_days']==28


def test_indices_mask_clouds_zero_and_negative_reflectance():
    a=np.array([[.6,.6,0,-.1]],dtype='float32'); b=np.array([[.2,.2,0,.2]],dtype='float32')
    result=e.normalised_difference(a,b,np.array([[True,False,True,True]]))
    assert result[0,0]==pytest.approx(.5)
    assert np.isnan(result[0,1:]).all()


def test_reference_metrics_ties_and_insufficient_labels():
    assert e.metrics([.8]*25,[1]*25)['auc'] is None
    assert e.metrics([.2]*10+[.8]*10,[0]*10+[1]*10)['auc']==1
    assert e.metrics([.5]*20,[0]*10+[1]*10)['auc']==.5
    assert e.metrics([.8]*10+[.2]*10,[0]*10+[1]*10)['auc']==0


def test_reference_sampling_retains_sparse_water_and_is_reproducible():
    values=np.zeros((40,40),dtype='float32')
    # Narrow water features away from the old fixed lattice points.
    values[::8,::8]=95
    valid=np.ones(values.shape,dtype=bool)
    values[0,0]=50  # Intermediate occurrence is never a label.
    valid[0,8]=False
    selected=e.reference_cells(values,valid,4)
    assert selected==e.reference_cells(values,valid,4)
    labels=[int(values[r,c]>=90) for r,c in selected]
    assert sum(labels)==23 and len(labels)==46
    assert len({(r//4,c//4) for r,c in selected})==len(selected)
    assert all(valid[r,c] and (values[r,c]==0 or values[r,c]>=90) for r,c in selected)


def test_comparisons_are_frozen_with_the_run(tmp_path,monkeypatch):
    def original(*args): return {'status':'original','points':[], 'accuracy':None}
    monkeypatch.setattr(e,'evaluate_run',original)
    e.freeze_comparisons(tmp_path)
    saved=json.loads((tmp_path/'comparisons.json').read_text())
    monkeypatch.setattr(e,'evaluate_run',lambda *args: {'status':'changed'})
    assert len(saved['results'])==4
    assert saved['results']['satellite:surface_water_presence']['status']=='original'


def test_soil_without_embedded_crs_is_reprojected(tmp_path):
    native='+proj=igh +datum=WGS84 +units=m +no_defs'
    from pyproj import Transformer
    x,y=Transformer.from_crs(4326,native,always_xy=True).transform(79.13,10.78)
    p=tmp_path/'soil.tif'
    with rasterio.open(p,'w',driver='GTiff',width=12,height=12,count=1,dtype='uint16',transform=from_origin(x-1500,y+1500,250,250)) as f:
        f.write(np.full((12,12),355,dtype='uint16'),1)
    result=local_band(p,e.grid(),native,0)
    assert np.isfinite(result).any()
    assert np.nanmin(result)==355


def record(**updates):
    return {'id':'test-1','longitude':79.13,'latitude':10.78,'observed_on':'2025-01-01',
            'target':'surface_water_presence','value':1,'source':'Independent field notebook reference',
            'method':'Located site observation','independence_statement':'Observed independently of the terrain model.',**updates}


def test_field_validation_is_located_dated_and_deduplicated():
    assert len(e.validate_records([record()]))==1
    with pytest.raises(ValueError): e.validate_records([record(value=.5)])
    with pytest.raises(ValueError): e.validate_records([record(latitude=20)])
    with pytest.raises(ValueError): e.validate_records([record(),record(id='duplicate')])
    with pytest.raises(ValueError): e.validate_records([record(observed_on='2099-01-01')])


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(e,'ENV',tmp_path/'environment')
    monkeypatch.setattr(db,'RUNTIME',tmp_path)
    monkeypatch.setattr(api,'RUNTIME',tmp_path)
    monkeypatch.setattr(heritage,'RUNTIME',tmp_path)
    with TestClient(api.app) as c: yield c


def test_imports_and_invalid_reference_target(client):
    assert client.put('/api/environment/field-records',json=[record()]).status_code==200
    assert len(client.get('/api/environment').json()['field_records'])==1
    bad={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[79.13,10.78]},'properties':{}}]}
    assert client.put('/api/environment/historical-features',json=bad).status_code==422
    bad['features'][0]['properties']={'title':'Test historical location','source':'Test map reference','period':'Undated test','interpretation':'Test candidate','confidence':'candidate'}
    assert client.put('/api/environment/historical-features',json=bad).status_code==200
    assert client.get('/api/environment/historical-features').json()['features']
    assert client.get('/api/environment/image/unknown').status_code==404
    assert client.post('/api/environment/acquire',json={'start_year':2025,'end_year':2099}).status_code==422


@pytest.mark.parametrize('geometry',[
    {'type':'Point','coordinates':[79.13]},
    {'type':'Polygon','coordinates':[[[79.13,10.78],[79.14,10.79]]]},
    {'type':'LineString','coordinates':[[79.13,10.78]]},
    {'type':'Point','coordinates':None},
])
def test_malformed_history_returns_validation_error(client,geometry):
    body={'type':'FeatureCollection','features':[{'type':'Feature','geometry':geometry,
          'properties':{'title':'Test','source':'Test record','period':'2025','interpretation':'Candidate','confidence':'candidate'}}]}
    assert client.put('/api/environment/historical-features',json=body).status_code==422
    assert client.get('/api/environment/historical-features').json()['features']==[]


def test_acquisition_start_failure_releases_lock(client,monkeypatch):
    from backend import environment_api as module
    def fail(*args): raise OSError('Simulated unwritable job file')
    monkeypatch.setattr(module,'atomic_json',fail)
    with pytest.raises(OSError,match='Simulated'):
        client.post('/api/environment/acquire',json={})
    assert not module.acquire_lock.locked()


def test_snapshot_keeps_source_versions(tmp_path,monkeypatch):
    monkeypatch.setattr(e,'ENV',tmp_path/'environment')
    p=e.ENV/'rainfall';p.mkdir(parents=True)
    e.atomic_json(p/'series.json',{'test':'first'})
    e.atomic_json(p/'manifest.json',{'id':'rainfall','layers':[]})
    out=tmp_path/'run';out.mkdir()
    snap=e.snapshot(out)
    e.atomic_json(p/'series.json',{'test':'second'})
    assert json.loads((out/'rainfall.json').read_text())=={'test':'first'}
    assert snap['rainfall_sha256']!=e.checksum(p/'series.json')


def test_snapshot_rejects_missing_or_modified_published_raster(tmp_path,monkeypatch):
    monkeypatch.setattr(e,'ENV',tmp_path/'environment')
    folder=e.ENV/'soil';folder.mkdir(parents=True)
    manifest={'id':'soil','layers':[{'id':'clay','file':'soil/clay.tif','sha256':'expected-source-hash'}]}
    e.atomic_json(folder/'manifest.json',manifest)
    output=tmp_path/'run';output.mkdir()
    with pytest.raises(ValueError,match='missing'): e.snapshot(output)
    (folder/'clay.tif').write_bytes(b'changed raster content')
    with pytest.raises(ValueError,match='differs from its source manifest'): e.snapshot(output)


def test_failed_refresh_preserves_published_products(tmp_path,monkeypatch):
    from backend import acquisition as a
    monkeypatch.setattr(e,'ENV',tmp_path)
    folder=tmp_path/'history';folder.mkdir()
    published=folder/'occurrence.tif';published.write_bytes(b'previous successful raster')
    original={'id':'history','layers':[{'file':'history/occurrence.tif'}]}
    e.atomic_json(folder/'manifest.json',original)
    for key in ('occurrence','transitions'):
        (folder/f'jrc_{key}_v1_5.tif').write_bytes(b'cached source')
    g={'inside':np.ones((2,2),dtype=bool)}
    monkeypatch.setattr(e,'grid',lambda:g)
    def read(path,*args,**kwargs):
        if 'transitions' in path.name: raise ValueError('simulated source failure')
        return np.ones((2,2),dtype='float32')
    monkeypatch.setattr(a,'local_band',read)
    monkeypatch.setattr(e,'write_raster',lambda path,*args:path.write_bytes(b'new raster'))
    monkeypatch.setattr(e,'layer_metadata',lambda *args:{'id':args[0]})
    with pytest.raises(ValueError,match='simulated'): a.history(lambda stage:None)
    assert published.read_bytes()==b'previous successful raster'
    assert json.loads((folder/'manifest.json').read_text())==original
