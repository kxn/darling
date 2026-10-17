#!/usr/bin/env python3
"""Bounded, read-only Intel service API/protocol and DVT call-site inspection."""
from pathlib import Path
from datetime import datetime, timezone
import bisect, hashlib, json, re, runpy, struct, subprocess, sys
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root/'runtime/tools/python-capstone'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP
d = runpy.run_path(str(root/'scripts/dsc-image.py'), init_globals={
    'REFERENCE_CACHE_PATH': root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT': root/'runtime/fullsystem-libraries'})
provider = '/usr/lib/system/libxpc.dylib'
image = d['image'](provider)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native = root/'runtime/fullsystem-libraries'/provider.lstrip('/')
assert digest(native) == '9fd39e678c12bf9d82f8245459ab15f15acd3f4e8e0399f6d986838661bd43dc'
header = d['read'](image.base, 32)
cursor = image.base + 32
for _ in range(struct.unpack_from('<I', header, 16)[0]):
    command, size = struct.unpack('<II', d['read'](cursor, 8))
    raw = d['read'](cursor, size)
    if command == 0x19 and raw[8:24].split(b'\0')[0] == b'__LINKEDIT':
        linkaddr, _, linkoff = struct.unpack_from('<QQQ', raw, 24)
    if command == 0x26: startoff, startsize = struct.unpack_from('<II', raw, 8)
    cursor += size
starts = []; address = image.base; value = shift = 0
for byte in d['read'](linkaddr + startoff - linkoff, startsize):
    value |= (byte & 127) << shift
    if byte < 128:
        if not value: break
        address += value; starts.append(address); value = shift = 0
    else: shift += 7
machine = Cs(CS_ARCH_X86, CS_MODE_64); machine.detail = True; machine.skipdata = True
symbols = ['_xpc_service_create', '_xpc_service_create_from_specifier',
    '_xpc_service_get_rendezvous_token', '_xpc_service_kickstart',
    '_xpc_service_kickstart_with_flags', '_xpc_service_attach',
    '_xpc_service_attach_with_flags', '_xpc_service_set_attach_handler',
    '__xpc_service_routine', '__xpc_service_last_xref_cancel']
selected = {d['resolve'](provider, s): s for s in symbols}
selected.update({0x7ff802b8ed4d: 'common_create', 0x7ff802b8ee97: 'specifier_parse',
    0x7ff802b8f356: 'service_request', 0x7ff802b8f5e1: 'attach_notification'})
log = []; functions = []
for address, name in sorted(selected.items()):
    index = bisect.bisect_right(starts, address)-1
    assert starts[index] == address
    end = starts[index+1]; code = d['read'](address, end-address)
    log.append(f'\nFUNCTION {name} {address:#x}..{end:#x}\n')
    for i in machine.disasm(code, address): log.append(f'{i.address:#x} {i.mnemonic} {i.op_str}\n')
    functions.append(dict(name=name, address=hex(address), end=hex(end),
        sha256=hashlib.sha256(code).hexdigest()))
path = root/'logs/xpc-service-native-abi.log'; path.write_text(''.join(log))
report = dict(checked_at=datetime.now(timezone.utc).isoformat(),
    provider=provider, provider_sha256=digest(native), functions=functions,
    native_execution=False, native_private_layout_reused=False,
    protocol=dict(subsystem=2, kickstart=702, attach=703, register_handler=704, cancel=706,
        selector_keys=['type','handle','name','unidomain'],
        kickstart_keys=['suspended','kill','unthrottle'],
        flags=dict(suspended=1, kill=2), return_type='int error',
        create_kind_to_domain={'1':5,'other':6},
        specifier_domains=dict(system=1,user=2,login=3,pid=5,gui=8,loginwindow=2)),
    log=str(path.relative_to(root)), log_sha256=digest(path))
(root/'artifacts/xpc-service-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Native service ABI inspected:', len(functions), 'bounded functions')
