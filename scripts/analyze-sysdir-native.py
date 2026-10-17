#!/usr/bin/env python3
"""Verify the original paired public/private Intel directory enumeration wrappers."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, sys
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
pin=json.loads((root/'config/cache-image-pins.json').read_text())['dirhelper-native']
assert digest('runtime/fullsystem-libraries'+pin['path'])==pin['sha256']
api=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
records=[];text=[];targets=[]
for name,size in [('_sysdir_start_search_path_enumeration',15),('_sysdir_start_search_path_enumeration_private',12),('_sysdir_get_next_search_path_enumeration',10)]:
    address=api['resolve'](pin['path'],name);code=api['read'](address,size)
    instructions=list(Cs(CS_ARCH_X86,CS_MODE_64).disasm(code,address))
    assert sum(i.size for i in instructions)==size and instructions[-1].mnemonic=='jmp'
    target=int(instructions[-1].op_str,16);targets.append(target)
    records.append(dict(name=name,address=hex(address),sha256=hashlib.sha256(code).hexdigest(),size=size,target=hex(target)))
    text.append(name+'\n'+'\n'.join(f'{i.address:x}: {i.mnemonic} {i.op_str}' for i in instructions))
assert targets[0]==targets[1]
assert 'mov edx, 0x1ff0' in text[0] and 'xor edx, edx' in text[1]
next_body='\n'.join(i.mnemonic+' '+i.op_str for i in Cs(CS_ARCH_X86,CS_MODE_64).disasm(api['read'](targets[2],64),targets[2]))
assert 'mov r14d, edi' in next_body
log='logs/sysdir-native-abi.log';(root/log).write_text('\n\n'.join(text)+'\nNEXT BODY\n'+next_body+'\n')
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=pin,functions=records,
    state_width=32,public_excluded_domain_bits=0x1ff0,private_excluded_domain_bits=0,
    common_starter_body=True,log=log,log_sha256=digest(log),
    scope='Original wrapper and state argument ABI only; paired-path execution is validated separately.')
(root/'artifacts/sysdir-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified native 32-bit state, shared starter body and distinct public/private filters')
