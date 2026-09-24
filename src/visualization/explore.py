"""
src/visualization/explore.py
-----------------------------
Interactive Folium map for quick visual QA of processed layers.
Opens in the default browser.

Run
---
    python -m src.visualization.explore
"""

from __future__ import annotations

import pathlib
import webbrowser

import folium
import geopandas as gpd

from src.utils.config import cfg
from src.utils.logger import get_logger

log = get_logger(__name__)

OUT_MAPS = pathlib.Path(cfg.paths.outputs.maps)
OUT_MAPS.mkdir(parents=True, exist_ok=True)

LAYER_MAP = {
    "Boundary":  (cfg.files.boundary,  "#000000", 2),
    "Waterways": (cfg.files.waterways, "#1e90ff", 1),
    "Roads":     (cfg.files.roads,     "#ff8c00", 1),
    "Buildings": (cfg.files.buildings, "#8b0000", 1),
    "Landuse":   (cfg.files.landuse,   "#228b22", 1),
}


def make_map(out_html: pathlib.Path | None = None) -> folium.Map:
    boundary = gpd.read_file(cfg.files.boundary).to_crs("EPSG:4326")
    centroid  = boundary.geometry.centroid.iloc[0]

    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=10,
                   tiles="CartoDB dark_matter")

    for name, (path, color, weight) in LAYER_MAP.items():
        p = pathlib.Path(path)
        if not p.exists():
            log.warning("Layer '%s' not found at %s — skipping.", name, p)
            continue
        gdf = gpd.read_file(p).to_crs("EPSG:4326")
        fg  = folium.FeatureGroup(name=name, show=(name == "Boundary"))
        folium.GeoJson(
            gdf.__geo_interface__,
            style_function=lambda _f, c=color, w=weight: {
                "color": c, "weight": w, "fillOpacity": 0.15,
            },
            tooltip=folium.GeoJsonTooltip(fields=list(gdf.columns[:3]))
            if len(gdf.columns) >= 1 else None,
        ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl().add_to(m)

    if out_html is None:
        out_html = OUT_MAPS / "thanjavur_explorer.html"
    m.save(str(out_html))
    log.info("Interactive map saved → %s", out_html)
    return m


if __name__ == "__main__":
    html_path = OUT_MAPS / "thanjavur_explorer.html"
    make_map(html_path)
    webbrowser.open(html_path.as_uri())
