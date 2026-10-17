#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/container-persona-profile.py'));environment=m['environment']
def profile():
 p=m['profile']();stage=json.loads((root/'artifacts/mobilegestalt-source-build.json').read_text())
 for key in ['source','header','cmake','library','object','original']:assert hashlib.sha256((root/stage[key]).read_bytes()).hexdigest()==stage[key+'_sha256']
 c=list(p['command']);i=next(i for i,v in enumerate(c) if v.startswith('DYLD_LIBRARY_PATH='));c[i]='DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/mobilegestalt-source/libraries:'+c[i].split('=',1)[1]
 return {**p,'command':c,'mobilegestalt_source':stage}
