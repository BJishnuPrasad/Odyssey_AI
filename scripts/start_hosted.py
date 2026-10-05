"""Idempotent first-boot seeding, then one Uvicorn process on Render's PORT."""
import json
import os
import shutil
from pathlib import Path
from backend import database as db
from backend.catalog import checksum, read_json
from backend.heritage import atomic_json
from backend.settings import ROOT, RUNTIME


def initialize_seed(seed=None):
    seed=Path(seed or ROOT/'deployment/seed').resolve()
    marker=RUNTIME/'.hosted-seed.json'
    db.initialize(recover=False)
    if marker.exists(): return
    manifest=read_json(seed/'seed.json')
    # Validate everything before copying; reject corrupt or escaping seed paths.
    for relative,info in manifest['files'].items():
        source=(seed/relative).resolve()
        if not source.is_relative_to(seed) or not source.is_file() or checksum(source)!=info['sha256']:
            raise ValueError(f'Invalid deployment seed: {relative}')
        if relative.startswith('runtime/'):
            target=(RUNTIME/relative[len('runtime/'):]).resolve()
            if not target.is_relative_to(RUNTIME.resolve()): raise ValueError('Invalid runtime seed path')
    for relative in manifest['files']:
        if not relative.startswith('runtime/'): continue
        target=RUNTIME/relative[len('runtime/'):]
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_name(target.name+'.seed-tmp')
            shutil.copyfile(seed/relative,temporary)
            temporary.replace(target)
    r=manifest['run']
    if not db.get_run(r['id']):
        summary=read_json(RUNTIME/'runs'/r['id']/'report.json')
        with db.connection() as connection:
            connection.execute('INSERT INTO runs(id,created_at,finished_at,status,progress,stage,parameters,summary) VALUES(?,?,?,?,?,?,?,?)',
                (r['id'],r['created_at'],r['finished_at'],'completed',100,'Imported verified public snapshot',
                 json.dumps(r['parameters']),json.dumps(summary,allow_nan=False)))
    atomic_json(marker,{'schema_version':1,'run_id':r['id']})


if __name__=='__main__':
    initialize_seed()
    import uvicorn
    uvicorn.run('backend.api:app',host='0.0.0.0',port=int(os.environ.get('PORT','10000')),workers=1)
