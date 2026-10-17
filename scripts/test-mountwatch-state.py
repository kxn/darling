#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent;folder=root/'runtime/mount-flags-tests';folder.mkdir(exist_ok=True)
source='fixtures/hello/mountwatch-state.c';header='vendor/darling/src/external/libnotify/notifyd/mountwatch_state.h';binary=folder/'mountwatch-state'
command=['gcc','-std=c11','-D_POSIX_C_SOURCE=200809L','-fsanitize=address,undefined','-g','-I'+str((root/header).parent),str(root/source),'-o',str(binary)];subprocess.run(command,check=True)
a=subprocess.run([str(binary)],capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/mountwatch-state.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();match=re.search(r'LINUX_MOUNTWATCH_STATE_OK checks=(\d+) real_namespace_records=(\d+)',text)
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=a.returncode,source=source,source_sha256=digest(source),header=header,header_sha256=digest(header),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,actual_mountinfo_records=int(match[2]) if match else 0,address_and_undefined_sanitizers=True,controlled_mount_deltas=True,passed=a.returncode==0 and match is not None)
(root/'artifacts/mountwatch-state-test.json').write_text(json.dumps(d,indent=2)+'\n');print(text);assert d['passed']
