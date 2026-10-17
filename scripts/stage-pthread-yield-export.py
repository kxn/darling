#!/usr/bin/env python3
"""Expose the existing genuine yield wrapper through an isolated libSystem copy."""
from pathlib import Path
import fcntl,hashlib,json,runpy,struct,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=root/'runtime/native-library-stage/libSystem.B.dylib'
old=json.loads((root/'artifacts/dyld-cache-introspection.json').read_text())
assert digest(base)==old['libsystem_stage_sha256']
provider=root/'runtime/native-library-stage/libDarlingFoundationSystem.dylib'
proof=json.loads((root/'artifacts/foundation-libc-compat.json').read_text())
assert digest(provider)==proof['library_sha256'] and proof['selected_libc_api_execution_verified']
source=root/'scripts/foundation-libc-compat.c';assert 'void pthread_yield_np(void) { (void)sched_yield(); }' in source.read_text()
assert '_pthread_yield_np' in subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(provider)],text=True)
data=provider.read_bytes();at=32;dependencies=[]
for _ in range(struct.unpack_from('<I',data,16)[0]):
    cmd,size=struct.unpack_from('<II',data,at)
    if cmd in (0xc,0x80000018,0x8000001f,0x80000023):
        start=at+struct.unpack_from('<I',data,at+8)[0];dependencies.append(data[start:data.index(0,start)].decode())
    if cmd==0x19:
        for j in range(struct.unpack_from('<I',data,at+64)[0]):
            s=at+72+80*j
            assert data[s:s+16].split(b'\0')[0]!=b'__mod_init_func' or not struct.unpack_from('<Q',data,s+40)[0]
    at+=size
assert dependencies==['/usr/lib/libSystem.B.dylib']
api=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))
payload,report=api['add'](base.read_bytes(),'/usr/lib/libDarlingFoundationSystem.dylib',['_pthread_yield_np'])
destination=root/'runtime/pthread-yield-export/libraries/libSystem.B.dylib';destination.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending=destination.with_name('libSystem.B.dylib.pending');pending.write_bytes(payload);pending.replace(destination)
record=dict(installed=False,runtime_execution_verified=False,base=str(base.relative_to(root)),base_sha256=digest(base),
    staged_library=str(destination.relative_to(root)),staged_library_sha256=digest(destination),
    provider=str(provider.relative_to(root)),provider_sha256=digest(provider),
    provider_source=str(source.relative_to(root)),provider_source_sha256=digest(source),
    provider_has_no_initializers=True,provider_dependencies=dependencies,export_changes=report,
    scope='Existing pthread_yield_np delegates to real sched_yield; selected source kernel swtch_pri calls Linux sched_yield. Only this single name is newly reexported by the isolated libSystem copy.',
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/pthread-yield-export-stage.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged one named pthread_yield_np reexport; original libSystem stage and existing code unchanged')
