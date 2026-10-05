"""Integration against the supplied district inputs; no external data requests."""
import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from shapely.geometry import shape
from backend.analysis import execute, NODATA
from backend.catalog import boundary, project, read_json
from backend.settings import DEM


@pytest.fixture(scope='module')
def result(tmp_path_factory):
    output = tmp_path_factory.mktemp('analysis')
    report = execute(output, {'resolution_m': 250, 'slope_weight': 0.55})
    return output, report


def test_zone_totals_mask_and_orientation(result):
    output, report = result
    assert sum(zone['cells'] for zone in report['zones']) == report['grid_cells']
    assert sum(zone['cells'] for zone in report['zones'] if zone['code'] != 4) == report['valid_cells']
    with rasterio.open(output / 'terrain.tif') as raster:
        assert raster.crs.to_epsg() == 32644
        assert raster.transform.a == 250
        assert raster.transform.e == -250
        assert raster.count == 7
        zones = raster.read(6)
        scores = raster.read(4)
        assert np.all(scores[zones == 4] == NODATA)
        assert set(np.unique(zones)) <= {NODATA, 1, 2, 3, 4}
        assert np.all(raster.read(7)[zones != NODATA] == 4)
        assert np.all(raster.read()[:, zones == NODATA] == NODATA)


def test_exported_elevation_matches_source_coordinates(result):
    output, _ = result
    with rasterio.open(output / 'terrain.tif') as raster, rasterio.open(DEM) as original:
        inverse = Transformer.from_crs(raster.crs, original.crs, always_xy=True)
        # Spatial control points would fail if rows/columns were transposed or flipped.
        forward = Transformer.from_crs('EPSG:4326', raster.crs, always_xy=True)
        for lng, lat in [(79.13, 10.78), (79.1, 10.9), (79.25, 10.43)]:
            x, y = forward.transform(lng, lat)
            row, col = raster.index(x, y)
            cx, cy = raster.xy(row, col)
            source_coord = inverse.transform(cx, cy)
            source_height = next(original.sample([source_coord]))[0]
            output_height = raster.read(1, window=((row, row+1), (col, col+1)))[0, 0]
            assert output_height != NODATA
            assert abs(float(source_height) - float(output_height)) < 8


def test_vector_outputs_clipped_and_report_honest(result):
    output, report = result
    district = project(boundary())
    for feature in read_json(output / 'zones.geojson')['features']:
        # Ignore sub-metre reprojection precision along the boundary.
        assert project(shape(feature['geometry'])).difference(district.buffer(0.1)).area < 1
    assert report['validation']['accuracy'] is None
    assert report['evidence_assessment'] == 'Insufficient data'
    assert len(report['provenance']) >= 6
