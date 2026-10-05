# MVP review — 5 October 2026

The application is a working local research and teaching MVP. Its terrain screening, environmental context, heritage viewer and library are usable. It is **not a validated machine-learning model for storage capacity or archaeological discovery**. The original project brief described a broader dual-timescale model; that model is not implemented by the active application.

## Errors corrected in this review

| Finding | Correction |
| --- | --- |
| Connection label stayed green after a loaded API stopped | A separate health check runs every five seconds, with a four-second timeout. It displays offline status and reloads workspace data when the API returns. |
| Requests could wait indefinitely; structured validation errors were reduced to generic messages | Requests have a 30-second default timeout and readable field validation messages. Writes are never automatically retried. |
| Retry did not necessarily reload the same selected completed run; recovered run errors could remain visible | Workspace refresh explicitly reloads the selected run. Run errors are cleared when that run loads successfully without dismissing unrelated operation errors. |
| Some malformed GeoJSON geometries raised uncaught geometry-library errors | These now return HTTP 422; invalid imports do not overwrite existing historical evidence. |
| Failure while creating an acquisition job could leave its lock held | Startup exceptions release the acquisition lock, allowing another attempt. |
| A deleted published context raster could silently disappear from a new run | Missing rasters and checksum mismatches now fail the run explicitly with a refresh instruction; previous completed runs remain untouched. |
| The reference library did not list all acquired public sources | Added NASA POWER, Earth Search and JRC and clarified acquired versus discovery-only sources. |

## Verified MVP scope

- FastAPI + React application on localhost; SQLite run history and per-run artifacts; no login or permission system, as requested.
- DEM reprojection and NoData handling, configurable terrain heuristic, sensitivity analysis, map inspection and geographic exports.
- Four rainfall grid series for 2024–2025 (2,924 daily values), soil texture context, sixteen actual Sentinel-2 scenes represented by four 2025 seasonal mosaics, and JRC v1.5 water history for 1984–2024.
- Frozen source manifests, six context layers, eight seasonal rasters and saved reference comparisons for new runs. Acquired context does not silently change old scores or reports.
- Nine heritage profiles; shared map/name lookup; cached detailed procedural 3D scenes; orbit/zoom/pan; validated self-contained GLB uploads and restoration of the approximation.
- Six acquired heritage soil profiles; explicit missing values for the other three. Validated field-profile imports can replace estimates.
- Searchable site encyclopedia, six glossary entries, three lessons with live project examples and a reference collection. Student/practitioner modes are local display preferences.
- Field-outcome and sourced historical-feature imports, export workflows and responsive desktop/mobile views.

## Missing parts and practical limits

| Area | Remaining work or evidence |
| --- | --- |
| Predictive model | No trained archaeological/storage model, calibrated probability, uncertainty model or validated fast/slow fusion. Existing outputs are a declared terrain heuristic. |
| Hydrology | No flow routing, catchment connectivity, drainage-density model or TWI calculation. Rainfall/soil/NDVI are context layers, not active score predictors. |
| DEM completeness | At 250 m, usable terrain coverage is 70.49%. Better source coverage and verified vertical provenance are needed before assessing remaining cells. |
| Infiltration/storage | SoilGrids is a prediction. Sand/(sand+clay) is only a texture indicator. Measured infiltration, soil storage parameters and independent storage outcomes are absent. |
| Validation | The 250 m dataset provides only five eligible persistent-water blocks, paired with five dry blocks. Ten samples are below the required twenty, so accuracy metrics remain withheld. No field outcomes have been supplied. |
| Historical landscape | JRC gives satellite-era water history. Georeferenced older map features and dated palaeochannel/sediment evidence have not been supplied. The import workflow exists; ancient-channel confirmation does not. |
| 3D geometry | Detailed architectural illustrations remain approximate. Extracted OSM outlines are retained separately, not used as surveyed building plans. No photogrammetry reconstruction, shadow-derived height workflow or surveyed mesh was acquired. GLB is supported; CAD/BIM must first be exported to GLB. |
| Subsurface | Bedrock and cultural-layer depths remain unknown without supporting evidence. Regional soil depth intervals are not excavated stratigraphy. Soil uncertainty quantiles are not acquired. |
| Operational uptime | The preview depends on the local server process and an awake computer. Browser recovery detects and reconnects; it does not restart a stopped server. An always-on Windows service or hosted deployment with recovery remains a separate operational step. |
| Deployment scale | One local API process is supported. Do not run CLI acquisition and API acquisition/analysis concurrently. No multi-user queue, cancellation, scheduled backups or load-test certification is provided. |

These gaps are not filled with fabricated observations or accuracy claims. Authentication is deliberately excluded, not treated as an unfinished requested feature.

## Verification

Final result: **34 Python tests passed; frontend lint and production build passed; all four browser suites passed.** The final preview run is `3916930b49b349f58df7acf7af3acd64`: 250 m, 70.49% usable terrain, six context layers, eight seasonal exports and ten eligible reference samples. No predictive accuracy is asserted.

Run the Python suite with `python -m pytest tests -q`; frontend checks with `npm run lint` and `npm run build`. Browser suites are `test:browser`, `test:environment`, `test:heritage` and `test:recovery` from the frontend directory. Recovery tests intercept requests in their own browser context; they do not stop the user's API or mutate source records. Existing browser suites also exercise invalid imports, completed-run exports, actual raster image loading, WebGL rendering, upload/reset and mobile overflow.

Review scope covers local workflows and saved datasets. It does not establish scientific predictive validity, continuous uptime, production load capacity or freshness beyond each source's recorded dates. Non-blocking tool warnings remain: the lazy Three.js viewer bundle is larger than Vite's default warning threshold, and the installed Starlette/httpx test integration emits a deprecation warning.

Preview: http://127.0.0.1:8000. Start manually with `Start-GeoDyssey.cmd` and keep its terminal open. Do not launch a duplicate server if the preview is already healthy.
