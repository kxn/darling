#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/objc-selector-source-profile.py'));environment=m['environment']
def profile():
 p=m['profile']();stage=json.loads((root/'artifacts/foundation-coherent-stage.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
 for key in ['original','source','library','reconstruction']:assert digest(stage['shim'][key])==stage['shim'][key+'_sha256']
 for key in ['base','library','provider']:assert digest(stage['float_class'][key])==stage['float_class'][key+'_sha256']
 c=list(p['command']);i=next(i for i,v in enumerate(c) if v.startswith('DYLD_LIBRARY_PATH='));c[i]='DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-coherent/libraries:'+c[i].split('=',1)[1]
 return {**p,'command':c,'foundation_coherent':stage}
