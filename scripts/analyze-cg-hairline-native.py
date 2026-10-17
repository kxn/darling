#!/usr/bin/env python3
"""Verify the original Intel hairline sentinel and actual scalar comparisons."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,struct,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/System/Library/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics'
symbol='_kCGLineWidthHairline';address=d['resolve'](provider,symbol)
payload=d['read'](address,8);assert payload.hex()=='00e522263c5f43c3'
value=struct.unpack('<d',payload)[0];assert value.hex()=='-0x1.35f3c2622e500p+53'
consumer='/System/Library/Frameworks/QuartzCore.framework/Versions/A/QuartzCore'
image=d['image'](consumer);machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True
references=[];lines=[]
for offset in [0xc6fd1,0x198ffb,0x3043e3]:
    pc=image.base+offset;code=d['read'](pc,40);instructions=list(machine.disasm(code,pc))
    first=instructions[0];assert first.mnemonic=='mov'
    operand=first.operands[1];assert operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP
    cell=first.address+first.size+operand.mem.disp;assert d['pointer'](cell)==address
    assert any(i.mnemonic=='ucomisd' for i in instructions[1:3])
    references.append(dict(address=hex(pc),pointer_cell=hex(cell),code_sha256=hashlib.sha256(code).hexdigest(),length=len(code)))
    lines.append(f'\nREFERENCE {pc:#x} -> {address:#x}\n')
    for i in instructions:lines.append(f'{i.address:#x} {i.mnemonic} {i.op_str}\n')
log=root/'logs/cg-hairline-native-abi.log';log.write_text(''.join(lines))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,
    provider=provider,provider_sha256=hashlib.sha256((root/'runtime/fullsystem-libraries'/provider.lstrip('/')).read_bytes()).hexdigest(),
    consumer=consumer,consumer_sha256=hashlib.sha256((root/'runtime/fullsystem-libraries'/consumer.lstrip('/')).read_bytes()).hexdigest(),
    symbol=symbol,address=hex(address),abi='x86_64 8-byte double scalar storage, not a CFString or pointer',
    bytes=payload.hex(),value=value,hex_float=value.hex(),references=references,
    log=str(log.relative_to(root)),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
    drawing_operations_implemented=False)
(root/'artifacts/cg-hairline-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified native hairline double sentinel and three real QuartzCore scalar comparisons')
