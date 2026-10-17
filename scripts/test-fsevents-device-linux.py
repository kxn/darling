#!/usr/bin/env python3
"""Exercise real inotify events and independently decode XNU wire records."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
folder=root/'runtime/fsevents-device-tests';folder.mkdir(exist_ok=True)
source='fixtures/hello/fsevents-device-linux.cpp'
implementation='vendor/darlingserver/src/fsevents-device.cpp'
header='vendor/darlingserver/internal-include/darlingserver/fsevents-device.hpp'
command=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-pthread',
         '-fsanitize=address,undefined','-fno-omit-frame-pointer',
         '-I'+str(root/'vendor/darlingserver/internal-include'),source,implementation,'-o',str(folder/'linux')]
subprocess.run(command,cwd=root,check=True)
result=subprocess.run([str(folder/'linux')],cwd=root,capture_output=True,text=True,timeout=30)
log='logs/fsevents-device-linux-test.log';(root/log).write_text(result.stdout+result.stderr)
print(result.stdout+result.stderr,end='');assert result.returncode==0
match=re.search(r'FSEVENTS_DEVICE_REAL_LINUX_OK checks=(\d+)',result.stdout);assert match
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=result.returncode,
            real_linux_events=True,checks=int(match[1]),asan_ubsan=True,
            inputs={n:digest(n) for n in [source,implementation,header]},log=log,log_sha256=digest(log),
            binary=str((folder/'linux').relative_to(root)),binary_sha256=digest(folder/'linux'),
            supported_events=['delete','rename'],originating_pid_available=False,
            raw_Darling_device_integration_verified=False,full_xcode_build_ready=False)
(root/'artifacts/fsevents-device-linux-test.json').write_text(json.dumps(report,indent=2)+'\n')
