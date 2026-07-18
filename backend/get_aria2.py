import urllib.request
import zipfile
import os
import shutil
from pathlib import Path

url = "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"
zip_path = Path("aria2.zip")

print("Downloading aria2c (multi-threaded downloader, ~2MB)...")
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    print("Download complete! Extracting aria2c.exe...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            if file_info.filename.endswith('aria2c.exe'):
                filename = os.path.basename(file_info.filename)
                with zip_ref.open(file_info) as source, open(filename, 'wb') as target:
                    shutil.copyfileobj(source, target)
                print(f"Extracted {filename} successfully!")
                break
    print("aria2c.exe is ready in backend folder!")
except Exception as e:
    print(f"Error: {e}")
finally:
    if zip_path.exists():
        os.remove(zip_path)
