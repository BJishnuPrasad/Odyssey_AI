# Local verification — 1 October 2026

- Python: 13 tests passed. Checks cover metric slope, NoData/neighbourhood handling, classification thresholds, API validation and run gating, failed-run isolation, restart recovery, raster masks, raster/source coordinate checks, vector clipping and truthful missing validation metrics.
- One upstream Starlette/httpx deprecation warning was emitted; tests passed. No test failure remains.
- Active React source: lint clean. Production Vite build succeeds.
- Browser: Microsoft Edge via Playwright passed navigation, evidence view, heritage location focus, water-layer loading, map cell inspection, background run creation, GeoTIFF download and mobile overflow checks. Browser runtime errors: none.
- Final default run: `628b4599c8c54748bbc5c85d87866f76`, 250 m grid, slope weight 0.55; completed with 54,845 district cells, 38,658 valid cells, 70.49% terrain coverage and 11 source/code/dependency fingerprints.
- Visual checks: desktop and mobile screenshots reviewed; removed the API-key-placeholder basemap and made online tiles optional/off by default. Categorical map pixels are rendered without interpolating colours. Tiny nonzero zone percentages retain two decimal places.

Outputs: `runtime/runs/628b4599c8c54748bbc5c85d87866f76/`. Screenshots: `artifacts/final-desktop.png` and `artifacts/final-mobile.png` (captured immediately before the tiny-percentage display refinement). These runtime artifacts are local and ignored by Git; regenerate them from the supplied inputs.

These checks verify implementation and geographical consistency. They do not validate the terrain heuristic against real storage outcomes or establish archaeological discovery performance.
