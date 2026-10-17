#!/usr/bin/env python3
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/iokitd-matching-runtime-profile.py'))['profile']()
kname='artifacts/mount-paths-kernel-build.json';kernel=json.loads((root/kname).read_text());nname='artifacts/notifyd-mounts-build.json';notify=json.loads((root/nname).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
folder=root/'runtime/mount-flags-runtime';folder.mkdir(exist_ok=True);variant=folder/'darling-root';pending=folder/'darling-root.pending'
selected={k:dict(v) for k,v in p['source_runtime'].items()};selected['LINUXCODE_LIBSYSTEM_KERNEL']=dict(path='runtime/mount-paths-kernel/libsystem_kernel.dylib',sha256=kernel['binary_sha256'])
assert digest(selected['LINUXCODE_LIBSYSTEM_KERNEL']['path'])==kernel['binary_sha256'];assert digest(notify['binary'])==notify['binary_sha256']
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if pending.exists():shutil.rmtree(pending)
 subprocess.run(['cp','-a','--reflink=auto',str(root/kernel['variant_root']),str(pending)],check=True)
 shutil.copy2(root/notify['binary'],pending/'usr/sbin/notifyd')
 for item in selected.values():
  dest=folder/Path(item['path']).name;shutil.copy2(root/item['path'],dest);item.update(path=str(dest.relative_to(root)),sha256=digest(dest))
 if variant.exists():shutil.rmtree(variant)
 pending.replace(variant)
header='vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/include/conversion/stat/mount_flags.h'
d=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),kernel_build=kname,kernel_build_sha256=digest(kname),source_kernel=kernel,notifyd_build=nname,notifyd_build_sha256=digest(nname),source_notifyd=notify,mount_flags_header=header,mount_flags_header_sha256=digest(header),notifyd_binary=str((variant/'usr/sbin/notifyd').relative_to(root)),notifyd_binary_sha256=digest(variant/'usr/sbin/notifyd'),default_entry_promoted=False,full_xcode_build_ready=False)
(root/'artifacts/mount-flags-stage.json').write_text(json.dumps(d,indent=2)+'\n');print('Staged mount flags and real namespace notification backend')
