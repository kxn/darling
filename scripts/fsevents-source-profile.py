#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/combine-native-profile.py'));environment=m['environment']
def profile():
 p=m['profile']();stage=json.loads((root/'artifacts/fsevents-source-build.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
 for key in ['original','library']:assert digest(stage[key])==stage[key+'_sha256']
 for n,sha in {**stage['sources'],**stage['headers']}.items():assert digest(n)==sha
 c=list(p['command']);i=next(i for i,v in enumerate(c) if v.startswith('DYLD_FRAMEWORK_PATH='));c[i]='DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/fsevents-source/frameworks:'+c[i].split('=',1)[1]
 return {**p,'command':c,'source_fsevents':stage}
