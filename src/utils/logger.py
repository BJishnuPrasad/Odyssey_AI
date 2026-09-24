"""
src/utils/logger.py
-------------------
Centralised logging setup.  All pipeline modules call `get_logger(__name__)`
instead of configuring logging individually.

Usage
-----
    from src.utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Processing DEM …")
"""

from __future__ import annotations

import logging
import pathlib
import sys
from datetime import datetime

_LOG_DIR = pathlib.Path(__file__).resolve().parents[2] / "outputs" / "reports"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_FILE = _LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
    ],
)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.  Call once per module at the top level."""
    return logging.getLogger(name)
