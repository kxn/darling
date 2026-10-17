#!/usr/bin/env python3
"""Inspect the actual Intel audit-token container-path wrapper and source ABI."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, runpy, struct, subprocess, sys
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
pin = json.loads((root / 'config/cache-image-pins.json').read_text())['sandbox-native']
assert digest('runtime/fullsystem-libraries' + pin['path']) == pin['sha256']
api = runpy.run_path(str(root / 'scripts/dsc-image.py'), init_globals={
    'REFERENCE_CACHE_PATH': root / 'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT': root / 'runtime/fullsystem-libraries'})
sys.path.insert(0, str(root / 'runtime/tools/python-capstone'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
address = api['resolve'](pin['path'], '_sandbox_container_path_for_audit_token')
code = api['read'](address, 64)
instructions = list(Cs(CS_ARCH_X86, CS_MODE_64).disasm(code, address))
assert sum(i.size for i in instructions) == len(code) and instructions[-1].mnemonic == 'ret'
native = '\n'.join(f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in instructions)
for text in ['mov eax, dword ptr [rbp + 0x24]', 'mov ecx, dword ptr [rbp + 0x2c]',
    'mov qword ptr [rdx + 0x10], rdi', 'mov qword ptr [rdx + 0x18], rsi',
    'mov qword ptr [rdx + 0x20], 1', 'mov esi, 4']:
    assert text in native
policy = next(i for i in instructions if i.mnemonic == 'lea' and i.op_str.startswith('rdi, [rip'))
displacement = int(re.search(r'rip \+ (0x[0-9a-f]+)', policy.op_str)[1], 16)
assert api['read'](policy.address + policy.size + displacement, 8) == b'Sandbox\0'
call = next(i for i in instructions if i.mnemonic == 'call')
stub_address = int(call.op_str, 16); stub = api['read'](stub_address, 6)
assert stub[:2] == b'\xff\x25'
assert api['pointer'](stub_address + 6 + struct.unpack_from('<i', stub, 2)[0]) == api['resolve']('/usr/lib/system/libsystem_kernel.dylib', '___mac_syscall')
stage = json.loads((root / 'artifacts/sandbox-container-source-stage.json').read_text())
assert digest(stage['helper']) == stage['helper_sha256']
compiled = subprocess.check_output(['llvm-objdump-19', '--disassemble-symbols=_sandbox_container_path_for_audit_token', str(root / stage['helper'])], text=True)
for text in ['movl\t0x24(%rbp)', 'movl\t0x2c(%rbp)', 'movl\t$0x4, %esi']: assert text in compiled
log = 'logs/sandbox-container-native-abi.log'
(root / log).write_text('ORIGINAL CACHE WRAPPER\n' + native + '\n\nCOMPILED SOURCE WRAPPER\n' + compiled)
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), provider=pin,
    native_address=hex(address), native_code_sha256=hashlib.sha256(code).hexdigest(),
    compiled_helper_sha256=stage['helper_sha256'], source_sha256=digest(stage['source']),
    Intel_signature='int sandbox_container_path_for_audit_token(audit_token_t by_value, char *, size_t)',
    audit_token_size=32, pid_stack_offset_from_rbp=0x24, pid_version_stack_offset_from_rbp=0x2c,
    mac_policy='Sandbox', operation=4, slots=['zero-extended PID', 'zero-extended PID version', 'output pointer', 'size_t capacity', '1 (audit identity mode)'],
    log=log, log_sha256=digest(log),
    authority_enforcement_verified=False, positive_container_query_verified=False,
    scope='Native and compiled Intel ABI only; absent-policy differential tests do not prove authorization or positive path queries.')
(root / 'artifacts/sandbox-container-native-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print('Verified original by-value token stack/register ABI and five-slot Sandbox operation 4')
