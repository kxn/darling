#!/usr/bin/env python3
"""Unpack pinned Debian build tools locally, without installing host packages."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/darlingserver-source-build.json').read_text())
destination=root/'runtime/host-build-tools';downloads=destination/'downloads'
downloads.mkdir(parents=True,exist_ok=True)
for package in config['tools']:
    path=downloads/package['filename']
    if not path.exists():
        subprocess.run(['apt-get','download',package['package']+'='+package['version']],cwd=downloads,check=True)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=package['sha256']:
        raise ValueError('Changed build-tool package: '+package['filename'])
    subprocess.run(['dpkg-deb','-x',str(path),str(destination)],check=True)
print('Verified and unpacked local bison/flex/m4; no host package installation')
