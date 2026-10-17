#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/foundation-coherent-profile.py'));p=m['profile']();guest='/Volumes/SystemRoot/workspace/';toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain';sdk='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();checks=[]
entries=[('float-compile',[toolchain+'/usr/bin/clang','-target','x86_64-apple-macos14','-isysroot',sdk,'-Xclang','-fobjc-constant-literals',guest+'fixtures/hello/constant-float-number.m','-L'+guest+'runtime/foundation-coherent/libraries','-lDarlingConstantFloat','-framework','Foundation','-framework','CoreFoundation','-o',guest+'artifacts/constant-float-native-smoke'],None),('float-execute',[guest+'artifacts/constant-float-native-smoke'],'APPLE_CLANG_CONSTANT_FLOAT_LAYOUT_BITS_CF_BRIDGE_EQUALITY_HASH_COPY_OK')]
for name,tail,marker in entries:
 command=p['command'][:-2]+tail;log='logs/foundation-coherent-'+name+'.log'
 with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
 text=(root/log).read_text();verified=r.returncode==0 and (marker is None or marker in text) and 'is implemented in both' not in text;checks.append(dict(name=name,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),verified=verified));print(name,r.returncode,text[-3000:],flush=True)
 if not verified:break
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'source_sha256':digest('fixtures/hello/constant-float-number.m'),'runtime_execution_verified':len(checks)==2 and all(c['verified'] for c in checks),'full_Foundation_compatibility':False}
if (root/'artifacts/constant-float-native-smoke').exists():record['binary_sha256']=digest('artifacts/constant-float-native-smoke')
(root/'artifacts/foundation-coherent-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['runtime_execution_verified'] else 1)
