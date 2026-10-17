#!/usr/bin/env python3
"""Verify real source logging callbacks against the original native formatter."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'runtime/log-hooks/include'),'-fblocks','-O2','-c','fixtures/hello/log-hooks.m','-o','artifacts/log-hooks.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem','artifacts/log-hooks.o','-o','artifacts/log-hooks'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/log-hooks-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/log-hooks']
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/log-hooks-test.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='')
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/log-hooks.m'),'binary_sha256':digest('artifacts/log-hooks'),'runtime_execution_verified':r.returncode==0,'full_unified_log_service_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/log-hooks-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
