"""Shared site lookup, persistent assets and evidence-aware learning catalogue."""
import hashlib
import json
import re
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .settings import ROOT, RUNTIME, DERIVED
from .catalog import curated_sites, read_json
from .heritage_schema import SoilProfile, AssetRecord, LibraryEntry, SiteProfile

CONTENT = ROOT / "content"
GENERATOR = "architecture-3"
DEPTHS = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)]


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def profiles():
    metadata = read_json(CONTENT / "sites.json")
    result = []
    for feature in curated_sites()[0]["features"]:
        props = feature["properties"]
        site_id = props["osm_id"].replace("/", "-")
        item = {"id": site_id, "kind": "site", "title": props["name"], "region": "Thanjavur",
                "period": "Unknown", "typology": "heritage", "confidence": "limited documentation",
                "summary": "Mapped heritage record; identity and chronology need independent verification.",
                "aliases": [], "references": [], **metadata.get(site_id, {}),
                "coordinates": feature["geometry"]["coordinates"], "osm_id": props["osm_id"],
                "location_quality": props["location_quality"]}
        item["references"] = [*item["references"], {"title": "OpenStreetMap record · ODbL", "url": "https://www.openstreetmap.org/" + props["osm_id"]}]
        result.append(SiteProfile.model_validate(item).model_dump(exclude_none=True))
    return result


def site(site_id):
    found = next((s for s in profiles() if s["id"] == site_id), None)
    if not found:
        raise KeyError(site_id)
    return found


def normalize(value):
    return " ".join(re.findall(r"\w+", value.casefold()))


def lookup(query):
    q = normalize(query)
    if not q:
        return []
    matches = []
    for s in profiles():
        names = [normalize(n) for n in [s["title"], *s["aliases"]]]
        if any(n in q or q in n for n in names):
            matches.append(s)
    return matches


def entries():
    result = profiles()
    for path in sorted((CONTENT / "library").glob("*.json")):
        result.append(LibraryEntry.model_validate(read_json(path)).model_dump())
    return result


def search(query="", kind="", region="", period="", typology="", confidence=""):
    tokens = normalize(query).split()
    found = []
    for entry in entries():
        if any(value and entry.get(key) != value for key, value in
               [("kind", kind), ("region", region), ("period", period), ("typology", typology), ("confidence", confidence)]):
            continue
        if all(t in normalize(json.dumps(entry, ensure_ascii=False)) for t in tokens):
            found.append(entry)
    return found


def soil_profile(site_id):
    site(site_id)
    path = RUNTIME / "heritage" / site_id / "soil.json"
    if path.exists():
        return SoilProfile.model_validate(read_json(path)).model_dump()
    return SoilProfile(site_id=site_id, source_kind="unavailable", source="ISRIC SoilGrids; no usable values available",
        source_url="https://docs.isric.org/globaldata/soilgrids/index.html", confidence="unavailable",
        caveat="Depth intervals are a sampling template, not observed horizons. No soil composition, bedrock or burial depth is inferred. SoilGrids at 250 m cannot resolve archaeological strata.",
        layers=[dict(top_cm=a, bottom_cm=b, label="No measurements") for a, b in DEPTHS]).model_dump()


def save_soil(site_id, data):
    site(site_id)
    profile = SoilProfile.model_validate(data)
    if profile.site_id != site_id:
        raise ValueError("Profile site_id does not match the selected site")
    if profile.source_kind == "unavailable":
        raise ValueError("Supply a real data source")
    # Source type controls the label; importing data does not certify a survey.
    profile.confidence = "model estimate" if profile.source_kind == "soilgrids" else "field data supplied"
    profile.caveat += " Imported data; provenance and spatial representativeness require review."
    atomic_json(RUNTIME / "heritage" / site_id / "soil.json", profile.model_dump())
    return profile.model_dump()


def procedural_scene(s):
    from .site_geometry import build_site
    return build_site(s)


def asset(site_id):
    s = site(site_id)
    folder = RUNTIME / "heritage" / site_id
    uploaded = folder / "upload.json"
    if uploaded.exists():
        return AssetRecord.model_validate(read_json(uploaded)).model_dump()
    scene = procedural_scene(s)
    digest = hashlib.sha256(json.dumps([GENERATOR, s, scene], sort_keys=True).encode()).hexdigest()
    path = folder / f"{digest}.json"
    if not path.exists():
        record = AssetRecord(site_id=site_id, tier=1, kind="procedural", sha256=digest,
            generator_version=GENERATOR, confidence="Reconstructed approximation",
            caveat="Architecturally informed reconstruction, not a surveyed model. Pillars, ornament, materials and layout are illustrative. Cited heights describe the monument approximately; this geometry is unsuitable for measurement.",
            source="Local architectural generator + official historical descriptions and reference photographs", created_at=now(), scene=scene)
        atomic_json(path, record.model_dump())
    return read_json(path)


def validate_glb(data):
    if len(data) < 20 or len(data) > 25*1024*1024:
        raise ValueError("GLB must be between 20 bytes and 25 MiB")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("Expected a complete binary glTF 2.0 (.glb) file")
    chunk_size, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A or chunk_size % 4 or 20+chunk_size > len(data):
        raise ValueError("Invalid GLB JSON chunk")
    try:
        document = json.loads(data[20:20+chunk_size])
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid GLB metadata") from exc
    def check(value):
        if isinstance(value, dict):
            if "uri" in value:
                raise ValueError("Use a self-contained GLB with embedded buffer views, without external or data URIs")
            for v in value.values():
                check(v)
        elif isinstance(value, list):
            for v in value:
                check(v)
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("Invalid glTF asset version")
    check(document)
    if document.get("extensionsRequired"):
        raise ValueError("Export an uncompressed GLB without required extensions")
    if not document.get("meshes"):
        raise ValueError("GLB contains no mesh")
    offset = 20 + chunk_size
    binary_size = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated GLB chunk")
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8 + size
        if size % 4 or offset > len(data):
            raise ValueError("Truncated GLB binary data")
        if kind == 0x004E4942:
            binary_size = size
    if not binary_size or any(b.get("byteLength", 0) > binary_size for b in document.get("buffers", [])):
        raise ValueError("Missing or incomplete mesh buffer")
    return document


def save_glb(site_id, data):
    site(site_id)
    validate_glb(data)
    digest = hashlib.sha256(data).hexdigest()
    folder = RUNTIME / "heritage" / site_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{digest}.glb"
    tmp = folder / f".{uuid.uuid4().hex}.tmp"
    tmp.write_bytes(data)
    tmp.replace(destination)
    record = AssetRecord(site_id=site_id, tier=3, kind="glb", sha256=digest, generator_version="user-upload",
        confidence="User-supplied model · unverified", caveat="Upload does not establish survey accuracy, scale, age or provenance.",
        source="User-supplied GLB", created_at=now(), url=f"/api/heritage/{site_id}/model/{digest}.glb")
    atomic_json(folder / "upload.json", record.model_dump())
    return record.model_dump()


def prewarm():
    for s in profiles():
        asset(s["id"])
