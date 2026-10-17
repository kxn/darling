#!/usr/bin/env python3
"""Read-only ABI inspection of the pinned Intel libquarantine implementation."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
pins=json.loads((root/'config/cache-image-pins.json').read_text())['quarantine-native']
provider=root/'runtime/fullsystem-libraries/usr/lib/system/libquarantine.dylib'
digest=lambda b:hashlib.sha256(b).hexdigest()
assert digest(provider.read_bytes())==pins['sha256']
cache=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
image=cache['image'](pins['path'])
functions=[]
machine=Cs(CS_ARCH_X86,CS_MODE_64)
log=root/'logs/responsibility-native-abi.log'
with log.open('w') as stream:
    for symbol,address,length in [
        ('_responsibility_spawnattrs_setdisclaim',0x7ff811fcc44b,93),
        ('_responsibility_spawnattrs_getdisclaim',0x7ff811fcd22d,82),
        ('_qtn_spawnattrs_alloc',0x7ff811fcd153,218),
        ('_responsibility_get_pid_responsible_for_pid',0x7ff811fcb7d0,54),
        ('_responsibility_get_uniqueid_responsible_for_pid',0x7ff811fcc607,55),
        ('internal_query',0x7ff811fcb806,107)]:
        if symbol in image.exports:assert cache['resolve'](pins['path'],symbol)==address
        code=cache['read'](address,length)
        instructions=list(machine.disasm(code,address))
        assert sum(i.size for i in instructions)==length
        functions.append(dict(symbol=symbol,address=hex(address),length=length,sha256=digest(code),
                              exported=symbol in image.exports))
        print('\nFUNCTION',symbol,hex(address),file=stream)
        for i in instructions:print(hex(i.address),i.mnemonic,i.op_str,file=stream)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=pins['path'],provider_sha256=pins['sha256'],
    read_only=True,functions=functions,log=str(log.relative_to(root)),log_sha256=digest(log.read_bytes()),
    spawn_record=dict(size=24,version_offset=0,size_offset=4,flags_offset=8,disclaim_bit=0,
                      allocation='one borrowed 24-byte pthread-specific buffer, reset when attaching a new policy entry'),
    query=dict(policy='Quarantine',opcode=180,arguments='five uint64 slots: PID, PID output pointer, unique-ID output pointer, reserved zero x2'),
    source_references=['vendor/darling/src/external/xnu/security/mac_base.c',
                       'https://github.com/llvm/llvm-project/blob/main/lldb/source/Host/macosx/objcxx/PosixSpawnResponsible.h'],
    execution_report='artifacts/responsibility-source.json',native_macos_kernel_execution=False,
    scope='Native user-space record and query ABI plus actual native/source attribute differential; no native macOS kernel attribution comparison or TCC enforcement claim.')
(root/'artifacts/responsibility-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Inspected pinned native responsibility ABI:',log)
