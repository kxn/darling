#!/usr/bin/env python3
"""Isolated diagnostic policy, never a replacement for original strict tests."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/unrestricted-sandbox-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/coreservices-unrestricted-diagnostic';build.mkdir(exist_ok=True)
base=root/p['source_unrestricted_sandbox']['variant_root'];variant=build/'darling-root'
relative='System/Library/Sandbox/Profiles/com.apple.coreservicesd.sb'
original=base/relative
source='(version 1)\n(set! *apply-implicit-policy* #f)\n(allow default)\n(allow file-write-setugid job-creation system-kas-info storage-class-map)\n'
selected={key:dict(item) for key,item in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending=build/'darling-root.pending'
    if pending.exists():shutil.rmtree(pending)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True)
    (pending/relative).write_text(source)
    for item in selected.values():
        target=build/Path(item['path']).name;shutil.copy2(root/item['path'],target)
        item.update(path=str(target.relative_to(root)),sha256=digest(target))
    if variant.exists():shutil.rmtree(variant)
    pending.replace(variant)
report=dict(test_only=True,diagnostic_policy_overrides_original=True,
            original_policy=str(original.relative_to(root)),original_policy_sha256=digest(original),
            selected_policy=str((variant/relative).relative_to(root)),selected_policy_sha256=digest(variant/relative),
            diagnostic_SBPL=source,original_coreservicesd_binary_modified=False,
            previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),
            original_strict_policy_application_verified=False,full_xcode_build_ready=False)
(root/'artifacts/coreservices-unrestricted-diagnostic-stage.json').write_text(json.dumps(report,indent=2)+'\n')
print('Staged explicitly permissive CoreServices diagnostic policy; original strict root preserved')
