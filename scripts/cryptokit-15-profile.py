#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/argument-parser-native-profile.py'))
def profile(include_system_resources=True):
    p=m['profile'](include_system_resources);d=json.loads((root/'artifacts/cryptokit-15-stage.json').read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
    assert digest(d['reference'])==d['reference_sha256']
    for item in d['images']:
        for key in ['original','framework']:assert digest(item[key])==item[key+'_sha256'],key
    command=list(p['command']);i=next(i for i,a in enumerate(command) if a.startswith('DYLD_FRAMEWORK_PATH='))
    command[i]='DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/cryptokit-15-native/frameworks:'+command[i].split('=',1)[1]
    return {**p,'command':command,'native_cryptokit_15':d}
def environment(p):return m['environment'](p)
