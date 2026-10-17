#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/container-persona-profile.py'));environment=m['environment']
def profile():
 p=m['profile']();stage=json.loads((root/'artifacts/mobilegestalt-native-stage.json').read_text())
 for key in ['source','library','reconstruction']:assert hashlib.sha256((root/stage[key]).read_bytes()).hexdigest()==stage[key+'_sha256']
 for key in ['source','library','reconstruction']:assert hashlib.sha256((root/stage['dependency'][key]).read_bytes()).hexdigest()==stage['dependency'][key+'_sha256']
 for key in ['source','library','reconstruction']:assert hashlib.sha256((root/stage['oah_dependency'][key]).read_bytes()).hexdigest()==stage['oah_dependency'][key+'_sha256']
 for key in ['source','library']:assert hashlib.sha256((root/stage['typed_cpp_adapter'][key]).read_bytes()).hexdigest()==stage['typed_cpp_adapter'][key+'_sha256']
 c=list(p['command']);i=next(i for i,v in enumerate(c) if v.startswith('DYLD_LIBRARY_PATH='));c[i]='DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/mobilegestalt-native/libraries:'+c[i].split('=',1)[1]
 i=next(i for i,v in enumerate(c) if v.startswith('DYLD_FRAMEWORK_PATH='));c[i]='DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/mobilegestalt-native/frameworks:'+c[i].split('=',1)[1]
 return {**p,'command':c,'mobilegestalt_native':stage}
