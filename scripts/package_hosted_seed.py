"""Package only public acquired evidence and a field-free completed run for hosting.

Deliberately excludes the SQLite database, uploaded GLBs, contributor field
records, imported historical interpretations, logs and raw download caches.
"""
import json
import shutil
from pathlib import Path
from backend import database as db
from backend.catalog import checksum, read_json
from backend.settings import ROOT, RUNTIME, DERIVED


def package(destination):
    destination=Path(destination)
    if destination.exists():
        raise ValueError('Use a new output directory; do not overwrite a published seed')
    runs=[r for r in db.list_runs() if r['status']=='completed']
    if not runs: raise ValueError('A completed run is required')
    run=runs[0]
    output=RUNTIME/'runs'/run['id']
    for filename in ('validation_records.json','historical_features.geojson'):
        if (output/filename).exists():
            raise ValueError('Selected run includes contributor records; choose a public-only run before packaging')
    files={}
    def copy(source,relative):
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        files[relative]={'sha256':checksum(target),'bytes':target.stat().st_size}
    for name in ('water.geojson','landuse.geojson','manifest.json','heritage_footprints.json'):
        copy(DERIVED/name,'derived/'+name)
    for kind in ('rainfall','soil','satellite','history'):
        root=RUNTIME/'environment'
        manifest=root/kind/'manifest.json'
        data=read_json(manifest)
        copy(manifest,f'runtime/environment/{kind}/manifest.json')
        references={layer['file'] for layer in data.get('layers',[])}
        for season in data.get('seasons',[]):
            references.update([season['ndvi_file'],season['ndwi_file']])
        if kind=='rainfall': references.add('rainfall/series.json')
        for name in sorted(references): copy(root/name,'runtime/environment/'+name)
    for source in sorted((RUNTIME/'heritage').glob('*/soil.json')):
        if read_json(source)['source_kind']=='soilgrids':
            copy(source,f'runtime/heritage/{source.parent.name}/soil.json')
    names={'terrain.tif','zones.geojson','report.json','overlay.png','evidence.png','sites.geojson',
           'environment.json','rainfall.json','comparisons.json'}
    names.update(p.name for p in output.glob('context_*.tif'))
    names.update(p.name for p in output.glob('context_*.png'))
    for name in sorted(names): copy(output/name,f'runtime/runs/{run["id"]}/{name}')
    manifest={'schema_version':1,'run':{k:run[k] for k in ('id','created_at','finished_at','parameters')},'files':files}
    (destination/'seed.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Packaged {len(files)} public files ({sum(f["bytes"] for f in files.values())/1024**2:.2f} MiB)')


if __name__=='__main__':
    package(ROOT/'deployment/seed')
