#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess,re
root=Path(__file__).resolve().parent.parent;sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c','fixtures/hello/objc-selected-owner.c','-o','artifacts/objc-selected-owner.o'],cwd=root,check=True);subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lobjc','-lSystem','artifacts/objc-selected-owner.o','-o','artifacts/objc-selected-owner'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/fsevents-flush-profile.py'));p=m['profile']();command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/objc-selected-owner'];r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/objc-selected-owner.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='');digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/objc-selected-owner.c'),'binary_sha256':digest('artifacts/objc-selected-owner'),'runtime_execution_verified':r.returncode==0}
(root/'artifacts/objc-selected-owner-probe.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
