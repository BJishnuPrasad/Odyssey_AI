# GeoDyssey — Thanjavur Research Atlas

A local React + FastAPI workspace for exploring terrain, mapped water and heritage context. Adapted from `BJishnuPrasad/Odyssey_AI` at `6946a64`. This implementation replaces the disconnected demonstration dashboard with real, versioned analysis results.

## Free Render deployment

[Deploy the free demonstration](https://render.com/deploy?repo=https://github.com/BJishnuPrasad/Odyssey_AI). Read the [setup and free-tier limitations](docs/RENDER.md): the service sleeps and new uploads/results are temporary. No paid disk or database is configured.

## Start on this computer

The environment, dependencies, OSM extracts and production frontend have already been installed. Open **Start-GeoDyssey.cmd** in this folder and visit **http://127.0.0.1:8000**. If a server is already running there, use it rather than starting another. API documentation is at `/docs`.

Keep the launcher terminal open; Ctrl+C stops a server started by the launcher. The server used during development may be running in the background; its PID is recorded in `runtime/server.pid` and logs are in `runtime/server.*.log`.

To stop that background instance before using the launcher, run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-GeoDyssey.ps1`. The script verifies the recorded process belongs to this project before stopping it.

## What works

See the [5 October MVP review](docs/MVP_REVIEW.md) for verified workflows, corrected errors and outstanding research/deployment requirements.

- Environmental evidence workspace with acquired 2024–2025 rainfall, four 2025 Sentinel-2 NDVI/NDWI mosaics, district SoilGrids texture screening, 1984–2024 JRC water history, sourced historical-feature imports and independent reference/field comparison workflows. Each new run freezes source manifests, seasonal rasters and comparison results. See [methods, sources and imports](docs/ENVIRONMENTAL_EVIDENCE.md).

- Integrated heritage 3D/soil detail views and a learning library: map or name lookup, locally cached approximate models, GLB upload, six acquired SoilGrids profiles, glossary, searchable site encyclopedia, live-data lessons and Student/Practitioner views without logins. See [setup, sources, schemas and limitations](docs/HERITAGE_LIBRARY.md).

### Heritage and education readiness

The local viewer, library, caching, search, GLB upload and soil-profile import are implemented. Site geometry is labelled **reconstructed approximation** unless a user uploads a model (still labelled unverified). Official historical/photo references are linked; no surveyed 3D scans were acquired. SoilGrids properties are regional predictions at 250 m, not excavated strata. Three locations have no usable soil values. Photogrammetry, measured field logs, bedrock and cultural-layer depths await suitable evidence. These additions do not activate a calibrated ML model or dual-timescale fusion.

### Existing analysis features

- React research atlas with district boundaries, heritage locations, optional mapped-water and online basemap layers, cell inspection, responsive layouts and explicit error states.
- Source catalogue with available/missing evidence, settlement context with deduplicated records, and transparent methodology.
- Background analysis with durable SQLite status, progress, failure details and run history. Results belong to one run; failed runs cannot expose an older report as their own.
- 100, 250 or 500 m UTM 44N analysis grids; configurable slope contribution; sensitivity comparisons.
- Geographically aligned seven-band GeoTIFF, clipped zone GeoJSON, result JSON with SHA-256 source fingerprints, heritage GeoJSON and lightweight PNG display overlays.
- Recent mapped-water proximity and descriptive terrain association at known heritage records.

## Scientific scope — read before interpreting the map

**This is a working exploratory research application, not a validated water-storage or archaeological discovery model.**

The *Terrain potential* view uses a declared heuristic: `slope_weight × exp(-slope_degrees / 5) + (1-slope_weight) × clip(0.5 + (local_mean_elevation - elevation) / 10, 0, 1)`. The local square neighbourhood extends approximately 1 km in each direction. Analyst-selected thresholds are low `<0.40`, moderate `0.40–<0.65`, high `≥0.65`. These are relative terrain patterns, not probabilities or physical capacity. Missing DEM data, invalid neighbours and less than 80% neighbourhood support produce **insufficient data**.

The separate *Evidence assessment* view conservatively remains **insufficient data throughout the district**. Public reanalysis rainfall, predicted soil properties, dated Sentinel-2 observations and JRC historical water maps are acquired as context. Measured infiltration, dated palaeochannel/archaeological evidence and independent storage outcomes remain missing. A separately reported surface-water reference comparison does not establish storage accuracy. This release does not implement historical/current fusion, TWI, catchment flow routing, calibrated ML, groundwater storage or cubic-metre capacity estimates. Existing land-use geometry is catalogued but does not change the score. Water proximity is descriptive and does not change the terrain score.

At 250 m with the supplied inputs, the first verified run has **54,845 district cells and 70.49% usable terrain coverage**. The supplied boundary measures approximately **3,428.53 km²** in UTM 44N; this is calculated, not the old hard-coded area. The PBF yields **1,425 water features and 832 land-use polygons**. The 11 heritage records reduce to 9 contextual locations after exclusions. Only 6 overlap usable terrain in that run. Counts and coverage change with input data and grid settings.

The SRTM-labelled input is not a contemporary observation, and the original raster's vertical datum/source provenance is not independently verified. Coastal flats and managed drainage can receive high terrain scores without being suitable storage locations. OSM inventory proximity is not independent validation. Raster water distances are approximate to one analysis cell. Cells are counted by centre inclusion; vector exports clip boundary edges, so their total areas can differ slightly.

## Database and files

SQLite is included in Python: **no database server, account or paid service is required**. `runtime/geodyssey.sqlite3` holds run state, parameters, summaries and dataset metadata. Large artifacts live in `runtime/runs/<run-id>/`, with a separate folder per run. Original source data stays in `Data/`; district OSM extracts are in `Data/derived/`.

SQLite WAL mode and one worker suit this local application. Use exactly **one API process**. For shared/public deployment, add authentication, a process-safe job queue and access controls; PostgreSQL/PostGIS is an optional next step for concurrent spatial queries. The current server binds only to `127.0.0.1`.

## Project structure

```text
backend/                   FastAPI, SQLite, data catalogue, terrain analysis
frontend/src/GeoDyssey.jsx  Active React application
frontend/src/components/Atlas.jsx  Leaflet spatial explorer
frontend/src/api.js         Same-origin API client
frontend/src/geodyssey.css  Responsive visual design
scripts/extract_osm.py      Water and land-use extraction from supplied PBF
scripts/run_analysis.py     Command-line analysis using the same engine
scripts/browser_smoke.cjs   Browser workflow and responsive checks
tests/                     Numerical, API and geospatial integration tests
Data/raw/                  Original supplied district data
Data/derived/              Regenerable OSM extracts and extraction manifest
runtime/                   Local database, run outputs and logs (ignored by Git)
docs/                      Architecture and research roadmap
```

`src/`, the old frontend `App.jsx`/tab components, and `outputs/reports/` are retained legacy material for reference. The active application does **not** import the old hard-coded charts, old model scores or old feature pipeline. `app.py` now launches the new API, and `pipeline.py` routes to the new CLI. The original orchestration is retained in `legacy/pipeline.py`.

## Fresh installation

Requires Python 3.12 (tested), Node.js 24 (tested), Git and Git LFS. Fetch the PBF with `git lfs pull` if it is still a text pointer. The regional PBF is about 556 MB; extraction also needs memory for OSM node locations and multipolygon assembly.

```powershell
.\Setup-GeoDyssey.ps1 -Python 'C:\path\to\python.exe'
.\Start-GeoDyssey.ps1
```

If PowerShell blocks the script, the `.cmd` launcher uses a process-local execution-policy option. No global setting is changed. Dependencies are pinned in `requirements-lock.txt` and `frontend/package-lock.json`.

Manual or non-Windows equivalent:

```text
python -m venv .venv
# Activate the environment with your platform's activation command.
python -m pip install -r requirements-lock.txt
cd frontend
npm ci
npm run build
cd ..
python -m scripts.extract_osm
python app.py
```

For development, start the API as above and run `npm run dev` from `frontend/` in a second terminal. Vite proxies `/api` to the local backend; production serves both from one origin. Browser requests do not assume the visitor has a separately hosted backend at localhost. A `VITE_API_BASE_URL` override is available for a separately configured backend; configure CORS at that deployment if using a different origin.

## Recreating the acquired evidence after cloning

Git includes the application, dependency lockfiles, structured content, acquisition scripts, schemas and tests. Generated data under `runtime/` and `Data/derived/`, local Python/Node environments, frontend build files, logs and screenshots remain on the original computer and are excluded from Git. Existing source datasets tracked by Git LFS remain in LFS; run `git lfs pull` after cloning.

After setup, recreate the public environmental evidence and heritage profiles with:

```powershell
.\.venv\Scripts\python.exe -m scripts.extract_heritage
.\.venv\Scripts\python.exe -m scripts.fetch_heritage_soil
.\.venv\Scripts\python.exe -m scripts.acquire_environment --kinds rainfall soil satellite history --start-year 2024 --end-year 2025
.\.venv\Scripts\python.exe -m scripts.run_analysis --resolution 250
```

Run acquisition with network access and no concurrent analysis. The environmental acquisition is also available through the application's **Acquire / refresh public data** button. Results depend on source availability and retain their own dates and provenance. Local uploaded models, field records and SQLite run history are not published; preserve `runtime/` separately if moving those personal project records between computers.

## Run and verify

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
cd frontend
npm run lint
npm run build
npm run test:browser
npm run test:heritage
npm run test:environment
```

The browser test requires the app to be running with at least one completed run and Microsoft Edge installed. It creates a 500 m test run, downloads a TIFF and saves screenshots under `artifacts/`. To use another installed Playwright browser channel, set `PLAYWRIGHT_CHANNEL`. External basemap requests are disabled during automation. For a first result without the UI, use `python -m scripts.run_analysis --resolution 250` while no other analysis is active.

## Sources and internet use

Analysis uses supplied files and cached public datasets and needs no online account. The explicit environmental acquisition action contacts NASA POWER, ISRIC, Earth Search/Sentinel COG hosting and JRC. It downloads bounded data once and reuses cached source files; local navigation does not reacquire them. Basemaps are optional and off by default. Enabling the standard OSM basemap sends viewport tile requests to OpenStreetMap; font styling can request Google Fonts, with local fallbacks when offline. No bulk tile download or offline tile cache is provided.

- [OpenStreetMap attribution and ODbL](https://www.openstreetmap.org/copyright)
- [Standard basemap usage policy](https://operations.osmfoundation.org/policies/tiles/)
- [GDAL slope and coordinate-unit guidance](https://gdal.org/en/stable/programs/gdaldem.html)
- [USGS SRTM source context](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm)

Further research milestones are documented in `docs/RESEARCH_ROADMAP.md`.
