#!/usr/bin/env python3
"""Extract bounded, relocation-free Intel reference code for differential tests."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
build=root/'runtime/layer-log-reference';build.mkdir(parents=True,exist_ok=True)
records=[];assembly=[];disassembly=[]
for provider,symbol,length,label in [
 ('/System/Library/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics','_CGFloatIsValid',32,'_reference_CGFloatIsValid'),
 ('/usr/lib/system/libsystem_trace.dylib','_os_log_compare_enablement',91,'_reference_os_log_compare_enablement')]:
 address=m['resolve'](provider,symbol);code=m['read'](address,length)
 instructions=list(cs.disasm(code,address));assert sum(i.size for i in instructions)==length
 outside=[]
 for i in instructions:
  for operand in i.operands:
   assert not(operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP)
  if i.mnemonic=='call' or i.mnemonic.startswith('j'):
   assert i.operands[0].type==X86_OP_IMM
   target=i.operands[0].imm
   if not address<=target<address+length:outside.append(target)
 # The compare helper's two invalid-enum branches point to the immediately
 # following native assertion path. Only defined log types enter this oracle.
 if symbol=='_os_log_compare_enablement':assert outside==[address+length,address+length]
 else:assert not outside and instructions[-1].mnemonic=='ret'
 assembly.extend(['.text',f'.globl {label}',label+':','.byte '+','.join(hex(b) for b in code)])
 if outside:assembly.append('ud2 // invalid enums are outside the native reference test domain')
 disassembly.append(symbol+'\n'+'\n'.join(f'{i.address:#x} {i.mnemonic} {i.op_str}' for i in instructions))
 records.append(dict(provider=provider,provider_sha256=hashlib.sha256((root/'runtime/fullsystem-libraries'/provider.lstrip('/')).read_bytes()).hexdigest(),
  symbol=symbol,address=hex(address),length=length,bytes_sha256=hashlib.sha256(code).hexdigest(),reference_label=label,external_branches=outside))
cg='/System/Library/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics'
for symbol,length in [('_CGContextGetBaseCTM',140),('_CGContextSetBaseCTM',140),('_CGContextSaveGState',160)]:
 address=m['resolve'](cg,symbol);code=m['read'](address,length)
 disassembly.append(symbol+'\n'+'\n'.join(f'{i.address:#x} {i.mnemonic} {i.op_str}' for i in cs.disasm(code,address)))
 records.append(dict(provider=cg,symbol=symbol,address=hex(address),length=length,bytes_sha256=hashlib.sha256(code).hexdigest(),execution_reference=False))
source='runtime/layer-log-reference/reference.S';log='logs/layer-log-native-abi.log'
(root/source).write_text('\n'.join(assembly)+'\n');(root/log).write_text('\n\n'.join(disassembly)+'\n')
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),functions=records,reference_source=source,reference_source_sha256=digest(source),log=log,log_sha256=digest(log),
 scope='Exact original Intel scalar instructions; compare valid-enum domain only. Context functions are inspected for ABI and separate render-state storage, not executed against Onyx objects.')
(root/'artifacts/layer-log-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Extracted original CGFloat and valid-type log ordering references; recorded context ABI')
