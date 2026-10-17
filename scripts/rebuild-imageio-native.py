#!/usr/bin/env python3
"""Reconstruct pinned original ImageIO and its original codec dependency images."""
from pathlib import Path
import concurrent.futures,json,subprocess
root=Path(__file__).resolve().parent.parent
names=['imageio-native','apple-jpeg-native','colorsync-native','iosurface-accelerator-native','ate-native']+['imageio-'+s.lower()+'-native' for s in ['Png','TIFF','GIF','JP2','JPEG','Radiance']]
def build(name):
 log=root/('logs/rebuild-'+name+'.log')
 with log.open('w') as stream:r=subprocess.run(['python3','scripts/rebuild-c-cache-image.py','--target',name,'--lazy-functions','--analyze-code'],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
 print(name,r.returncode,flush=True);return r.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(build,names))
raise SystemExit(1 if any(results) else 0)
