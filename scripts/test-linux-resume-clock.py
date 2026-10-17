#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,subprocess
from datetime import datetime,timezone
root=Path(__file__).resolve().parent.parent
source='fixtures/hello/linux-resume-clock.cpp';header='vendor/darling/src/external/iokitd/src/LinuxResumeClock.h';binary='runtime/iokitd-power-tests/resume-clock'
command=['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str((root/header).parent),str(root/source),'-o',str(root/binary)]
subprocess.run(command,check=True);p=subprocess.run([str(root/binary)],capture_output=True,text=True);output=p.stdout+p.stderr
log='logs/linux-resume-clock-test.log';(root/log).write_text(output);match=re.search(r'LINUX_RESUME_CLOCK checks=(\d+)',output)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=p.returncode,checks=int(match[1]) if match else 0,source=source,source_sha256=digest(source),header=header,header_sha256=digest(header),binary=binary,binary_sha256=digest(binary),log=log,log_sha256=digest(log),address_and_undefined_sanitizers=True,synthetic_clock_samples=True,physical_host_suspend_verified=False,passed=p.returncode==0 and match is not None)
(root/'artifacts/linux-resume-clock-test.json').write_text(json.dumps(d,indent=2)+'\n');print(output);assert d['passed']
