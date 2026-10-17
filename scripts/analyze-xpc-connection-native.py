#!/usr/bin/env python3
"""Read-only native invalidation-reason ABI inspection; not native XPC execution."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
config=json.loads((root/'config/xpc-rich-error.json').read_text())
native=config['native_reference'];provider=root/'runtime/fullsystem-libraries'/native['path'].lstrip('/')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(provider)==native['sha256']
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
header=sdk/'usr/include/xpc/connection.h'
assert digest(header)==config['sdk_files']['usr/include/xpc/connection.h']
data=header.read_text()
assert 'xpc_connection_copy_invalidation_reason(xpc_connection_t connection)' in data
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
address=d['resolve'](native['path'],'_xpc_connection_copy_invalidation_reason')
assert address==0x7ff802b7dbbd
code=d['read'](address,54);instructions=list(Cs(CS_ARCH_X86,CS_MODE_64).disasm(code,address))
assert sum(i.size for i in instructions)==len(code)
log=root/'logs/xpc-connection-native-invalidation-abi.log'
log.write_text(''.join(f'{i.address:#x} {i.mnemonic} {i.op_str}\n' for i in instructions))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=native['path'],provider_sha256=native['sha256'],
    symbol='_xpc_connection_copy_invalidation_reason',address=hex(address),length=len(code),code_sha256=hashlib.sha256(code).hexdigest(),
    sdk_header=str(header.relative_to(root)),sdk_header_sha256=digest(header),
    sdk_return_contract='NULL before invalidation, otherwise a caller-owned description string.',
    native_private_reason_state_offset=96,darling_native_private_layout_reused=False,
    source_state='Atomic Darling is_cancelled, initialized false and published before actual DISPATCH_MACH_CANCELED handler callback.',
    source_reason='Connection cancelled by the Darling XPC backend',
    adapter_migration='Resolve only public SPIs owned by xpc_connection_cancel implementation; retain original packaged UUID/code/layout guard for private fallback.',
    native_macos_connection_execution_compared=False,native_peer_verification_implemented=False,
    log=str(log.relative_to(root)),log_sha256=digest(log),execution_report='artifacts/xpc-connection-source.json',
    scope='Native user-space ABI and SDK contract inspection. Actual Darling cancellation, concurrency, ownership, delegation and guard tests are separate; no full modern reason-code/peer-signature semantics claim.')
(root/'artifacts/xpc-connection-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Inspected native XPC invalidation ABI:',log)
