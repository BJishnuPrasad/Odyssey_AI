"""
pipeline.py
-----------
Master orchestrator.  Runs all stages in order.

Usage
-----
    python pipeline.py                     # full run
    python pipeline.py --stage osm        # single stage
    python pipeline.py --stage dem osm    # multiple stages
"""

from __future__ import annotations

import argparse
import sys

from src.utils.logger import get_logger

log = get_logger("pipeline")


def _stage_ingest_osm() -> None:
    log.info("═══ Stage 1 — OSM Ingestion ═══")
    from src.ingestion.extract_osm import extract_all
    extract_all()


def _stage_process_dem() -> None:
    log.info("═══ Stage 2 — DEM Processing ═══")
    from src.processing.process_dem import run
    run()


def _stage_process_osm() -> None:
    log.info("═══ Stage 3 — OSM Processing ═══")
    from src.processing.process_osm import run
    run()


def _stage_features() -> None:
    log.info("═══ Stage 4 — Feature Engineering ═══")
    from src.features.build_features import build
    build()


def _stage_train() -> None:
    log.info("═══ Stage 5 — Model Training ═══")
    from src.models.train import train
    train()


def _stage_predict() -> None:
    log.info("═══ Stage 6 — Suitability Prediction ═══")
    from src.models.predict import predict
    predict()


STAGES = {
    "osm":     _stage_ingest_osm,
    "dem":     _stage_process_dem,
    "proc_osm":_stage_process_osm,
    "features":_stage_features,
    "train":   _stage_train,
    "predict": _stage_predict,
}

ALL_STAGES = list(STAGES.keys())


def main(stages: list[str]) -> None:
    for name in stages:
        if name not in STAGES:
            log.error("Unknown stage '%s'. Available: %s", name, ALL_STAGES)
            sys.exit(1)
        STAGES[name]()
    log.info("Pipeline finished ✓")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Odyssey AI Pipeline")
    parser.add_argument(
        "--stage", nargs="*", choices=ALL_STAGES,
        help="Stage(s) to run. Omit to run all stages in sequence.",
    )
    args = parser.parse_args()
    chosen = args.stage if args.stage else ALL_STAGES
    main(chosen)
