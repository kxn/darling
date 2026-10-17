#!/usr/bin/env python3
"""Download the public Apple recovery payload in validated HTTP byte ranges."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace
import urllib.request

project = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("macrecovery", project / "vendor/macrecovery/macrecovery.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
info_path = project / "downloads/recovery-info.json"
if not info_path.exists():
    session = module.get_session(SimpleNamespace(verbose=False))
    info = module.get_image_info(session, bid="Mac-27AD2F918AE68F61", os_type="latest")
    info_path.write_text(json.dumps(info, indent=2) + "\n")
else:
    info = json.loads(info_path.read_text())
output = project / "downloads/recovery"
parts = output / "chunks"
parts.mkdir(parents=True, exist_ok=True)
chunklist = output / 'BaseSystem.chunklist'
if not chunklist.exists():
    request = urllib.request.Request(info['CU'], headers={
        'User-Agent': 'InternetRecovery/1.0', 'Cookie': 'AssetToken=' + info['CT'],
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        chunklist.write_bytes(response.read())
    list(module.verify_chunklist(str(chunklist)))
headers = {"User-Agent": "InternetRecovery/1.0", "Cookie": "AssetToken=" + info["AT"]}
with urllib.request.urlopen(urllib.request.Request(info["AU"], headers=headers, method="HEAD"), timeout=30) as response:
    length = int(response.headers["Content-Length"])
chunk_size = 1024 * 1024
count = (length + chunk_size - 1) // chunk_size

def fetch(index):
    start = index * chunk_size
    end = min(length - 1, start + chunk_size - 1)
    path = parts / f"{index:06d}"
    if path.exists() and path.stat().st_size == end - start + 1:
        return index
    for attempt in range(20):
        try:
            # A distinct cache key avoids CDN nodes retaining truncated responses.
            request = urllib.request.Request(info["AU"] + f"?range={start}&attempt={attempt}", headers={**headers, "Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(request, timeout=15) as response:
                expected = f"bytes {start}-{end}/{length}"
                if response.status != 206 or response.headers.get("Content-Range") != expected:
                    raise ValueError("Server did not honor the requested byte range")
                data = response.read()
            if len(data) != end - start + 1:
                raise ValueError("Truncated recovery range")
            path.with_suffix('.part').write_bytes(data)
            path.with_suffix('.part').replace(path)
            return index
        except Exception:
            if attempt == 19:
                raise
            time.sleep(min(attempt + 1, 5))

with ThreadPoolExecutor(max_workers=16) as pool:
    for completed, _ in enumerate(pool.map(fetch, range(count)), 1):
        if completed % 64 == 0 or completed == count:
            print(f"Recovery download: {completed}/{count} ranges", flush=True)
destination = output / "BaseSystem.dmg"
with destination.open("wb") as stream:
    for index in range(count):
        stream.write((parts / f"{index:06d}").read_bytes())
module.verify_image(str(destination), str(chunklist))
print("Apple recovery chunklist verification passed.", flush=True)
