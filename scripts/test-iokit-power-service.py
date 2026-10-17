#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,runpy,subprocess
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/iokitd-power-runtime-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
folder=root/'runtime/iokitd-power-tests';folder.mkdir(exist_ok=True)
source=root/'fixtures/hello/iokit-power-service.c';binary=folder/'power-service';obj=folder/'power-service.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-Wno-deprecated-declarations','-c',str(source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-framework','IOKit','-framework','CoreFoundation',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True)
output=a.stdout+a.stderr;log=root/'logs/iokit-power-service.log';log.write_text(output)
digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
match=re.search(r'IOKIT_POWER_SERVICE_OK checks=(\d+) cycles=128 physical_ool_cases=7',output)
report=dict(runtime_execution_verified=a.returncode==0 and match is not None,checks=int(match[1]) if match else 0,physical_ool_cases=7,connection_subscription_cycles=128,physical_host_suspend_verified=False,sleep_barrier_implemented=False,checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,source=str(source.relative_to(root)),source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=str(log.relative_to(root)),log_sha256=digest(log),source_iokitd_power=p['source_iokitd_power'],full_xcode_build_ready=False)
(root/'artifacts/iokit-power-service-test.json').write_text(json.dumps(report,indent=2)+'\n');print(output);assert report['runtime_execution_verified']
