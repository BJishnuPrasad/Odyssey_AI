import ee
import geemap

# Authenticate / initialize Earth Engine
ee.Authenticate()
ee.Initialize()

# Load Thanjavur boundary (same file used by download_dem.py)
aoi = geemap.geojson_to_ee(
    "data/raw/boundary_geojson/thanjavur_boundary.geojson"
)


def mask_s2_clouds(image):
    """Masks clouds in a Sentinel-2 image using the QA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('QA60')

    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    # Both flags should be set to zero, indicating clear conditions.
    mask = (
        qa.bitwiseAnd(cloud_bit_mask)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )

    return image.updateMask(mask).divide(10000)


dataset = (
    ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(aoi)
    .filterDate('2020-01-01', '2020-01-30')
    # Pre-filter to get less cloudy granules.
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .map(mask_s2_clouds)
)

# Clip the composite to the Thanjavur boundary
sentinel_thanjavur = dataset.mean().clip(aoi)

visualization = {
    'min': 0.0,
    'max': 0.3,
    'bands': ['B4', 'B3', 'B2'],
}

Map = geemap.Map()
Map.centerObject(aoi, 10)
Map.addLayer(sentinel_thanjavur, visualization, 'Thanjavur Sentinel-2 RGB')

# Optional: export the clipped composite to Google Drive as a GeoTIFF
# so it can be loaded locally with rasterio alongside the DEM.
# Uncomment when ready to export.
#
# export_task = ee.batch.Export.image.toDrive(
#     image=sentinel_thanjavur,
#     description='thanjavur_sentinel2_2020_01',
#     folder='thanjavur-archaeology-gis',
#     region=aoi.geometry(),
#     scale=10,
#     crs='EPSG:32644',
#     maxPixels=1e9,
# )
# export_task.start()

Map
