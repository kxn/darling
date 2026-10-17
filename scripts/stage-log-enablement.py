#!/usr/bin/env python3
"""Expose the source libtrace comparator through the selected libSystem."""
from pathlib import Path
import fcntl, hashlib, json, runpy
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
base='runtime/container-manager-export/libraries/libSystem.B.dylib'
previous=json.loads((root/'artifacts/container-manager-export-stage.json').read_text())
assert digest(base)==previous['library_sha256']
build=json.loads((root/'artifacts/libtrace-enablement-source-build.json').read_text())
assert digest(build['library'])==build['library_sha256']
api=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))
payload,changes=api['add']((root/base).read_bytes(),'/usr/lib/libTrace.dylib',['_os_log_compare_enablement'])
output='runtime/log-enablement/libraries/libSystem.B.dylib';target=root/output;target.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending=target.with_suffix('.pending');pending.write_bytes(payload);pending.replace(target)
record=dict(base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),source_build=build,export_changes=changes,installed=False,runtime_execution_verified=False)
(root/'artifacts/log-enablement-stage.json').write_text(json.dumps(record,indent=2)+'\n')
print('Exposed source log-level comparator through private libSystem')
