import geopandas as gpd

for name in ["Data/export.geojson", "Data/export (1).geojson"]:
    try:
        gdf = gpd.read_file(name)
        print(f"File: {name}")
        print(f"  Shape: {gdf.shape}")
        print(f"  Columns: {list(gdf.columns)}")
        print(f"  Geometry: {gdf.geom_type.value_counts()}")
        # print first few rows
        print(gdf.head(3))
        print("-" * 50)
    except Exception as e:
        print(f"Error reading {name}: {e}")
