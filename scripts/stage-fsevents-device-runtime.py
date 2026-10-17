#!/usr/bin/env python3
"""Stage real device transport; keep the permissive policy diagnostic separate."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/unrestricted-sandbox-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
sn='artifacts/fsevents-device-server-build.json';kn='artifacts/fsevents-device-kernel-build.json'
server=json.loads((root/sn).read_text());kernel=json.loads((root/kn).read_text())
assert server['previous_source_runtime']==p['source_runtime'] and kernel['complete_source_files']==879
assert not kernel.get('test_only_source_overrides')
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for diagnostic in [False,True]:
        folder=root/('runtime/fsevents-device-'+('diagnostic' if diagnostic else 'runtime'));folder.mkdir(exist_ok=True)
        pending=folder/'darling-root.pending';variant=folder/'darling-root'
        if pending.exists():shutil.rmtree(pending)
        subprocess.run(['cp','-a','--reflink=auto',str(root/kernel['variant_root']),str(pending)],check=True)
        selected={key:dict(item) for key,item in p['source_runtime'].items()}
        for key,item in selected.items():
            source=server['server'] if key=='LINUXCODE_DARLING_SERVER' else str(Path(kernel['variant_root']).parent/'libsystem_kernel.dylib') if key=='LINUXCODE_LIBSYSTEM_KERNEL' else item['path']
            target=folder/Path(item['path']).name;shutil.copy2(root/source,target)
            item.update(path=str(target.relative_to(root)),sha256=digest(target))
        policy=None
        if diagnostic:
            old=json.loads((root/'artifacts/coreservices-unrestricted-diagnostic-stage.json').read_text())
            relative='System/Library/Sandbox/Profiles/com.apple.coreservicesd.sb'
            policy=dict(original_policy=str((root/kernel['variant_root']/relative).relative_to(root)),
                        original_policy_sha256=digest(root/kernel['variant_root']/relative),
                        selected_policy=str((variant/relative).relative_to(root)),
                        selected_policy_sha256=old['selected_policy_sha256'],diagnostic_SBPL=old['diagnostic_SBPL'],
                        test_only=True,diagnostic_policy_overrides_original=True)
            (pending/relative).write_text(old['diagnostic_SBPL'])
        if variant.exists():shutil.rmtree(variant)
        pending.replace(variant)
        report=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),
                    server_build=sn,server_build_sha256=digest(sn),kernel_build=kn,kernel_build_sha256=digest(kn),
                    diagnostic_policy=policy,test_only=diagnostic,raw_device_integration_verified=False,
                    event_selection=['delete','rename'],originating_pid_available=False,
                    watch_scope='virtual-root-tree; external SystemRoot aliases are not covered',full_xcode_build_ready=False)
        (root/('artifacts/fsevents-device-'+('diagnostic' if diagnostic else 'runtime')+'-stage.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Staged private device runtime and a separately identified permissive-policy diagnostic')
