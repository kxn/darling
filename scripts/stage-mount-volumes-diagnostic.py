#!/usr/bin/env python3
"""Keep permissive CoreServices diagnostics separate from the strict candidate."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'));p=m['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
folder=root/'runtime/mount-volumes-diagnostic';folder.mkdir(exist_ok=True)
base=root/p['source_mount_flags']['variant_root'];variant=folder/'darling-root';pending=folder/'darling-root.pending'
relative='System/Library/Sandbox/Profiles/com.apple.coreservicesd.sb'
prior=json.loads((root/'artifacts/coreservices-unrestricted-diagnostic-stage.json').read_text())
policy=root/prior['selected_policy'];assert digest(policy)==prior['selected_policy_sha256']
selected={k:dict(v) for k,v in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if pending.exists():shutil.rmtree(pending)
 subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True)
 shutil.copy2(policy,pending/relative)
 for item in selected.values():
  dest=folder/Path(item['path']).name;shutil.copy2(root/item['path'],dest);item.update(path=str(dest.relative_to(root)),sha256=digest(dest))
 if variant.exists():shutil.rmtree(variant)
 pending.replace(variant)
d=dict(test_only=True,diagnostic_policy_overrides_original=True,previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),original_policy=str((base/relative).relative_to(root)),original_policy_sha256=digest(base/relative),selected_policy=str((variant/relative).relative_to(root)),selected_policy_sha256=digest(variant/relative),full_xcode_build_ready=False)
(root/'artifacts/mount-volumes-diagnostic-stage.json').write_text(json.dumps(d,indent=2)+'\n')
