#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/log-enablement-profile.py'));environment=m['environment']
def profile(source_build=None):
 p=m['profile'](source_build=source_build);stage=json.loads((root/'artifacts/native-log-message-stage.json').read_text())
 for key in ['base','library','helper','source','provider','reconstruction']:assert hashlib.sha256((root/stage[key]).read_bytes()).hexdigest()==stage[key+'_sha256']
 c=list(p['command']);i=next(i for i,v in enumerate(c) if v.startswith('DYLD_LIBRARY_PATH='));c[i]='DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/native-log-message/libraries:'+c[i].split('=',1)[1]
 return {**p,'command':c,'native_log_message':stage}
