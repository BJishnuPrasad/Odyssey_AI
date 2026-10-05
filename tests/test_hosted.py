import json
import pytest
from backend import database as db
from scripts import start_hosted


def test_public_seed_restores_and_preserves_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'RUNTIME', tmp_path)
    monkeypatch.setattr(start_hosted, 'RUNTIME', tmp_path)
    start_hosted.initialize_seed()
    runs = db.list_runs()
    assert len(runs) == 1 and runs[0]['status'] == 'completed'
    assert (tmp_path / 'runs' / runs[0]['id'] / 'terrain.tif').is_file()
    profile = next((tmp_path / 'heritage').glob('*/soil.json'))
    profile.write_text('{"preserved": true}')
    db.create_run('new-user-run', {})
    start_hosted.initialize_seed()
    assert json.loads(profile.read_text()) == {'preserved': True}
    assert db.get_run('new-user-run') is not None


def test_corrupt_seed_rejected_before_copy(tmp_path, monkeypatch):
    runtime = tmp_path / 'runtime'
    seed = tmp_path / 'seed'
    seed.mkdir()
    (seed / 'bad.json').write_text('{}')
    (seed / 'seed.json').write_text(json.dumps({'files': {'bad.json': {'sha256': 'invalid'}}}))
    monkeypatch.setattr(db, 'RUNTIME', runtime)
    monkeypatch.setattr(start_hosted, 'RUNTIME', runtime)
    with pytest.raises(ValueError, match='Invalid deployment seed'):
        start_hosted.initialize_seed(seed)
    assert not (runtime / '.hosted-seed.json').exists()


def test_hosted_mode_reported(monkeypatch):
    from backend.api import health
    monkeypatch.setenv('GEODYSSEY_HOSTED_DEMO', '1')
    assert health()['hosted_demo'] is True
    monkeypatch.delenv('GEODYSSEY_HOSTED_DEMO')
    assert health()['hosted_demo'] is False
