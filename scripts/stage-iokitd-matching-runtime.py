#!/usr/bin/env python3
"""Stage the new source daemon under the original boot job in a private root."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/iokitd-power-runtime-profile.py'))['profile']()
name='artifacts/iokitd-matching-build.json';build=json.loads((root/name).read_text())
notify_build_name='artifacts/notifyd-matching-build.json';notify_build=json.loads((root/notify_build_name).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
assert digest(build['binary'])==build['binary_sha256'] and build['full_iokitd_source_build']
assert digest(notify_build['binary'])==notify_build['binary_sha256'] and notify_build['full_notifyd_source_build']
folder=root/'runtime/iokitd-matching-runtime';folder.mkdir(exist_ok=True)
variant=folder/'darling-root';pending=folder/'darling-root.pending'
selected={k:dict(v) for k,v in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if pending.exists():shutil.rmtree(pending)
    subprocess.run(['cp','-a','--reflink=auto',str(root/p['source_iokitd_power']['variant_root']),str(pending)],check=True)
    shutil.copy2(root/build['binary'],pending/'usr/sbin/iokitd')
    shutil.copy2(root/notify_build['binary'],pending/'usr/sbin/notifyd')
    notify_job='vendor/darling/src/external/libnotify/notifyd/com.apple.notifyd.plist'
    shutil.copy2(root/notify_job,pending/'System/Library/LaunchDaemons/com.apple.notifyd.plist')
    (pending/'System/Library/LaunchDaemons/com.apple.notifyd.plist').chmod(0o644)
    for item in selected.values():
        dest=folder/Path(item['path']).name;shutil.copy2(root/item['path'],dest);item.update(path=str(dest.relative_to(root)),sha256=digest(dest))
    if variant.exists():shutil.rmtree(variant)
    pending.replace(variant)
d=dict(source_notifyd_build=notify_build_name,source_notifyd_build_sha256=digest(notify_build_name),source_notifyd=notify_build,notifyd_job_source=notify_job,notifyd_job_source_sha256=digest(notify_job),notifyd_binary=str((variant/'usr/sbin/notifyd').relative_to(root)),notifyd_binary_sha256=digest(variant/'usr/sbin/notifyd'),notifyd_job=str((variant/'System/Library/LaunchDaemons/com.apple.notifyd.plist').relative_to(root)),notifyd_job_sha256=digest(variant/'System/Library/LaunchDaemons/com.apple.notifyd.plist'),source_build=name,source_build_sha256=digest(name),source_iokitd=build,previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),original_launchd_job_preserved=True,original_job_sha256=digest(variant/'System/Library/LaunchDaemons/org.darlinghq.iokitd.plist'),test_only_fixture_services_in_production=False,runtime_execution_verified=False,default_entry_promoted=False,full_xcode_build_ready=False)
(root/'artifacts/iokitd-matching-stage.json').write_text(json.dumps(d,indent=2)+'\n');print('Staged complete matching iokitd with original job')
