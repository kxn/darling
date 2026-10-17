#!/usr/bin/env python3
"""Select the complete source kernel and server with matching PID versions."""
from pathlib import Path
import fcntl, hashlib, json, runpy, shutil
root = Path(__file__).resolve().parent.parent
digest = lambda n: hashlib.sha256((root/n).read_bytes()).hexdigest()
p = runpy.run_path(str(root/'scripts/sandbox-policy-source-profile.py'))['profile']()
report = 'artifacts/pid-generation-kernel-source-build.json'
build = json.loads((root/report).read_text())
folder = root/'runtime/pid-generation-kernel-source'
assert build['full_libsystem_kernel_source_build'] and build['complete_source_files'] == 875
assert digest('runtime/pid-generation-kernel-source/libsystem_kernel.dylib') == build['binary_sha256']
selected = {k:dict(v) for k,v in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for key,item in selected.items():
        if key == 'LINUXCODE_LIBSYSTEM_KERNEL':
            item.update(path='runtime/pid-generation-kernel-source/libsystem_kernel.dylib', sha256=build['binary_sha256'])
        else:
            assert digest(item['path']) == item['sha256']
            target = folder/Path(item['path']).name
            shutil.copy2(root/item['path'], target)
            item['path'] = str(target.relative_to(root))
    for key,name in [('LINUXCODE_LAUNCHD','sbin/launchd'),('LINUXCODE_LIBXPC','usr/lib/system/libxpc.dylib'),('LINUXCODE_LIBSYSTEM_KERNEL','usr/lib/system/libsystem_kernel.dylib'),('LINUXCODE_QUARANTINE','usr/lib/system/libquarantine.dylib'),('LINUXCODE_SANDBOX','usr/lib/system/libsystem_sandbox.dylib'),('LINUXCODE_LIBDYLD','usr/lib/system/libdyld.dylib')]:
        assert digest(str((folder/'darling-root'/name).relative_to(root))) == selected[key]['sha256']
files = ['runtime/darlingserver-source-build/darlingserver/include/darlingserver/rpc.h','runtime/darlingserver-source-build/darlingserver/internal-include/darlingserver/rpc.internal.h']
stage = dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,kernel_build_report=report,kernel_build_report_sha256=digest(report),source_files={n:digest(n) for n in files},PID_version_RPC='process_get_generation',PID_versions_change_on_fork_and_successful_exec=True,full_xcode_build_ready=False)
(root/'artifacts/pid-generation-source-stage.json').write_text(json.dumps(stage,indent=2)+'\n')
print('Selected matching full source kernel and server; six guest components checked')
