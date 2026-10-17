#!/usr/bin/env python3
"""Pair the real process-policy server with the source VFS enforcing it."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/crypto-quarantine-runtime-profile.py'))['profile']()
server_name='artifacts/quarantine-vfs-server-build.json';server=json.loads((root/server_name).read_text())
assert server['previous_source_runtime']==p['source_runtime']
kernel_name='artifacts/quarantine-vfs-kernel-source-build.json';kernel=json.loads((root/kernel_name).read_text())
assert kernel['full_libsystem_kernel_source_build'] and kernel['complete_source_files']==877
folder=root/'runtime/quarantine-vfs-kernel-source';selected={k:dict(v) for k,v in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for key,item in selected.items():
        if key=='LINUXCODE_LIBSYSTEM_KERNEL':item.update(path='runtime/quarantine-vfs-kernel-source/libsystem_kernel.dylib',sha256=kernel['binary_sha256'])
        else:
            source=server['server'] if key=='LINUXCODE_DARLING_SERVER' else item['path']
            expected=server['server_sha256'] if key=='LINUXCODE_DARLING_SERVER' else item['sha256'];assert digest(source)==expected
            target=folder/Path(source).name;shutil.copy2(root/source,target);item.update(path=str(target.relative_to(root)),sha256=expected)
    for key,name in [('LINUXCODE_LAUNCHD','sbin/launchd'),('LINUXCODE_LIBXPC','usr/lib/system/libxpc.dylib'),('LINUXCODE_LIBSYSTEM_KERNEL','usr/lib/system/libsystem_kernel.dylib'),('LINUXCODE_QUARANTINE','usr/lib/system/libquarantine.dylib'),('LINUXCODE_SANDBOX','usr/lib/system/libsystem_sandbox.dylib'),('LINUXCODE_LIBDYLD','usr/lib/system/libdyld.dylib')]:assert digest(str((folder/'darling-root'/name).relative_to(root)))==selected[key]['sha256']
record=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,kernel_build=kernel_name,kernel_build_sha256=digest(kernel_name),server_build=server_name,server_build_sha256=digest(server_name),kernel_capabilities=0x1000f,supported_self_policy_flags=[6],unsupported_policy_flags_return_errors=True,source_files={n:digest(n) for n in ['runtime/darlingserver-source-build/darlingserver/include/darlingserver/rpc.h','runtime/darlingserver-source-build/darlingserver/internal-include/darlingserver/rpc.internal.h']},full_xcode_build_ready=False)
(root/'artifacts/quarantine-vfs-runtime-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Paired full 877-source kernel with real process-policy backend; old-kernel clients cannot acknowledge this policy')
