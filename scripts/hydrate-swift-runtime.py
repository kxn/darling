#!/usr/bin/env python3
"""Replace incorrectly packaged Git LFS pointers with verified upstream binaries."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

project = Path(__file__).resolve().parent.parent
runtime = project / "runtime/rootfs/usr/libexec/darling/usr/lib/swift"
cache = project / "downloads/swift-lfs"
cache.mkdir(parents=True, exist_ok=True)
pointers = {}
for path in runtime.glob("*.dylib"):
    if path.stat().st_size > 1024:
        continue
    data = path.read_text()
    if not data.startswith("version https://git-lfs.github.com/spec/v1\n"):
        continue
    fields = dict(line.split(" ", 1) for line in data.splitlines())
    oid = fields["oid"].removeprefix("sha256:")
    pointers[oid] = (path, int(fields["size"]))
if not pointers:
    print("Swift runtime is already hydrated.")
    raise SystemExit
request = urllib.request.Request(
    "https://github.com/darlinghq/darling-swift.git/info/lfs/objects/batch",
    data=json.dumps({"operation": "download", "transfers": ["basic"], "objects": [
        {"oid": oid, "size": value[1]} for oid, value in pointers.items()
    ]}).encode(),
    headers={"Content-Type": "application/vnd.git-lfs+json", "Accept": "application/vnd.git-lfs+json"},
)
with urllib.request.urlopen(request) as response:
    objects = json.load(response)["objects"]

def install(item):
    oid = item["oid"]
    path, size = pointers[oid]
    cached = cache / oid
    if not cached.exists():
        action = item["actions"]["download"]
        download = urllib.request.Request(action["href"], headers=action.get("header", {}))
        with urllib.request.urlopen(download) as source, cached.with_suffix(".part").open("wb") as output:
            shutil.copyfileobj(source, output)
        cached.with_suffix(".part").rename(cached)
    if cached.stat().st_size != size or hashlib.sha256(cached.read_bytes()).hexdigest() != oid:
        raise ValueError(f"LFS integrity check failed: {path.name}")
    shutil.copyfile(cached, path)
    path.chmod(0o755)
    print(f"Installed {path.name} ({size} bytes)", flush=True)

with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(install, objects))
