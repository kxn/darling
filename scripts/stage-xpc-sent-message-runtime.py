#!/usr/bin/env python3
"""Publish coherent selectors for the complete libxpc send-ownership repair."""
from pathlib import Path
import fcntl,hashlib,json,re,runpy,shutil,subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/diskmanagement-nserror-runtime-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=json.loads((root/'artifacts/xpc-sent-message-source-build.json').read_text());folder=root/'runtime/xpc-sent-message-source'
exports=lambda path:set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True),re.M))
assert exports(root/p['source_runtime']['LINUXCODE_LIBXPC']['path'])<=exports(folder/'libxpc.dylib')
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);selected={}
    for key,item in p['source_runtime'].items():
        filename=Path(item['path']).name
        if key!='LINUXCODE_LIBXPC':shutil.copy2(root/item['path'],folder/filename)
        path=str((folder/filename).relative_to(root));sha=digest(path)
        assert sha==(build['library_sha256'] if key=='LINUXCODE_LIBXPC' else item['sha256'])
        selected[key]=dict(path=path,sha256=sha)
    assert digest(build['variant_root']+'/usr/lib/system/libdispatch.dylib')==p['source_dispatch_workloop']['library_sha256']
    d=dict(previous_source_runtime=p['source_runtime'],source_runtime=selected,build='artifacts/xpc-sent-message-source-build.json',build_sha256=digest('artifacts/xpc-sent-message-source-build.json'))
    (root/'artifacts/xpc-sent-message-runtime-stage.json').write_text(json.dumps(d,indent=2)+'\n')
print('Staged source libxpc with the complete source libdispatch and matching kernel')
