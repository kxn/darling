#!/usr/bin/env python3
"""Pair the identical test transport with the older unchecked launchd."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/launchd-sandbox-capture-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
baseline=p['source_launchd_sandbox']['previous_source_runtime']['LINUXCODE_LAUNCHD']
assert digest(baseline['path'])==baseline['sha256']
build=root/'runtime/launchd-sandbox-capture-baseline';build.mkdir(exist_ok=True)
base=root/p['test_only_launchd_sandbox_capture']['variant_root'];variant=build/'darling-root'
selected={key:dict(item) for key,item in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    staging=build/'darling-root.pending'
    if staging.exists():shutil.rmtree(staging)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(staging)],check=True)
    shutil.copy2(root/baseline['path'],staging/'sbin/launchd')
    for key,item in selected.items():
        source=root/(baseline['path'] if key=='LINUXCODE_LAUNCHD' else item['path'])
        target=build/source.name;shutil.copy2(source,target)
        item.update(path=str(target.relative_to(root)),sha256=digest(target.relative_to(root)))
    if variant.exists():shutil.rmtree(variant)
    staging.replace(variant)
report=dict(test_only=True,previous_source_runtime=p['source_runtime'],source_runtime=selected,
            variant_root=str(variant.relative_to(root)),baseline_launchd=baseline,
            only_selected_binary_changed='LINUXCODE_LAUNCHD')
(root/'artifacts/launchd-sandbox-capture-baseline-stage.json').write_text(json.dumps(report,indent=2)+'\n')
print('Staged old launchd with the identical test Sandbox library')
