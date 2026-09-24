import json

def inspect_file(filename, log_file):
    log_file.write(f"Inspecting {filename}:\n")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        log_file.write(f"Keys: {list(data.keys())}\n")
        if "features" in data:
            log_file.write(f"Number of features: {len(data['features'])}\n")
            if len(data["features"]) > 0:
                log_file.write(f"First feature properties: {data['features'][0].get('properties', {})}\n")
                log_file.write(f"First feature geometry type: {data['features'][0].get('geometry', {}).get('type', 'None')}\n")
                # Look at another feature if first has empty properties
                for i in range(min(10, len(data["features"]))):
                    p = data["features"][i].get("properties", {})
                    if p:
                        log_file.write(f"Feature {i} properties: {p}\n")
            else:
                log_file.write("Features is empty\n")
        else:
            log_file.write("No features key\n")
    except Exception as e:
        log_file.write(f"Error: {e}\n")
    log_file.write("=" * 50 + "\n")

with open("read_export.log", "w", encoding="utf-8") as f_out:
    inspect_file("Data/export.geojson", f_out)
    inspect_file("Data/export (1).geojson", f_out)
