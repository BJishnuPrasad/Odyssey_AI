import zipfile
import os

with zipfile.ZipFile("Data_zipped.zip", "r") as z:
    print("Files in zip:")
    for f in z.namelist():
        print(f" - {f}")
    # Extract all files under Data/ that do not exist or just extract everything
    z.extractall(".")
print("Done extracting!")
