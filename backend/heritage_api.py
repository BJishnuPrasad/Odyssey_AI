import re
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import ValidationError
from . import heritage as h
from .heritage_schema import SoilProfile

router = APIRouter(prefix="/api")


def require_site(site_id):
    try:
        return h.site(site_id)
    except KeyError:
        raise HTTPException(404, "Heritage site not found")


@router.get("/library")
def library(q: str = Query(default="", max_length=300), kind: str = "", region: str = "", period: str = "", typology: str = "", confidence: str = ""):
    items = h.search(q, kind, region, period, typology, confidence)
    sites = h.profiles()
    return {"items": items, "facets": {key: sorted({s[key] for s in sites}) for key in ("region", "period", "typology", "confidence")}}


@router.get("/heritage/resolve")
def resolve(q: str = Query(min_length=1, max_length=300)):
    return {"matches": h.lookup(q)}


@router.get("/heritage/{site_id}")
def detail(site_id: str):
    profile = require_site(site_id)
    soil = h.soil_profile(site_id)
    upper = soil['layers'][0]
    texture = ', '.join(f"{label} {upper[key]:g}%" for key, label in
                      [('sand_pct', 'sand'), ('silt_pct', 'silt'), ('clay_pct', 'clay')] if upper[key] is not None)
    composition = f" Upper interval {upper['top_cm']:g}–{upper['bottom_cm']:g} cm: {texture}." if texture else " Soil composition is unavailable."
    return {"site": profile, "asset": h.asset(site_id), "soil": soil,
            "summary": f"{profile['title']} · {profile['typology']} · {profile['period']}. {profile['summary']} Soil evidence: {soil['confidence']}.{composition} Historical documentation does not verify the 3D geometry or subsurface."}


@router.put("/heritage/{site_id}/soil")
def import_soil(site_id: str, profile: SoilProfile):
    require_site(site_id)
    try:
        return h.save_soil(site_id, profile.model_dump())
    except (ValueError, ValidationError) as exc:
        raise HTTPException(422, str(exc))


@router.put("/heritage/{site_id}/model")
async def upload_model(site_id: str, request: Request):
    require_site(site_id)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 25*1024*1024:
            raise HTTPException(413, "Model exceeds 25 MiB")
    try:
        return h.save_glb(site_id, bytes(data))
    except (ValueError, RecursionError, TypeError, AttributeError, KeyError) as exc:
        raise HTTPException(422, str(exc) or "Malformed model")


@router.get("/heritage/{site_id}/model/{name}")
def model_file(site_id: str, name: str):
    require_site(site_id)
    if not re.fullmatch(r"[0-9a-f]{64}\.glb", name):
        raise HTTPException(404, "Model not found")
    path = h.RUNTIME / "heritage" / site_id / name
    if not path.exists():
        raise HTTPException(404, "Model not found")
    return FileResponse(path, media_type="model/gltf-binary")


@router.delete("/heritage/{site_id}/model")
def use_reconstruction(site_id: str):
    require_site(site_id)
    # Uploaded content-addressed binary is retained; only the active selection changes.
    (h.RUNTIME / "heritage" / site_id / "upload.json").unlink(missing_ok=True)
    return h.asset(site_id)
