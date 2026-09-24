import json
import os

with open("Data/raw/boundary/thanjavur_boundary.geojson", "r", encoding="utf-8") as f:
    boundary_data = json.load(f)

print("Boundary GeoJSON keys:", list(boundary_data.keys()))
if "features" in boundary_data:
    print("Num boundary features:", len(boundary_data["features"]))
    feat = boundary_data["features"][0]
    print("Boundary Properties:", feat.get("properties", {}))
    print("Boundary Geometry Type:", feat.get("geometry", {}).get("type", "None"))
    coords = feat.get("geometry", {}).get("coordinates", [])
    print("Coordinates sample (depth-1 length):", len(coords))
