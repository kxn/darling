#!/usr/bin/env python3
"""Fetch the tested Darwin gem lock using Linux TLS; verify every payload."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

project = Path(__file__).resolve().parent.parent
lock = json.loads((project / 'config/cocoapods-gems.lock.json').read_text())
cache = project / 'runtime/gem-offline-cache'
cache.mkdir(parents=True, exist_ok=True)

def fetch(item):
    path = cache / item['file']
    if not path.exists():
        request = urllib.request.Request('https://rubygems.org/downloads/'+item['file'])
        with urllib.request.urlopen(request, timeout=60) as response:
            path.with_suffix('.part').write_bytes(response.read())
        path.with_suffix('.part').replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('Gem checksum mismatch: '+item['file'])
    return item['file']

with ThreadPoolExecutor(max_workers=6) as pool:
    for name in pool.map(fetch, [lock['rubygems'], *lock['gems']]):
        print('Verified '+name, flush=True)
