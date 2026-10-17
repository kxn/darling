#!/usr/bin/env python3
"""Relocate the original Intel enumeration and file checks as a test-only oracle."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/usr/lib/system/libdyld.dylib';entry=m['resolve'](provider,'_macho_for_each_runnable_arch_name');assert entry==0x7ff802a96b0c
cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
functions=[('reference_for_each_runnable_arch_name',entry,182),('reference_has_file',0x7ff802a96bc2,147)]
calls={0x7ff802a96bc2:'_reference_has_file',0x7ff802aa6e0c:'_runnable_fixture_stat',0x7ff802aa6e2a:'_strlcpy',0x7ff802aa6e24:'_strlcat',0x7ff802aa6c4a:'___stack_chk_fail'}
assembly=['.text'];strings={};records=[];log=[]
for name,a,n in functions:
 instructions=list(cs.disasm(m['read'](a,n),a));assert sum(i.size for i in instructions)==n
 assembly+=['.p2align 4','.globl _'+name,'_'+name+':'];relocations=[]
 for i in instructions:
  log.append(f'{i.address:#x} {i.mnemonic} {i.op_str}')
  rip=[o for o in i.operands if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP]
  if rip:
   target=i.address+i.size+rip[0].mem.disp;assert i.size==7
   if i.mnemonic=='lea':
    raw=m['read'](target,160).split(b'\0')[0];label='Lstring_'+str(len(strings));strings[label]=raw;reg=i.reg_name(i.operands[0].reg);assembly.append(f'leaq {label}(%rip), %{reg}');relocations.append(dict(address=hex(i.address),kind='cstring',value=raw.decode()))
   else:
    assert i.mnemonic=='mov' and target==0x7ff840053748
    reg=i.reg_name(i.operands[0].reg);assembly.append(f'movq ___stack_chk_guard@GOTPCREL(%rip), %{reg}');relocations.append(dict(address=hex(i.address),kind='stack_guard'))
  elif i.mnemonic=='call' and i.operands[0].type==X86_OP_IMM:
   assert i.size==5;target=calls[i.operands[0].imm];assembly.append('callq '+target);relocations.append(dict(address=hex(i.address),kind='call',target=target))
  else:
   if i.mnemonic.startswith('j'):assert a<=i.operands[0].imm<a+n
   assembly.append('.byte '+','.join(hex(v) for v in i.bytes))
 assembly+=['_'+name+'_end:'];records.append(dict(name=name,address=hex(a),length=n,sha256=hashlib.sha256(m['read'](a,n)).hexdigest(),relocations=relocations))
assembly+=['.section __TEXT,__cstring,cstring_literals']
for label,value in strings.items():assembly.extend([label+':','.byte '+','.join(str(x) for x in value+b'\0')])
build=root/'runtime/runnable-archs-reference';build.mkdir(parents=True,exist_ok=True)
source='runtime/runnable-archs-reference/reference.S';out='logs/runnable-archs-native-abi.log';(root/source).write_text('\n'.join(assembly)+'\n');(root/out).write_text('\n'.join(log)+'\n')
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=digest('runtime/fullsystem-libraries'+provider),functions=records,reference_source=source,reference_source_sha256=digest(source),log=out,log_sha256=digest(out),reference_installed=False,scope='Original enumeration and hasFile machine instructions with internal branches preserved. Only external stat/cstring/guard relocations adapted; stat receives the same real temporary filesystem for both test implementations. No CPU grading or ARM execution is inferred from cache names.')
(root/'artifacts/runnable-archs-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print('Recovered original 182-byte enumeration and 147-byte cache-existence checks')
