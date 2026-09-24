import json
import os

def inspect_file(filename, log):
    log.write(f"Inspecting {filename}:\n")
    if not os.path.exists(filename):
        log.write("  File does not exist\n")
        return
    try:
        size = os.path.getsize(filename)
        log.write(f"  Size: {size / (1024*1024):.2f} MB\n")
        # Since it is a geojson, we can load it to see features
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            log.write(f"  Keys: {list(data.keys())}\n")
            if "features" in data:
                log.write(f"  Number of features: {len(data['features'])}\n")
                keys = set()
                for feat in data["features"][:1000]:
                    keys.update(feat.get("properties", {}).keys())
                log.write(f"  Sample tags in first 1000 features: {list(keys)[:30]}\n")
            else:
                log.write("  No features key\n")
    except Exception as e:
        log.write(f"Error: {e}\n")
    log.write("=" * 50 + "\n")

with open("read_raw_osm.log", "w", encoding="utf-8") as f_out:
    inspect_file("Data/raw/osm/thanjavur_osm_alt.geojson", f_out)
    inspect_file("Data/raw/osm/thanjavur_osm_full.geojson", f_out)
