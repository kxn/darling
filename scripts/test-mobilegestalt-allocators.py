#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang++-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-std=c++17','-O2','-c','fixtures/hello/mobilegestalt-allocators.cpp','-o','artifacts/mobilegestalt-allocators.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lc++','-lSystem','artifacts/mobilegestalt-allocators.o','-o','artifacts/mobilegestalt-allocators'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/mobilegestalt-native-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/mobilegestalt-allocators']
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/mobilegestalt-allocators.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='')
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/mobilegestalt-allocators.cpp'),'binary_sha256':digest('artifacts/mobilegestalt-allocators'),'runtime_execution_verified':r.returncode==0,'typed_zone_isolation_verified':False}
(root/'artifacts/mobilegestalt-allocators-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
