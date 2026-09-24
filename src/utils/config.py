"""
src/utils/config.py
-------------------
Central config loader.  All modules should import `cfg` from here
rather than hard-coding paths or parameters.

Usage
-----
    from src.utils.config import cfg

    raw_dem  = cfg.files.raw_dem          # → "data/raw/dem/output_SRTMGL1.tif"
    out_crs  = cfg.project.crs            # → "EPSG:32644"
"""

from __future__ import annotations

import pathlib
import yaml
from types import SimpleNamespace


def _dict_to_ns(d: dict) -> SimpleNamespace:
    """Recursively convert a nested dict into a SimpleNamespace for dot-access."""
    ns = SimpleNamespace()
    for k, v in d.items():
        setattr(ns, k, _dict_to_ns(v) if isinstance(v, dict) else v)
    return ns


def load_config(path: str | pathlib.Path | None = None) -> SimpleNamespace:
    """Load *configs/config.yaml* (or a custom path) and return a SimpleNamespace tree."""
    if path is None:
        # resolve relative to project root (two levels up from this file)
        path = pathlib.Path(__file__).resolve().parents[2] / "configs" / "config.yaml"
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return _dict_to_ns(raw)


# Module-level singleton – import this everywhere
cfg: SimpleNamespace = load_config()
