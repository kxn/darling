#!/usr/bin/env python3
"""Verify the nounlink wrapper uses the previously inspected protected mkdir body."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, struct, sys
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
old = json.loads((root / 'artifacts/rootless-datavault-native-analysis.json').read_text())
assert digest(old['log']) == old['log_sha256']
assert digest('runtime/fullsystem-libraries' + old['provider']['path']) == old['provider']['sha256']
api = runpy.run_path(str(root / 'scripts/dsc-image.py'), init_globals={
    'REFERENCE_CACHE_PATH': root / 'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT': root / 'runtime/fullsystem-libraries'})
address = api['resolve'](old['provider']['path'], '_rootless_mkdir_nounlink')
code = api['read'](address, 15)
assert code[:10] == bytes.fromhex('554889e5b9000010005d') and code[10] == 0xe9
target = address + 15 + struct.unpack_from('<i', code, 11)[0]
shared = next(f for f in old['functions'] if f['name'] == 'shared_protected_mkdir')
assert target == int(shared['address'], 16)
assert hashlib.sha256(api['read'](target, shared['size'])).hexdigest() == shared['sha256']
reference = root / 'vendor/darling/src/external/copyfile/copyfile_test/stat_test.c'
assert 'typedef int (*special_mkdir_func)(const char *, mode_t, const char *);' in reference.read_text()
sys.path.insert(0, str(root / 'runtime/tools/python-capstone'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
log = 'logs/rootless-nounlink-native-analysis.log'
(root / log).write_text('\n'.join(f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in Cs(CS_ARCH_X86, CS_MODE_64).disasm(code, address)) + '\n')
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), provider=old['provider'],
    address=hex(address), wrapper_sha256=hashlib.sha256(code).hexdigest(), flag=0x100000,
    original_shared_protected_mkdir=shared, original_datavault_analysis_sha256=digest('artifacts/rootless-datavault-native-analysis.json'),
    Intel_signature='int rootless_mkdir_nounlink(const char *, mode_t, const char *)',
    prototype_reference=str(reference.relative_to(root)), prototype_reference_sha256=digest(str(reference.relative_to(root))),
    log=log, log_sha256=digest(log), protection_implemented=False,
    scope='Original Intel wrapper/prototype only; actual syscall errors are recorded by the differential execution test.')
(root / 'artifacts/rootless-nounlink-native-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print('Verified original nounlink flag, three-argument ABI and shared protection implementation')
