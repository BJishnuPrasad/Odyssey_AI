from concurrent.futures import Future
from fastapi.testclient import TestClient
import pytest
from backend import api, database as db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "RUNTIME", tmp_path)
    monkeypatch.setattr(api, "RUNTIME", tmp_path)
    with TestClient(api.app) as client:
        yield client


def test_health_catalog_and_missing_run(client):
    assert client.get('/api/health').json()['database'] == 'SQLite'
    assert client.get('/api/catalog').json()['datasets']
    assert client.get('/api/runs/unknown').status_code == 404


def test_invalid_parameters_rejected(client):
    assert client.post('/api/runs', json={'resolution_m': 1}).status_code == 422
    assert client.post('/api/runs', json={'slope_weight': 2}).status_code == 422


def test_queued_duplicate_and_artifact_gating(client, monkeypatch):
    monkeypatch.setattr(api.app.state.executor, 'submit', lambda *args: Future())
    response = client.post('/api/runs', json={})
    assert response.status_code == 202
    run_id = response.json()['id']
    assert client.post('/api/runs', json={}).status_code == 409
    assert client.get(f'/api/runs/{run_id}/artifacts/report.json').status_code == 409


def test_failed_run_never_returns_previous_report(client, monkeypatch):
    db.create_run('previous', {'resolution_m': 250, 'slope_weight': 0.55})
    db.update_run('previous', status='completed', summary={'sentinel': True})
    db.create_run('failure', {'resolution_m': 250, 'slope_weight': 0.55})
    def fail(*args):
        raise ValueError('Missing DEM')
    monkeypatch.setattr(api, 'execute', fail)
    api.worker('failure', {})
    failed = client.get('/api/runs/failure').json()
    assert failed['status'] == 'failed'
    assert failed['summary'] is None
    assert 'Missing DEM' in failed['error']
    assert client.get('/api/runs/failure/artifacts/report.json').status_code == 409


def test_restart_marks_unfinished_runs_failed(client):
    db.create_run('interrupted', {'resolution_m': 250, 'slope_weight': 0.55})
    db.initialize()
    assert db.get_run('interrupted')['status'] == 'failed'


def test_layer_allowlist(client):
    assert client.get('/api/layers/secrets').status_code == 404
