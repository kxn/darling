#!/usr/bin/env python3
"""Make the complete original Intel OSLog framework visible to build services."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent;parent=runpy.run_path(str(root/'scripts/system-version-runtime-profile.py'));digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
name='runtime/rebuilt-oslog-build-service-native/reconstruction.json';image=json.loads((root/name).read_text());source='runtime/rebuilt-oslog-build-service-native/OSLog';assert digest(source)==image['staged_image_sha256'] and not image['backend_call_overrides'] and not image['redirected_imports'];runtimes={}
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for diagnostic in [False,True]:
  p=parent['profile'](diagnostic=diagnostic);label='diagnostic' if diagnostic else 'normal';folder=root/('runtime/swb-logging-'+label);folder.mkdir(exist_ok=True);variant=folder/'darling-root';pending=folder/'darling-root.pending';base=root/p['system_version_selected_runtime']['variant_root']
  if pending.exists():shutil.rmtree(pending)
  subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True)
  framework=pending/'System/Library/Frameworks/OSLog.framework';version=framework/'Versions/A';version.mkdir(parents=True,exist_ok=True);shutil.copy2(root/source,version/'OSLog')
  resources=root/'runtime/recovery/macOS Base System/System/Library/Frameworks/OSLog.framework/Versions/A/Resources'
  if resources.exists():shutil.copytree(resources,version/'Resources',dirs_exist_ok=True)
  for path,target in [(framework/'Versions/Current','A'),(framework/'OSLog','Versions/Current/OSLog'),(framework/'Resources','Versions/Current/Resources')]:
   if not path.exists() and not path.is_symlink():path.symlink_to(target)
  selected={k:dict(v) for k,v in p['source_runtime'].items()}
  for item in selected.values():
   target=folder/Path(item['path']).name;shutil.copy2(root/item['path'],target);item.update(path=str(target.relative_to(root)),sha256=digest(target))
  if variant.exists():shutil.rmtree(variant)
  pending.replace(variant);files={str(n.relative_to(root)):digest(str(n.relative_to(root))) for n in (variant/'System/Library/Frameworks/OSLog.framework').rglob('*') if n.is_file() and not n.is_symlink()};runtimes[label]=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),files=files,test_only_permissive_coreservices_policy=diagnostic)
(root/'artifacts/swb-logging-stage.json').write_text(json.dumps(dict(reconstruction=name,reconstruction_sha256=digest(name),source=source,source_sha256=digest(source),native_image=image,runtimes=runtimes,original_OSLog_backend_calls_preserved=True,logd_service_implemented=False,full_xcode_build_ready=False),indent=2)+'\n')
