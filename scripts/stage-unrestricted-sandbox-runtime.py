#!/usr/bin/env python3
"""Pair the unrestricted-profile server and source native-compatible XPC hook."""
from pathlib import Path
import fcntl,hashlib,json,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/sandbox-fs-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
server_name='artifacts/unrestricted-sandbox-server-build.json';server=json.loads((root/server_name).read_text())
xpc_name='artifacts/unrestricted-sandbox-libxpc-build.json';xpc=json.loads((root/xpc_name).read_text())
assert server['previous_source_runtime']==p['source_runtime']
folder=root/'runtime/unrestricted-sandbox-runtime';folder.mkdir(exist_ok=True)
selected={key:dict(item) for key,item in p['source_runtime'].items()}
exports=lambda path:set(__import__('re').findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/path)],text=True),__import__('re').M))
library='runtime/unrestricted-sandbox-libxpc/libxpc.dylib';assert digest(library)==xpc['library_sha256']
assert exports(p['source_runtime']['LINUXCODE_LIBXPC']['path'])<=exports(library)
assert '__xpc_runtime_process_has_entered_sandbox' in exports(library)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending=folder/'darling-root.pending';variant=folder/'darling-root'
    if pending.exists():shutil.rmtree(pending)
    subprocess.run(['cp','-a','--reflink=auto',str(root/xpc['variant_root']),str(pending)],check=True)
    for key,item in selected.items():
        source=server['server'] if key=='LINUXCODE_DARLING_SERVER' else library if key=='LINUXCODE_LIBXPC' else item['path']
        target=folder/Path(item['path']).name;shutil.copy2(root/source,target)
        item.update(path=str(target.relative_to(root)),sha256=digest(target))
    if variant.exists():shutil.rmtree(variant)
    pending.replace(variant)
report=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,
            server_build=server_name,server_build_sha256=digest(server_name),
            xpc_build=xpc_name,xpc_build_sha256=digest(xpc_name),variant_root=str(variant.relative_to(root)),
            unrestricted_profile_application_implemented=True,restrictive_profile_application_implemented=False,
            original_profile_resources_modified=False,full_xcode_build_ready=False)
(root/'artifacts/unrestricted-sandbox-runtime-stage.json').write_text(json.dumps(report,indent=2)+'\n')
print('Staged unrestricted-profile support with the original strict resource files unchanged')
