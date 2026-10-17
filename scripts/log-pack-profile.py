#!/usr/bin/env python3
"""Select the complete source log-pack implementation within the native profile."""
from pathlib import Path
import json,os,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/foundation-coherent-profile.py'))
environment=m['environment']
def profile():
    overrides={'LINUXCODE_LIBTRACE_BUILD_REPORT':'artifacts/libtrace-pack-source-build.json','LINUXCODE_FSEVENTS_BUILD_REPORT':'artifacts/fsevents-heap-source-build.json'}
    previous={key:os.environ.get(key) for key in overrides}
    try:
        os.environ.update(overrides)
        p=m['profile']()
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
    build=json.loads((root/'artifacts/libtrace-pack-source-build.json').read_text())
    assert p['source_libtrace']==build
    return {**p,'source_log_pack':build}
