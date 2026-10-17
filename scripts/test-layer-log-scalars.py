#!/usr/bin/env python3
"""Differential native scalar checks plus real Onyx graphics state and pixels."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
subprocess.run(['python3','scripts/analyze-layer-log-native.py'],cwd=root,check=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
for src,obj in [('runtime/layer-log-reference/reference.S','runtime/layer-log-reference/reference.o'),('fixtures/hello/layer-log-scalars.m','artifacts/layer-log-scalars.o')]:
 subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-c',src,'-o',obj],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreGraphics','-lobjc','-lSystem','artifacts/layer-log-scalars.o','runtime/layer-log-reference/reference.o','-o','artifacts/layer-log-scalars'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/log-enablement-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/layer-log-scalars']
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/layer-log-scalars.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='')
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/layer-log-scalars.m'),'binary_sha256':digest('artifacts/layer-log-scalars'),'reference_analysis_sha256':digest('artifacts/layer-log-native-analysis.json'),'runtime_execution_verified':r.returncode==0}
(root/'artifacts/layer-log-scalars-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
