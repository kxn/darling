#!/usr/bin/env python3
"""Keep all seven selectors in a coherent private root after a kernel repair."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/cryptex-native-profile.py'))['profile']()
build=json.loads((root/'artifacts/workqueue-stack-kernel-source-build.json').read_text())
folder=root/'runtime/workqueue-stack-kernel-source'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for key,filename in [('LINUXCODE_DARLING_SERVER','darlingserver'),('LINUXCODE_LIBXPC','libxpc.dylib'),('LINUXCODE_LAUNCHD','launchd')]:
        old=p['source_runtime'][key];assert digest(old['path'])==old['sha256']
        shutil.copy2(root/old['path'],folder/filename)
    selected={key:dict(path=str((folder/Path(v['path']).name).relative_to(root)),sha256=digest(str((folder/Path(v['path']).name).relative_to(root)))) for key,v in p['source_runtime'].items()}
    for key,item in selected.items():
        if key=='LINUXCODE_LIBSYSTEM_KERNEL':assert item['sha256']==build['binary_sha256']
        else:assert item['sha256']==p['source_runtime'][key]['sha256']
    record=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,kernel_build='artifacts/workqueue-stack-kernel-source-build.json',kernel_build_sha256=digest('artifacts/workqueue-stack-kernel-source-build.json'))
    (root/'artifacts/workqueue-stack-runtime-stage.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged seven coherent selectors; only libsystem_kernel has changed')
