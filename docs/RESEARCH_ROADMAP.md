# Research milestones

The poster describes the intended research programme, not established findings. Its accuracy claims, correlations and historical conclusions are hypotheses until evaluated.

## Delivered local foundation

React/FastAPI integration; source inventory; real OSM extraction; raster reprojection, NoData and orientation handling; terrain screening; contextual heritage/water association; run provenance; independent evidence status; SQLite; downloadable outputs; numerical/API/browser tests. Public rainfall (2024–2025), district SoilGrids context, four actual Sentinel-2 seasonal mosaics (2025), JRC historical water (1984–2024), field/historical imports and frozen reference comparisons are also delivered. See ENVIRONMENTAL_EVIDENCE.md.

## Next: complete and date the evidence

1. Obtain a DEM covering the eastern and northern boundary gaps; verify units, vertical datum and source metadata.
2. Supplement acquired reanalysis rainfall and soil predictions with local gauges, measured infiltration and storage observations. Define the study season and aggregation periods.
3. Extend the acquired four quarterly NDVI/NDWI mosaics to denser, consistently sampled time series; preserve cloud masks, observation dates and coverage differences.
4. Obtain georeferenced historical maps/palaeochannels and a dated, curated archaeological inventory with location uncertainty.
5. Assemble independent surveyed storage outcomes and an inventory of observed tanks/ponds. Do not use the same water layer as both predictor and independent validation.

## Then: defensible models

- Define surface accumulation, retention and groundwater recharge as distinct targets; identify what each dataset can support.
- Add hydrologically conditioned flow routing, accumulation, drainage connectivity and TWI with flat/pit/boundary checks. Compare these against real drainage and known hydrological behaviour.
- Separate short-term observations from long-term historical evidence. Fuse only where dates, coverage and spatial support are adequate. Preserve insufficient-data cells.
- Fit interpretable statistical/ML baselines only when labels support them. Hold out entire sites or separated spatial blocks, report uncertainty and compare with simple baselines.
- Validate on independent sites, assess sensitivity across parameters and resolutions, and quantify temporal consistency. Publish source IDs, split definitions and run fingerprints with metrics.

## Later: shared deployment

Authentication, role-based dataset administration, bounded job queue, cancellation/retry, backups, migration management, object storage and optional PostgreSQL/PostGIS. Add public data import workflows only with dataset-specific validation and provenance, not arbitrary unvalidated uploads.
