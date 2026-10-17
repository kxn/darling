#!/usr/bin/env python3
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
name='artifacts/s2c-lifecycle-server-build.json';build=json.loads((root/name).read_text());assert digest(build['server'])==build['server_sha256']
runtimes={}
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for diagnostic in [False,True]:
  label='diagnostic' if diagnostic else 'normal';folder=root/('runtime/s2c-lifecycle-'+label);folder.mkdir(exist_ok=True)
  variant=folder/'darling-root';pending=folder/'darling-root.pending'
  base=root/('runtime/mount-volumes-diagnostic/darling-root' if diagnostic else p['source_mount_flags']['variant_root'])
  if pending.exists():shutil.rmtree(pending)
  subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True)
  selected={k:dict(v) for k,v in p['source_runtime'].items()};selected['LINUXCODE_DARLING_SERVER']=dict(path=build['server'],sha256=build['server_sha256'])
  for item in selected.values():
   dest=folder/Path(item['path']).name;shutil.copy2(root/item['path'],dest);item.update(path=str(dest.relative_to(root)),sha256=digest(dest))
  if variant.exists():shutil.rmtree(variant)
  pending.replace(variant)
  policy=str((variant/'System/Library/Sandbox/Profiles/com.apple.coreservicesd.sb').relative_to(root))
  runtimes[label]=dict(source_runtime=selected,variant_root=str(variant.relative_to(root)),test_only_permissive_coreservices_policy=diagnostic,policy=policy,policy_sha256=digest(policy))
d=dict(previous_source_runtime=p['source_runtime'],server_build=name,server_build_sha256=digest(name),source_server=build,runtimes=runtimes,default_entry_promoted=False,full_xcode_build_ready=False)
(root/'artifacts/s2c-lifecycle-stage.json').write_text(json.dumps(d,indent=2)+'\n')
