#!/usr/bin/env python3
"""Replay the original Sandbox SDK client against the new server/kernel pair."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
old=json.loads((root/'artifacts/unrestricted-sandbox-native-test.json').read_text())
for key in ['source','binary']:assert digest(old[key])==old[key+'_sha256']
m=runpy.run_path(str(root/'scripts/fsevents-device-runtime-profile.py'));p=m['profile']()
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+old['binary']]
dump=root/'runtime/unrestricted-sandbox-tests/explicit-profile.bin';before=dump.read_bytes()
try:
    result=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True)
    assert dump.read_bytes()==before,'The original compiler produced a different policy; preserve and review separately'
finally:
    if dump.read_bytes()!=before:
        (root/'runtime/fsevents-device-tests/changed-explicit-profile.bin').write_bytes(dump.read_bytes())
        dump.write_bytes(before)
text=result.stdout+result.stderr;log='logs/fsevents-device-sandbox-regression.log';(root/log).write_text(text)
match=re.search(r'UNRESTRICTED_ORIGINAL_COMPILER_APPLY_NOTIFY_QUERY_FORK_EXEC_AND_RESTRICTIVE_FAILURES_OK checks=(\d+)',text)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=result.returncode,
            checks=int(match[1]) if match else 0,source=old['source'],source_sha256=old['source_sha256'],
            binary=old['binary'],binary_sha256=old['binary_sha256'],log=log,log_sha256=digest(log),
            source_fsevents_device=p['source_fsevents_device'],runtime_execution_verified=result.returncode==0 and match is not None,
            restrictive_profile_application_verified=False,full_xcode_build_ready=False)
(root/'artifacts/fsevents-device-sandbox-regression.json').write_text(json.dumps(report,indent=2)+'\n')
print(result.returncode,text[-5000:]);assert report['runtime_execution_verified'] and report['checks']==238
