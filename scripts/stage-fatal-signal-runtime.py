#!/usr/bin/env python3
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
parent=runpy.run_path(str(root/'scripts/icu-data-runtime-profile.py'));digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
name='artifacts/fatal-signal-kernel-build.json';kernel=json.loads((root/name).read_text());binary='runtime/fatal-signal-kernel/libsystem_kernel.dylib';assert digest(binary)==kernel['binary_sha256']
runtimes={}
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for diagnostic in [False,True]:
  p=parent['profile'](diagnostic=diagnostic);label='diagnostic' if diagnostic else 'normal';folder=root/('runtime/fatal-signal-'+label);folder.mkdir(exist_ok=True)
  variant=folder/'darling-root';pending=folder/'darling-root.pending';base=root/p['icu_data_selected_runtime']['variant_root']
  if pending.exists():shutil.rmtree(pending)
  subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True);shutil.copy2(root/binary,pending/'usr/lib/system/libsystem_kernel.dylib')
  selected={k:dict(v) for k,v in p['source_runtime'].items()};selected['LINUXCODE_LIBSYSTEM_KERNEL']=dict(path=binary,sha256=kernel['binary_sha256'])
  for item in selected.values():
   dest=folder/Path(item['path']).name;shutil.copy2(root/item['path'],dest);item.update(path=str(dest.relative_to(root)),sha256=digest(dest))
  if variant.exists():shutil.rmtree(variant)
  pending.replace(variant)
  policy=str((variant/'System/Library/Sandbox/Profiles/com.apple.coreservicesd.sb').relative_to(root))
  runtimes[label]=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),test_only_permissive_coreservices_policy=diagnostic,policy=policy,policy_sha256=digest(policy))
header='vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/include/common/tsd.h'
d=dict(kernel_build=name,kernel_build_sha256=digest(name),source_kernel=kernel,tsd_header=header,tsd_header_sha256=digest(header),runtimes=runtimes,process_policy_supported=False,dataless_file_provider_implemented=False,default_entry_promoted=False,full_xcode_build_ready=False)
(root/'artifacts/fatal-signal-stage.json').write_text(json.dumps(d,indent=2)+'\n')
