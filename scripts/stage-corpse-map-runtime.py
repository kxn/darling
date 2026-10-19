#!/usr/bin/env python3
"""Keep corpse-info error handling in separate normal/diagnostic runtime roots."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
parent=runpy.run_path(str(root/'scripts/fsevents-history-profile.py'))
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
name='artifacts/corpse-map-server-build.json';server=json.loads((root/name).read_text())
assert digest(server['server'])==server['server_sha256']
runtimes={}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for diagnostic in [False,True]:
        p=parent['profile'](diagnostic=diagnostic);label='diagnostic' if diagnostic else 'normal'
        folder=root/('runtime/corpse-map-'+label);folder.mkdir(exist_ok=True)
        base=root/p['swb_swift_logging_selected_runtime']['variant_root']
        pending=folder/'darling-root.pending';variant=folder/'darling-root'
        if pending.exists():shutil.rmtree(pending)
        subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending)],check=True)
        selected={k:dict(v) for k,v in p['source_runtime'].items()}
        selected['LINUXCODE_DARLING_SERVER']={'path':server['server'],'sha256':server['server_sha256']}
        for item in selected.values():
            target=folder/Path(item['path']).name;shutil.copy2(root/item['path'],target)
            item.update(path=str(target.relative_to(root)),sha256=digest(target))
        if variant.exists():shutil.rmtree(variant)
        pending.replace(variant)
        resource=variant/'System/Library/CoreServices/SystemVersion.plist'
        runtimes[label]=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,
            variant_root=str(variant.relative_to(root)),system_version_binding=str(resource.relative_to(root)),
            system_version_binding_sha256=digest(resource),test_only_permissive_coreservices_policy=diagnostic)
(root/'artifacts/corpse-map-stage.json').write_text(json.dumps(dict(server_build=name,server_build_sha256=digest(name),runtimes=runtimes,
    real_corpse_generation_implemented=False,real_corpse_kcdata_mapping_implemented=False,default_entry_promoted=False),indent=2)+'\n')
