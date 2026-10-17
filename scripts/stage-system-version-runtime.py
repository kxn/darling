#!/usr/bin/env python3
"""Stage original reference-userland SystemVersion metadata in isolated roots."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent;parent=runpy.run_path(str(root/'scripts/fatal-signal-runtime-profile.py'));digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resources=['runtime/recovery/macOS Base System/System/Library/CoreServices/SystemVersion.plist'];runtimes={}
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 for diagnostic in [False,True]:
  p=parent['profile'](diagnostic=diagnostic);label='diagnostic' if diagnostic else 'normal';folder=root/('runtime/system-version-'+label);folder.mkdir(exist_ok=True);variant=folder/'darling-root';pending=folder/'darling-root.pending';base=root/p['fatal_signal_selected_runtime']['variant_root']
  if pending.exists():shutil.rmtree(pending)
  subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True)
  (pending/'System/Library/CoreServices').mkdir(parents=True,exist_ok=True)
  staged={}
  for name in resources:
   target=pending/'System/Library/CoreServices'/Path(name).name;shutil.copy2(root/name,target);staged[str((variant/'System/Library/CoreServices'/Path(name).name).relative_to(root))]=digest(name)
  selected={k:dict(v) for k,v in p['source_runtime'].items()}
  for item in selected.values():
   target=folder/Path(item['path']).name;shutil.copy2(root/item['path'],target);item.update(path=str(target.relative_to(root)),sha256=digest(target))
  if variant.exists():shutil.rmtree(variant)
  pending.replace(variant);runtimes[label]=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),resources=staged,test_only_permissive_coreservices_policy=diagnostic)
name='runtime/foundation-native-library-stage/libicucore.A.dylib'
(root/'artifacts/system-version-stage.json').write_text(json.dumps(dict(original_resources={n:digest(n) for n in resources},selected_native_icu=name,selected_native_icu_sha256=digest(name),runtimes=runtimes,default_entry_promoted=False,full_xcode_build_ready=False),indent=2)+'\n')
