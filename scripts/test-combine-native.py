#!/usr/bin/env python3
"""Compile the unmodified Apple SDK interface client and run original Combine."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/combine-native-profile.py'));p=m['profile']();environment=m['environment'](p);guest='/Volumes/SystemRoot/workspace/'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';sdk_guest='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O2','-c','fixtures/hello/combine-native-owner.c','-o','artifacts/combine-native-owner.o'],cwd=root,check=True)
steps=[('compile',[toolchain+'/usr/bin/swift-frontend','-c',guest+'fixtures/hello/combine-native.swift','-target','x86_64-apple-macos14.0','-sdk',sdk_guest,'-module-name','OriginalCombineNativeProbe','-o',guest+'artifacts/combine-native.o']),('link',[toolchain+'/usr/bin/clang','-target','x86_64-apple-macos14.0','-isysroot',sdk_guest,guest+'artifacts/combine-native.o',guest+'artifacts/combine-native-owner.o','-L/usr/lib/swift','-lswiftCore','-lswiftSwiftOnoneSupport','-framework','Combine','-Wl,-rpath,/usr/lib/swift','-o',guest+'artifacts/combine-native']),('execute',[guest+'artifacts/combine-native'])]
checks=[]
for name,tail in steps:
 command=p['command'][:-2]+tail
 if name=='compile':command[3]='180'
 r=subprocess.run(command,cwd=root,env=environment,capture_output=True,text=True);log='logs/combine-native-'+name+'.log';(root/log).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout+r.stderr,flush=True);checks.append(dict(step=name,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log)))
 if r.returncode:break
verified=len(checks)==3 and checks[-1]['exit_status']==0 and 'NATIVE_COMBINE_ALL_CHECKED_SEMANTICS_OK' in (root/checks[-1]['log']).read_text()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'runtime_execution_verified':verified,'original_Apple_SDK_interface_used':True,'sources':{n:digest(n) for n in ['fixtures/hello/combine-native.swift','fixtures/hello/combine-native-owner.c']},'full_Combine_compatibility':False}
for name in ['artifacts/combine-native.o','artifacts/combine-native']:
 if (root/name).exists():record.setdefault('binaries',{})[name]=digest(name)
(root/'artifacts/combine-native-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if verified else 1)
