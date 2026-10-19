#!/usr/bin/env python3
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
parent=runpy.run_path(str(root/'scripts/global-fsevents-runtime-profile.py'))
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
name='artifacts/vchroot-links-kernel-build.json';kernel=json.loads((root/name).read_text());binary='runtime/vchroot-links-kernel/libsystem_kernel.dylib';assert digest(binary)==kernel['binary_sha256']
runtimes={}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for diagnostic in [False,True]:
        p=parent['profile'](diagnostic=diagnostic);label='diagnostic' if diagnostic else 'normal';folder=root/('runtime/vchroot-links-'+label);folder.mkdir(exist_ok=True)
        variant=folder/'darling-root';pending=folder/'darling-root.pending';base=root/p['global_fsevents_selected_runtime']['variant_root']
        if pending.exists():shutil.rmtree(pending)
        subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True);shutil.copy2(root/binary,pending/'usr/lib/system/libsystem_kernel.dylib')
        selected={k:dict(v) for k,v in p['source_runtime'].items()};selected['LINUXCODE_LIBSYSTEM_KERNEL']={'path':binary,'sha256':digest(binary)}
        for item in selected.values():
            target=folder/Path(item['path']).name;shutil.copy2(root/item['path'],target);item.update(path=str(target.relative_to(root)),sha256=digest(target))
        if variant.exists():shutil.rmtree(variant)
        pending.replace(variant);binding=str((variant/'System/Library/CoreServices/SystemVersion.plist').relative_to(root))
        runtimes[label]=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),system_version_binding=binding,system_version_binding_sha256=digest(binding),test_only_permissive_coreservices_policy=diagnostic)
(root/'artifacts/vchroot-links-stage.json').write_text(json.dumps(dict(kernel_build=name,kernel_build_sha256=digest(name),runtimes=runtimes,default_entry_promoted=False,full_xcode_build_ready=False),indent=2)+'\n')
