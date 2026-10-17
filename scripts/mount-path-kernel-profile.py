#!/usr/bin/env python3
from pathlib import Path
import runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/metadata-kernel-profile.py'))
environment=m['environment']
def profile():
 return m['profile']('artifacts/mount-path-kernel-vfs-baseline.json','runtime/mount-path-kernel-source')
