import json
import struct
import pytest
from fastapi.testclient import TestClient
from backend import api, heritage as h, database as db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(h, 'RUNTIME', tmp_path)
    monkeypatch.setattr(db, 'RUNTIME', tmp_path)
    monkeypatch.setattr(api, 'RUNTIME', tmp_path)
    with TestClient(api.app) as value:
        yield value


def triangle_glb(uri=None):
    document = {'asset': {'version':'2.0'}, 'scene':0, 'scenes':[{'nodes':[0]}],
        'nodes':[{'mesh':0}], 'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],
        'buffers':[{'byteLength':36}], 'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[0,0,0],'max':[1,1,0]}]}
    if uri:
        document['buffers'][0]['uri'] = uri
    meta = json.dumps(document).encode()
    meta += b' ' * (-len(meta)%4)
    binary = struct.pack('<9f', 0,0,0, 1,0,0, 0,1,0)
    return struct.pack('<4sII',b'glTF',2,28+len(meta)+len(binary))+struct.pack('<II',len(meta),0x4E4F534A)+meta+struct.pack('<II',len(binary),0x004E4942)+binary


def test_resolve_alias_and_unknown(client):
    result = client.get('/api/heritage/resolve',params={'q':'show me Brihadeeswarar Temple in 3D'}).json()
    assert [s['id'] for s in result['matches']] == ['relation-6668806']
    assert client.get('/api/heritage/resolve',params={'q':'nonexistent place'}).json()['matches'] == []
    assert len(client.get('/api/heritage/resolve',params={'q':'Temple'}).json()['matches']) > 1
    assert client.get('/api/heritage/unknown').status_code == 404


def test_cached_asset_and_honest_missing_soil(client):
    first = client.get('/api/heritage/relation-6668806').json()
    again = client.get('/api/heritage/relation-6668806').json()
    assert first['asset'] == again['asset']
    assert first['asset']['tier'] == 1
    assert first['soil']['confidence'] == 'unavailable'
    assert first['soil']['cultural_layer_cm'] is None
    assert all(l['clay_pct'] is None for l in first['soil']['layers'])
    assert len(first['soil']['layers']) == 6


def test_search_across_types_and_filters(client):
    assert len(client.get('/api/library',params={'kind':'site'}).json()['items']) == 9
    assert client.get('/api/library',params={'q':'near-infrared'}).json()['items'][0]['id'] == 'ndvi'
    results = client.get('/api/library',params={'typology':'temple','confidence':'documented history'}).json()['items']
    assert len(results) == 2
    assert client.get('/api/library',params={'q':'xxxxxxxxxxxx'}).json()['items'] == []


def test_glb_persistence_and_rejection(client):
    url = '/api/heritage/relation-6668806/model'
    assert client.put(url, content=b'not a model').status_code == 422
    assert client.put(url, content=triangle_glb('https://example.com/private.bin')).status_code == 422
    response = client.put(url, content=triangle_glb())
    assert response.status_code == 200
    record = response.json()
    assert record['tier'] == 3
    assert client.get(record['url']).content == triangle_glb()
    assert client.get('/api/heritage/relation-6668806').json()['asset'] == record
    assert client.delete(url).json()['tier'] == 1
    assert client.get(record['url']).status_code == 200  # preserve previous upload
    assert client.get(url+'/anything.glb').status_code == 404


def test_field_profile_validation(client):
    url = '/api/heritage/relation-6668806/soil'
    profile = client.get('/api/heritage/relation-6668806').json()['soil']
    profile.update(source_kind='borehole',source='Located test log, BH-1',confidence='field data supplied')
    profile['layers'][0]['clay_pct'] = 101
    assert client.put(url,json=profile).status_code == 422
    profile['layers'][0]['clay_pct'] = 35
    profile['cultural_layer_cm'] = [20,30]
    assert client.put(url,json=profile).status_code == 422
    profile['cultural_layer_evidence'] = 'Test-only logged interval'
    assert client.put(url,json=profile).status_code == 200
    result = client.get('/api/heritage/relation-6668806').json()['soil']
    assert result['layers'][0]['clay_pct'] == 35
    assert result['confidence'] == 'field data supplied'
    profile['site_id'] = 'way-555516027'
    assert client.put(url,json=profile).status_code == 422
