#!/usr/bin/env python3
"""Publish a complete private directory variant with the new source libxpc."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/log-pack-profile.py'))['profile']()
build=root/'runtime/xpc-collections-source';source=json.loads((root/'artifacts/xpc-collections-source-build.json').read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
assert source['full_libxpc_source_build'] and source['complete_source_files']==39
assert digest('runtime/xpc-collections-source/libxpc.dylib')==source['library_sha256']
selected={key:dict(value) for key,value in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for key,item in selected.items():
        if key=='LINUXCODE_LIBXPC':
            item.update(path='runtime/xpc-collections-source/libxpc.dylib',sha256=source['library_sha256']);continue
        filename=Path(item['path']).name;target=build/filename
        assert digest(item['path'])==item['sha256']
        pending=target.with_suffix('.pending');shutil.copyfile(root/item['path'],pending);pending.chmod((root/item['path']).stat().st_mode&0o777);pending.replace(target)
        item['path']=str(target.relative_to(root))
    guest=build/'darling-root'
    for key,path in [('LINUXCODE_LAUNCHD','sbin/launchd'),('LINUXCODE_LIBXPC','usr/lib/system/libxpc.dylib'),('LINUXCODE_LIBSYSTEM_KERNEL','usr/lib/system/libsystem_kernel.dylib'),('LINUXCODE_QUARANTINE','usr/lib/system/libquarantine.dylib'),('LINUXCODE_SANDBOX','usr/lib/system/libsystem_sandbox.dylib'),('LINUXCODE_LIBDYLD','usr/lib/system/libdyld.dylib')]:
        assert digest(str((guest/path).relative_to(root)))==selected[key]['sha256'],key
record={'source_build':'artifacts/xpc-collections-source-build.json','source_build_sha256':digest('artifacts/xpc-collections-source-build.json'),'source_runtime':selected,'previous_source_runtime':p['source_runtime'],'full_directory_variant':str(guest.relative_to(root)),'installed':False,'runtime_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/xpc-collections-runtime-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged matching 7 runtime components with the full 39-file source libxpc')
