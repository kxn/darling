#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/fsevents-device-runtime-profile.py'));p=m['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/fsevents-device-tests';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/fsevents-device-native.c';obj=build/'native.o';binary=build/'native'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-Wall','-Wextra','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];command[3]='100'
r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr
log='logs/fsevents-device-native-test.log';(root/log).write_text(text)
match=re.search(r'FSEVENTS_DEVICE_NATIVE_ABI_REAL_DELETE_RENAME_DUP_FORK_EXEC_OK checks=(\d+)',text)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=r.returncode,
            checks=int(match[1]) if match else 0,source=source,source_sha256=digest(source),
            binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=log,log_sha256=digest(log),
            source_fsevents_device=p['source_fsevents_device'],
            runtime_execution_verified=r.returncode==0 and match is not None,full_xcode_build_ready=False)
(root/'artifacts/fsevents-device-native-test.json').write_text(json.dumps(report,indent=2)+'\n')
print(r.returncode,text[-6000:]);assert report['runtime_execution_verified']
