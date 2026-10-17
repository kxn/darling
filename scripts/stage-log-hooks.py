#!/usr/bin/env python3
"""Expose the source log-hook entry without replacing the established runtime."""
from pathlib import Path
import fcntl,hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
base='runtime/native-log-message/libraries/libSystem.B.dylib';old=json.loads((root/'artifacts/native-log-message-stage.json').read_text());assert digest(base)==old['library_sha256']
build=json.loads((root/'artifacts/libtrace-hooks-source-build.json').read_text());assert build['complete_source_files']==9 and digest(build['library'])==build['library_sha256']
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/libTrace.dylib',['_os_log_set_hook'])
output='runtime/log-hooks/libraries/libSystem.B.dylib';target=root/output;target.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);temporary=target.with_suffix('.pending');temporary.write_bytes(payload);temporary.replace(target)
overlay=root/'runtime/log-hooks/include/os';overlay.mkdir(parents=True,exist_ok=True)
header=overlay/'log_private.h'
if not header.is_symlink():header.symlink_to(root/'vendor/darling/src/external/libtrace/include/os/log_private.h')
report=dict(base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),source_build=build,export_changes=changes,installed=False,runtime_execution_verified=False)
(root/'artifacts/log-hooks-stage.json').write_text(json.dumps(report,indent=2)+'\n');print('Staged the real source log-hook export and coherent libtrace build')
