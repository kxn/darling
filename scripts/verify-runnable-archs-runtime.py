#!/usr/bin/env python3
"""Exercise existing loader lifetimes, snapshots and native TLV with the new libdyld."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/runnable-archs-profile.py'));p=m['profile']();guest='/Volumes/SystemRoot/workspace/'
entries=[('loader',[guest+'artifacts/dyld-dlopen-header',*[guest+'runtime/libdyld-source/fixtures/'+s for s in ['empty.dylib','reexport.dylib','empty.bundle']]],['DYLD_DLOPEN_HEADER_API_OWNED_BY_ACTUAL_LIBDYLD_OK','DYLD_DLOPEN_HEADER_REAL_EIGHT_THREADS_512_DLOPEN_QUERY_DLCLOSE_CYCLES_OK']),('snapshot',[guest+'artifacts/dyld-process-snapshot',guest+'runtime/dyld-cache-introspection/fixture.dylib'],['REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK']),('tlv',[guest+'artifacts/metadata-thread-local'],['ORIGINAL_METADATA_EXPORTED_TLV_THREE_THREADS_ZERO_INITIALIZATION_DISTINCT_STORAGE_ISOLATION_OK'])]
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest();checks=[]
for name,tail,markers in entries:
 command=p['command'][:-2]+tail;r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/runnable-archs-'+name+'-regression.log';(root/log).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout+r.stderr,flush=True);verified=r.returncode==0 and all(any(line==n or line.startswith(n+' ') for line in r.stdout.splitlines()) for n in markers)
 checks.append(dict(name=name,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),binary_sha256=digest(tail[0].removeprefix(guest)),verified=verified))
 if not verified:break
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'runtime_execution_verified':len(checks)==3 and all(c['verified'] for c in checks),'full_xcode_build_ready':False,'signing_ready':False}
(root/'artifacts/runnable-archs-runtime-regressions.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['runtime_execution_verified'] else 1)
