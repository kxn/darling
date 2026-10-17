#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/iokitd-matching-runtime-profile.py'));p=m['profile']()
folder=root/'runtime/iokitd-matching-tests';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/iokit-power-service.c';obj=folder/'power.o';binary=folder/'power'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-framework','IOKit','-framework','CoreFoundation',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr
log='logs/iokitd-matching-power-regression.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();match=re.search(r'IOKIT_POWER_SERVICE_OK checks=(\d+) cycles=128 physical_ool_cases=7',text)
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,lifetime_cycles=128,physical_ool_cases=7,runtime_execution_verified=a.returncode==0 and match is not None,source_iokitd_matching=p['source_iokitd_matching'],full_xcode_build_ready=False)
(root/'artifacts/iokitd-matching-power-regression.json').write_text(json.dumps(d,indent=2)+'\n');print(text);assert d['runtime_execution_verified']
