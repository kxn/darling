#!/usr/bin/env python3
"""Re-execute existing native IPC and filesystem clients against the new kernel."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'));p=m['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
tests=[('power','artifacts/iokitd-matching-power-regression.json',r'IOKIT_POWER_SERVICE_OK checks=(\d+) cycles=128 physical_ool_cases=7'),
 ('matching','artifacts/iokitd-matching-test.json',r'IOKIT_MATCHING_NATIVE_CALLBACKS_OK checks=(\d+) callbacks=11 cycles=128'),
 ('fsevents','artifacts/fsevents-device-native-test.json',r'FSEVENTS_DEVICE_NATIVE_ABI_REAL_DELETE_RENAME_DUP_FORK_EXEC_OK checks=(\d+)')]
results={}
for name,prior,marker in tests:
 d=json.loads((root/prior).read_text());assert d['runtime_execution_verified']
 assert digest(d['binary'])==d['binary_sha256']
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+d['binary']];command[3]='100'
 a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr
 log='logs/mount-runtime-'+name+'-regression.log';(root/log).write_text(text);match=re.search(marker,text)
 results[name]=dict(prior_report=prior,prior_report_sha256=digest(prior),binary=d['binary'],binary_sha256=digest(d['binary']),command=command,exit_status=a.returncode,log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,runtime_execution_verified=a.returncode==0 and match is not None)
 print(name,a.returncode,text[-1500:],flush=True)
 assert results[name]['runtime_execution_verified']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_mount_flags=p['source_mount_flags'],results=results,runtime_execution_verified=True,full_xcode_build_ready=False)
(root/'artifacts/mount-runtime-regressions.json').write_text(json.dumps(record,indent=2)+'\n')
