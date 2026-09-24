import ee
import geemap

# Authenticate / initialize Earth Engine
ee.Authenticate()
ee.Initialize()

# Load Thanjavur boundary
aoi = geemap.geojson_to_ee(
    "datasets/boundary/thanjavur_boundary.geojson"
)

# Load NASADEM
dem = ee.Image("NASA/NASADEM_HGT/001").select("elevation")

# Clip DEM to Thanjavur
dem_thanjavur = dem.clip(aoi)

# Display
Map = geemap.Map()
Map.centerObject(aoi, 9)

Map.addLayer(
    dem_thanjavur,
    {
        "min": 0,
        "max": 100,
    },
    "Thanjavur DEM"
)

Map