# Environmental evidence

Open **Environmental evidence** for current acquired data, or **Research atlas → Run evidence overlay** for a selected run's frozen layers. New analyses retain the data available when they start. No login, account or permission system was added; FastAPI serves the React application and local data APIs.

## Acquired on 4 October 2026

| Evidence | Data available | Interpretation |
| --- | --- | --- |
| Rainfall | NASA POWER PRECTOTCORR, daily UTC 2024–2025; 4 coarse grid points, 2,924 daily values; monthly totals and completeness | Corrected reanalysis, approximately 0.5° × 0.625°; not local rain gauges or a fine-scale rainfall surface |
| Soil | ISRIC SoilGrids surface means, 0–5 cm, sand/silt/clay/bulk density/organic carbon; district clay and texture indicator maps | Predictions at 250 m; sand/(sand+clay) is dimensionless texture screening, not measured permeability, infiltration rate or storage |
| NDVI / NDWI | 16 actual Sentinel-2 Collection 1 L2A scenes across four 2025 quarter windows | Four representative clear-pixel mosaics, not quarterly means or continuous monitoring |
| Historical water | JRC Global Surface Water v1.5 occurrence and transition maps, 1984–2024 | Source: EC JRC/Google. Lost-water classes do not establish an ancient river course |
| Independent comparison | Frozen JRC reference samples and a validated field-outcome import workflow | Surface-water association is reported separately; no independent storage or archaeological field observations have been supplied |

The acquired district soil map covers 96.01% of the district's 250 m grid; the latest satellite mosaic covers 98.94%. Terrain coverage remains 70.49% on that grid. These are different masks, not interchangeable completeness measures. Six-depth heritage soil profiles remain available separately for six of the nine site locations.

## Acquisition and source handling

Use **Acquire / refresh public data** to request the default windows, then create a new analysis. Acquisition has progress and source-specific errors and is mutually exclusive with API analysis jobs. Restarted acquisitions are marked interrupted, preserving successful cached datasets. The app is intended for one local API process; do not run acquisition scripts concurrently with analysis or the UI acquisition worker.

```powershell
.\.venv\Scripts\python.exe -m scripts.acquire_environment --kinds rainfall soil satellite history --start-year 2024 --end-year 2025
```

The year range applies to rainfall; satellite acquisition uses the end year. Soil is model context; JRC is pinned to 1984–2024. Requests and raw files are cached under `runtime/environment/`. Existing raw files are reused; refresh does not force a redownload of a changed upstream version. Source URLs, observation dates, retrieval timestamps, checksums, reflectance scales/offsets and coverage are recorded in manifests. Normal navigation uses the local cache. Derived raster generations are published only after a complete dataset succeeds. Earlier successful rasters and their manifests remain available when a later attempt fails.

Soil WCS files may omit CRS tags. The documented Interrupted Goode Homolosine CRS is assigned explicitly before reprojection. Texture totals must be within 95–105%; unavailable source cells remain gaps. No pedotransfer estimate is presented as a field infiltration measurement.

Sentinel search is bounded to 100 returned candidates per quarter, sorted locally by reported scene cloud cover. At most six overlapping tiles are selected, one scene per tile. It is not an exhaustive least-cloud search. Red, green, NIR and scene-classification COG windows are acquired via overviews and nearest-sampled onto a 250 m UTM 44N grid. Asset-declared scale and offset are applied once. Only SCL classes 4, 5 and 6 are usable; negative reflectance and zero denominators are excluded. NDVI = (NIR−red)/(NIR+red); McFeeters NDWI = (green−NIR)/(green+NIR). Tile acquisition dates and remaining cloud gaps are shown. Coverage differences can affect seasonal means.

## Comparisons and reproducibility

The terrain heuristic and its fixed high-score threshold of 0.65 are unchanged. Reference labels are not used to fit the score or tune its threshold. JRC comparison labels are dry (occurrence 0%) and persistent water (90–100%); intermediate occurrence is excluded. One eligible pixel is chosen per approximately 2 km block, prioritizing persistent water and then proximity to the block centre. Equal wet and dry block samples are selected with a fixed seed (20251004), independently of terrain score values. This avoids a sparse point lattice missing narrow water bodies.

This is a balanced case/control association check. Accuracy and precision are conditional on its artificial class balance and do not estimate district prevalence or operational prediction performance. Adjacent blocks may still be spatially correlated. The historical reference period and terrain source period differ. The verified 250 m run has five eligible persistent-water blocks, producing ten balanced reference sites. Twenty usable samples and both classes are required; otherwise no metrics are asserted. Reported metrics include the confusion matrix, balanced accuracy, precision, recall and rank-based ROC AUC with tie handling.

Each completed new run saves `environment.json`, rainfall series, all eight seasonal NDVI/NDWI GeoTIFFs, six current context GeoTIFF/PNG layers, imported records and `comparisons.json`. Comparisons carry a method version and the sampled locations/scores/labels. The API reads these frozen results, so later code or source changes do not alter past validation. Older runs without saved comparisons invite a new run instead of silently recomputing. Field outcomes require a new run after import; the UI always identifies the selected run.

## Field records and older map evidence

Field import accepts a JSON array of records matching [FieldRecord.json](schemas/FieldRecord.json). Every record needs `id`, WGS84 `longitude`/`latitude`, `observed_on` (not in the future), `target`, `value`, `source`, `method` and `independence_statement`. Coordinates must lie inside the district. Duplicate IDs or coordinate/target pairs in an upload are rejected. An existing ID is explicitly updated; other stored records are preserved. Binary targets are `surface_water_presence`, `water_storage_suitability` and `archaeological_presence` with values 0 or 1. `infiltration_mm_h` records measured rates as context and is not evaluated as a binary outcome. Field comparisons retain one usable record per 2 km block, chosen in ID order. Contributor-declared provenance is not independent certification.

Historical import accepts a WGS84 GeoJSON FeatureCollection, at most 1,000 features per upload and 5 MiB. Each valid geometry must lie in the district and have string properties `title`, `source`, `period`, `interpretation`, plus `confidence`: `documented`, `candidate` or `field verified`. Accepted features append to the local collection, display with source/period information, and are copied into future runs. Imports are interpretations of already georeferenced evidence; the app does not georeference a scanned map automatically. No dated palaeochannel geometries or older historical-map features were fabricated to fill the remaining evidence gap.

## API

| Endpoint | Purpose |
| --- | --- |
| GET `/api/environment` | Current source manifests, rainfall, acquisition status and import counts |
| POST `/api/environment/acquire` | Explicit acquisition; optional kinds and start/end years |
| GET `/api/environment/layer/{id}` | Current raster metadata and display bounds |
| GET `/api/environment/image/{id}` | Current local display PNG |
| GET `/api/environment/season/{year}/{quarter}/{ndvi_or_ndwi}` | Seasonal display PNG |
| PUT `/api/environment/field-records` | Validated field-record upsert |
| GET/PUT `/api/environment/historical-features` | Read/import sourced GeoJSON |
| GET `/api/environment/validation/{run_id}?source=satellite&target=surface_water_presence` | Saved comparison for a completed run; use source=field for field outcomes |
| GET `/api/runs/{id}/artifacts/{name}` | Frozen exports; allowlisted file names only |

The cell endpoint also returns frozen environmental raster samples at the inspected heritage/site coordinates. The environmental rasters supply context and do not enter the terrain score or imply integrated water-storage capacity.

## Primary sources

- [NASA POWER daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [ISRIC SoilGrids documentation](https://docs.isric.org/globaldata/soilgrids/index.html)
- [Element 84 Earth Search](https://github.com/Element84/earth-search/blob/main/README.md) and [Sentinel-2 C1 L2A collection](https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a)
- [JRC corrected v1.5 downloads](https://global-surface-water.appspot.com/download) and [2024 data guide](https://storage.googleapis.com/water-world/downloads_ancillary/DataUsersGuidev2024_v.5.pdf)

Verify with `python -m pytest tests -q`, frontend lint/build, and `npm run test:environment` with the server running and a new completed run. Browser checks include actual loaded images, seasonal exports, source counts, reference modes, rejected incomplete records, heritage context and mobile overflow. The existing analysis and heritage browser suites cover run creation, GLB handling and WebGL rendering.
