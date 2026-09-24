import sys
with open("check_env_utf8.log", "w", encoding="utf-8") as f:
    f.write(f"Python Path: {sys.executable}\n")
    try:
        import geopandas as gpd
        f.write("geopandas: OK\n")
    except Exception as e:
        f.write(f"geopandas error: {e}\n")

    try:
        import pandas as pd
        f.write("pandas: OK\n")
    except Exception as e:
        f.write(f"pandas error: {e}\n")

    try:
        import rasterio
        f.write("rasterio: OK\n")
    except Exception as e:
        f.write(f"rasterio error: {e}\n")

    try:
        import sklearn
        f.write("scikit-learn: OK\n")
    except Exception as e:
        f.write(f"scikit-learn error: {e}\n")

    try:
        import richdem as rd
        f.write("richdem: OK\n")
    except Exception as e:
        f.write(f"richdem error: {e}\n")

    try:
        import pyrosm
        f.write("pyrosm: OK\n")
    except Exception as e:
        f.write(f"pyrosm error: {e}\n")
