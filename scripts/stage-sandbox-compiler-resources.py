#!/usr/bin/env python3
"""Stage unchanged original SBPL resources in a private coherent Darwin root."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/sandbox-compiler-native-profile.py'))['profile']()
build=root/'runtime/sandbox-compiler-resources';build.mkdir(exist_ok=True);variant=build/'darling-root'
base=(root/p['source_runtime']['LINUXCODE_LIBDYLD']['path']).parent/'darling-root';recovery=root/'runtime/recovery/macOS Base System';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();files={};links={}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not variant.exists():subprocess.run(['cp','-a','--reflink=auto',str(base),str(variant)],check=True)
    for relative in ['System/Library/Sandbox/Profiles','usr/share/sandbox']:
        source=recovery/relative;dest=variant/relative;dest.mkdir(parents=True,exist_ok=True)
        subprocess.run(['cp','-a',str(source)+'/.',str(dest)+'/'],check=True)
        for f in source.rglob('*'):
            target=dest/f.relative_to(source)
            if f.is_symlink():assert target.readlink()==f.readlink();links[str(target.relative_to(root))]=str(f.readlink())
            elif f.is_file():assert digest(f)==digest(target);files[str(target.relative_to(root))]=dict(source=str(f.relative_to(root)),sha256=digest(f))
    selected={}
    for key,item in p['source_runtime'].items():
        dest=build/Path(item['path']).name;shutil.copy2(root/item['path'],dest);assert digest(dest)==item['sha256'];selected[key]=dict(path=str(dest.relative_to(root)),sha256=digest(dest))
    assert digest(variant/'usr/lib/system/libsystem_coreservices.dylib')==p['source_coreservices_directories']['library_sha256']
record=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,variant_root=str(variant.relative_to(root)),resource_files=files,resource_symlinks=links,resources_modified=False,source_coreservices_library_sha256=p['source_coreservices_directories']['library_sha256'],sandbox_enforcement_implemented=False,default_entry_promoted=False)
(root/'artifacts/sandbox-compiler-resources-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged',len(files),'original sandbox resource files')
