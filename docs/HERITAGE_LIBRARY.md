# Heritage viewer and learning library

The active React/FastAPI application implements both features. There is no parallel Streamlit application and no authentication. Practitioner and Researcher/Student are remembered local view preferences, with the same underlying data and permissions.

## How to use

In the research atlas, enter a site name or a phrase such as “show me Brihadeeswarar Temple in 3D”. Multiple matches require selecting a location. A heritage marker's **Open 3D & soil profile** button opens the same site detail route. The Library searches site profiles, glossary definitions, lessons and references, with site-specific region, period, type and documentation filters. Learning modules use the selected run and actual retained site coordinates.

The side-by-side site detail includes an orbit/zoom/pan Three.js model, soil cross-section, property table, supporting sources and a live terrain experiment. On smaller screens these stack vertically. Model and soil confidence are separate from historical documentation quality.

## Acquired sources, 4 October 2026

- Nine retained OSM locations have profiles. Five principal monuments have independently matched official historical sources. The gateway has contextual temple documentation, and the three smaller shrine/memorial records retain explicit identification/date gaps.
- History and reference-image links: [UNESCO](https://whc.unesco.org/en/list/250/), [Thanjavur Palace](https://thanjavur.nic.in/tourist-place/thanjavur-palace/), [Manora Fort](https://thanjavur.nic.in/tourist-place/manora-fort/), [Grand Anicut](https://thanjavur.nic.in/tourist-place/grand-anicut-canal/), and [district galleries](https://thanjavur.nic.in/photo-gallery/). These links are not a licensed, overlapping photogrammetry capture set. No image-based survey model was acquired.
- Six exact OSM outlines were extracted from the supplied PBF: Brihadishwara, Palace, Airavateswarar, Kallanai, Manora and Gopuram. These source outlines are retained separately; the detailed architectural illustration does not treat a complex perimeter as a surveyed building plan. Source IDs and PBF SHA-256 are retained in `Data/derived/heritage_footprints.json`. OSM is attributed under ODbL.
- ISRIC's documented REST outage is bypassed using its public WCS. Thirty bounded rasters cover five soil properties at six depths. Actual site-point samples are cached for six locations. Palace, Kallanai and Manora have no usable values at their point locations. No neighbour's values are substituted.
- SoilGrids supplies model means, not survey measurements. The native grid is 250 m in Interrupted Goode Homolosine (ISRIC 152160). The returned WCS TIFFs can omit CRS tags; the acquisition script uses ISRIC's documented native CRS and grid-aligned requests. Raster hashes, request URLs, conversions and sampling method are retained in `runtime/heritage/soilgrids-wcs/manifest.json`. Zero/no-coverage responses are left unavailable; this conservative acquisition does not infer zero-valued soil properties.

## Working functionality and limits

Working locally: cached procedural assets; shared map/text site resolution; GLB upload, persistence and rendering; soil model sampling and cached profiles; field-profile JSON import; full-text library search and filters; three live-data lessons; source links; role view preferences; offline use after data acquisition/build.

Tier 1 uses detailed procedural architectural illustrations (generator architecture-3): stepped temple vimanas, halls and columns, gateways, compound walls, palace courtyards, the multi-storey Manora tower and Kallanai structures. Stone/paving textures, warm lighting, soft shadows and camera fitting improve legibility. Cited heights inform Brihadishwara (about 64.8 m) and Manora (about 23 m). Other dimensions, ornament and layouts are illustrative; no surveyed or shadow-derived geometry is claimed. Asset keys incorporate the generator version, site record and generated geometry. Known assets are warmed at API startup.

Tier 3 supports self-contained, uncompressed binary glTF 2.0 (`.glb`, 25 MiB maximum). Export BIM/CAD/scans to GLB first. External/data URIs and required decoder extensions are rejected. Uploaded models are labelled unverified; an upload is not survey certification. Returning to the procedural view retains uploaded binaries locally.

Pending real evidence: photogrammetry processing (Tier 2, optional external COLMAP workflow), measured borehole/GPR/trench/resistivity datasets, supported bedrock depths and cultural-layer interpretations. No likely burial depth is fabricated from a monument date. SoilGrids uncertainty quantiles have not been acquired; no numerical confidence interval is displayed.

The teaching experiment toggles the actual slope/flatness and relative-position terms, holding the selected run's weights fixed. Both off means **Unassessed**. Rainfall, NDVI and TWI score controls are disabled because these are not active score inputs. Available environmental raster values can be inspected separately at the site; rainfall and seasonal index views are on the Environmental evidence page. This is not causal feature attribution for a trained model. SoilGrids is site context only: adding these profiles does not recalibrate the existing terrain engine or enable historical/current fusion.

## Refresh and authoring

```powershell
.\.venv\Scripts\python.exe -m scripts.extract_heritage
.\.venv\Scripts\python.exe -m scripts.fetch_heritage_soil
```

Run acquisition explicitly with network access. Requests are bounded and cached; successful rasters are reused. A fresh cache directory is needed to acquire a different source version. Field-data imports are never overwritten by this script. Normal site navigation does not call remote soil services. The frontend bundles Three.js locally.

Edit `content/sites.json` to enrich the retained OSM IDs. Add one JSON file per term, lesson or reference under `content/library/`; no code change is needed. Entries are validated on read and plain text is rendered without raw HTML. Search indexes current JSON content on each request (appropriate for this local collection). Filters on historical documentation do not claim geometry confidence. Future predictions must first be added as explicitly sourced site records; this application currently has no archaeological prediction inventory.

## Contracts

Machine-readable JSON schemas are in `docs/schemas/`: `AssetRecord.json`, `SoilProfile.json`, `SiteProfile.json`, `LibraryEntry.json` (generated from `backend/heritage_schema.py`).

| Contract | Key fields |
| --- | --- |
| Cached asset | schema_version, site_id, tier, kind, sha256, generator_version, confidence, caveat, source, created_at, URL or scene |
| Soil profile | site_id, source_kind, source/source_url, retrieved_at, resolution_m, confidence, caveat, ordered layers, optional evidenced bedrock/cultural depths |
| Soil layer | top_cm, bottom_cm, label, nullable sand/silt/clay %, bulk density g/cm³, organic carbon g/kg |
| Library entry | id, kind, title, summary, plain-text body, tags, references, steps, exercise |

Soil intervals cannot overlap, contain impossible percentages, or place the cultural band outside the represented depths. Supporting evidence is mandatory for bedrock and cultural-depth claims. `soilgrids`, `borehole`, `trench`, `gpr`, and `resistivity` sources share the same schema/UI; geophysical profiles should contain interpreted intervals, not raw instrument files. The source kind determines the confidence label on import.

### Verification

Run `python -m pytest tests -q`, `npm run lint` and `npm run build` in their existing locations. With the local server running and a completed terrain run, run `node scripts/heritage_browser.cjs` for the viewer/library flow and `node scripts/browser_smoke.cjs` for existing analysis workflows. The browser checks render WebGL, compare toggled live contributions, verify missing soil states, search, lessons, view-mode persistence and mobile overflow. Screenshots are saved under `artifacts/`.

| API | Purpose |
| --- | --- |
| GET `/api/library?q=&kind=&region=&period=&typology=&confidence=` | Search and filter; returns facets |
| GET `/api/heritage/resolve?q=` | Name/alias/short-phrase lookup; returns candidates |
| GET `/api/heritage/{id}` | Site, active model, soil profile, summary |
| PUT `/api/heritage/{id}/model` | Raw GLB body; validated and content-addressed |
| GET `/api/heritage/{id}/model/{sha256}.glb` | Serve allowlisted local model |
| DELETE `/api/heritage/{id}/model` | Return to procedural view, retain uploaded file |
| PUT `/api/heritage/{id}/soil` | Validated profile JSON |

Keep the existing loopback-only, single-process deployment. No login or role-based access was added.
