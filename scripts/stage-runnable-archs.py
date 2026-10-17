#!/usr/bin/env python3
"""Expose the new source libdyld API through the existing libSystem umbrella."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,runpy
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
base='runtime/container-persona/libraries/libSystem.B.dylib';old=json.loads((root/'artifacts/container-persona-stage.json').read_text());assert digest(base)==old['library_sha256']
report='artifacts/runnable-archs-source-build.json';build=json.loads((root/report).read_text());assert build['full_libdyld_source_build'] and build['complete_source_files']==29
source_lib='runtime/runnable-archs-source/libdyld.dylib';assert digest(source_lib)==build['library_sha256']
for n,sha in build['source_files'].items():assert digest('vendor/darling/src/external/dyld/'+n)==sha
payload,changes=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))['add']((root/base).read_bytes(),'/usr/lib/system/libdyld.dylib',['_macho_for_each_runnable_arch_name'])
output='runtime/runnable-archs-source/libraries/libSystem.B.dylib';(root/output).parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending=root/(output+'.pending');pending.write_bytes(payload);pending.replace(root/output)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),source_library=source_lib,source_library_sha256=digest(source_lib),build_report=report,build_report_sha256=digest(report),export_changes=changes,installed=False,runtime_execution_verified=False,scope='Complete 29-file source libdyld. Only the new public entry is named-reexported by the libSystem umbrella; no hook, replacement backend or copied original function is installed for this API.')
(root/'artifacts/runnable-archs-source-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged source libdyld API and named libSystem export')
