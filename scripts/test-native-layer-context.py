#!/usr/bin/env python3
"""Verify actual offscreen pixels, ownership/state and explicit headless failures."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';include=root/'runtime/native-layer-context/include'
commands=[['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(include),'-O2','-fblocks','-c','fixtures/hello/native-layer-context.m','-o','artifacts/native-layer-context.o'],['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L',str(root/'runtime/native-layer-context/libraries'),'-lDarlingNativeLayerContext','-framework','Foundation','-framework','QuartzCore','-framework','CoreGraphics','-framework','CoreFoundation','-lobjc','-lSystem','artifacts/native-layer-context.o','-o','artifacts/native-layer-context']]
for c in commands:subprocess.run(c,cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/native-layer-context-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/native-layer-context'];log='logs/native-layer-context-test.log'
with (root/log).open('w') as f:
 proc=subprocess.Popen(c,cwd=root,env=m['environment'](p),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 for line in proc.stdout:f.write(line);f.flush();print(line,end='',flush=True)
 status=proc.wait()
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':status,'log':log,'log_sha256':digest(log),'diagnostic':(root/log).read_text(),'source_sha256':digest('fixtures/hello/native-layer-context.m'),'binary_sha256':digest('artifacts/native-layer-context'),'runtime_execution_verified':status==0,'full_xcode_build_ready':False,'window_or_OpenGL_backend_verified':False}
(root/'artifacts/native-layer-context-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(status)
