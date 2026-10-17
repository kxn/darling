#!/usr/bin/env python3
"""Exercise the unmodified Darling NSView caller with actual bitmap output."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'runtime/native-layer-context/include'),'-fblocks','-O2','-c','fixtures/hello/native-layer-appkit.m','-o','artifacts/native-layer-appkit.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L',str(root/'runtime/native-layer-context/libraries'),'-lDarlingNativeLayerContext','-framework','Foundation','-framework','AppKit','-framework','QuartzCore','-framework','CoreGraphics','-framework','CoreFoundation','-lobjc','-lSystem','artifacts/native-layer-appkit.o','-o','artifacts/native-layer-appkit'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/log-enablement-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/native-layer-appkit']
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/native-layer-appkit.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='')
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/native-layer-appkit.m'),'binary_sha256':digest('artifacts/native-layer-appkit'),'runtime_execution_verified':r.returncode==0,'window_backend_verified':False}
(root/'artifacts/native-layer-appkit-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
