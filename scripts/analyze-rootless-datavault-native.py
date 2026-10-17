#!/usr/bin/env python3
"""Read the pinned native data-vault implementation and its protection checks."""
from pathlib import Path
from datetime import datetime, timezone
import bisect, hashlib, json, runpy, struct, sys
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'runtime/tools/python-capstone'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
pin = json.loads((root / 'config/cache-image-pins.json').read_text())['sandbox-native']
assert digest('runtime/fullsystem-libraries' + pin['path']) == pin['sha256']
api = runpy.run_path(str(root / 'scripts/dsc-image.py'), init_globals={
    'REFERENCE_CACHE_PATH': root / 'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT': root / 'runtime/fullsystem-libraries'})
image = api['image'](pin['path'])
header = api['read'](image.base, 32)
commands = api['read'](image.base + 32, struct.unpack_from('<I', header, 20)[0])
cursor = 0
for _ in range(struct.unpack_from('<I', header, 16)[0]):
    command, size = struct.unpack_from('<II', commands, cursor)
    if command == 0x26: offset, length = struct.unpack_from('<II', commands, cursor + 8)
    cursor += size
segment = next(s for s in image.segments if s[0] == '__LINKEDIT')
encoded = api['read'](segment[1] + offset - segment[3], length)
cursor = 0; address = image.base; starts = []
while cursor < len(encoded):
    delta, cursor = api['uleb_read'](encoded, cursor)
    if not delta: break
    address += delta; starts.append(address)
machine = Cs(CS_ARCH_X86, CS_MODE_64)
machine.skipdata = True
symbol_by_address = {}
for path in [pin['path'], '/usr/lib/system/libsystem_kernel.dylib', '/usr/lib/system/libsystem_c.dylib']:
    for name, item in api['image'](path).exports.items():
        if item[0] == 'address': symbol_by_address.setdefault(item[1], []).append(name)
functions = []; calls = []
log = 'logs/rootless-datavault-native-analysis.log'
with (root / log).open('w') as stream:
    for name, address in [('rootless_mkdir_datavault', api['resolve'](pin['path'], '_rootless_mkdir_datavault')),
                          ('shared_protected_mkdir', 0x7ff810896b91)]:
        index = bisect.bisect_left(starts, address); assert starts[index] == address
        code = api['read'](address, starts[index + 1] - address)
        instructions = list(machine.disasm(code, address))
        assert sum(i.size for i in instructions) == len(code)
        functions.append(dict(name=name, address=hex(address), size=len(code), sha256=hashlib.sha256(code).hexdigest()))
        print('\nFUNCTION', name, file=stream)
        for item in instructions:
            annotation = ''
            if item.mnemonic == 'call' and item.op_str.startswith('0x'):
                target = int(item.op_str, 16); stub = api['read'](target, 6)
                if stub[:2] == b'\xff\x25':
                    resolved = api['pointer'](target + 6 + struct.unpack_from('<i', stub, 2)[0])
                    annotation = ' / '.join(symbol_by_address.get(resolved, [hex(resolved)]))
                    calls.append(dict(site=hex(item.address), target=annotation))
            print(hex(item.address), item.mnemonic, item.op_str, annotation, file=stream)
text = (root / log).read_text()
assert 'mov ecx, 0x80' in text and 'mov esi, 0x105' in text
assert any('___mac_syscall' in c['target'].split(' / ') for c in calls)
assert any(c['target'] == '_fchflags' for c in calls)
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), provider=pin,
    functions=functions, calls=calls, log=log, log_sha256=digest(log),
    Intel_signature='int rootless_mkdir_datavault(const char *path, mode_t mode, const char *storage_class)',
    data_vault_flag=0x80, mac_policy_call=0x105,
    native_postcondition='Reopen/stat the same directory and check required st_flags bits; preserve original failure paths.',
    protection_backend_implemented=False, native_macos_kernel_execution=False,
    scope='Original Intel user-space ABI and code only. Actual Linux execution/errors are recorded separately; no data-vault protection claim.')
(root / 'artifacts/rootless-datavault-native-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print('Inspected original rootless mkdir, MAC call, fchflags and stat postcondition')
