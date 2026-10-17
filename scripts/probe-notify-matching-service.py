#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,runpy,subprocess
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/iokitd-matching-runtime-profile.py'));p=m['profile']()
folder=root/'runtime/iokitd-matching-tests';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/notify-matching-service.c';binary=folder/'notify-client';obj=folder/'notify-client.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
script=folder/'notify-client.sh';script.write_text('#!/bin/bash\n/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))+'\nstatus=$?\nlaunchctl list com.apple.notifyd || true\nexit "$status"\n')
command=p['command'][:-2]+['/bin/bash','/Volumes/SystemRoot/workspace/'+str(script.relative_to(root))]
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr
log='logs/notify-matching-service.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();match=re.search(r'NOTIFY_CROSS_PROCESS_MACH_DELIVERY_OK checks=(\d+)',text)
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),script=str(script.relative_to(root)),script_sha256=digest(script),log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,source_iokitd_matching=p['source_iokitd_matching'],runtime_execution_verified=a.returncode==0 and match is not None,actual_Linux_mount_event_verified=False,full_xcode_build_ready=False)
(root/'artifacts/notify-matching-service-probe.json').write_text(json.dumps(d,indent=2)+'\n');print(text);assert d['runtime_execution_verified']
