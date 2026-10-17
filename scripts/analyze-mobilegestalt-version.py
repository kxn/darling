#!/usr/bin/env python3
"""Recover original Intel version callbacks as a bounded differential oracle.

Original control flow and register operations are retained. External calls and
constant-address relocations target real CF functions and controlled dictionary
inputs in the test executable; this is not installed in the runtime.
"""
from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,json,runpy,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/usr/lib/libMobileGestalt.dylib';image=m['image'](provider);cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
questions={}
for name in ['ProductVersion','HumanReadableProductVersionString']:
 digest=base64.b64encode(hashlib.md5(('MGCopyAnswer'+name).encode()).digest()).decode().rstrip('=')
 pool=next(s for s in image.sections if s[0]=='__cstring');data=m['read'](pool[2],pool[3]);target=pool[2]+data.index(digest.encode()+b'\0')
 rows=[]
 for section,segment,a,n,flags in image.sections:
  if section!='__const':continue
  for at in range(a,a+n-7,8):
   if m['pointer'](at)==target:rows.append(at)
 assert len(rows)==1
 questions[name]=dict(hash=digest,row=hex(rows[0]),callback=m['pointer'](rows[0]+8))
assert questions['ProductVersion']['callback']==0x7ff80915d3f0
assert questions['HumanReadableProductVersionString']['callback']==0x7ff80914e9f1
# Read lengths as integers; they are not slid pointer fields.
def text(a):
 import struct
 n=struct.unpack('<Q',m['read'](a+24,8))[0];return m['read'](m['pointer'](a+16),n).decode()
assert text(0x7ff840aa1268)==questions['ProductVersion']['hash']
assert text(0x7ff840aa4f48)=='ProductVersionExtra' and text(0x7ff840aa1288)=='%@ %@'
assert text(0x7ff840aa6a68)=='iOSSupportVersion'
calls={0x7ff809149c74:'__CFMZEnabled',0x7ff80914991b:'_reference_copy_system_value',0x7ff80914c16e:'_reference_cached_product',0x7ff8091a2220:'__CFCopySupplementalVersionDictionary',0x7ff809149aba:'_reference_copy_value_and_release_dictionary',0x7ff8091a20ac:'_CFStringCreateWithFormat',0x7ff8091a203a:'_CFRelease',0x7ff8091a2040:'_CFRetain'}
constants={0x7ff8400099e8:('_reference_product_key_address','rax'),0x7ff840aa6a68:('_reference_ios_key','rdi'),0x7ff840aa1268:('_reference_product_question','rdi'),0x7ff840aa4f48:('_reference_extra_key','rsi'),0x7ff840009d28:('_reference_allocator_address','rax'),0x7ff840aa1288:('_reference_format','rdx')}
assembly=['.text'];records=[];log=[]
for name,a,n in [('product_version',0x7ff80915d3f0,43),('human_version',0x7ff80914e9f1,149)]:
 instructions=list(cs.disasm(m['read'](a,n),a));assert sum(i.size for i in instructions)==n
 assembly+=['.p2align 4','.globl _reference_'+name,'_reference_'+name+':'];relocations=[]
 for i in instructions:
  log.append(f'{i.address:#x} {i.mnemonic} {i.op_str}')
  rip=[o for o in i.operands if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP]
  if rip:
   target=i.address+i.size+rip[0].mem.disp
   # Native LEA addresses constant CFString objects. A load of a CFSTR pointer
   # has the same 7-byte length and supplies the same kind of object address.
   if name=='product_version' and i.mnemonic=='mov':
    assert i.mnemonic=='mov' and i.size==7 and target==0x7ff8400099e8
    key,reg='_reference_product_key_address','rax'
   else:key,reg=constants[target]
   assert i.size==7
   assembly.append(f'movq {key}(%rip), %{reg}');relocations.append(dict(address=hex(i.address),kind='constant',target=key))
  elif i.mnemonic=='call' or (i.mnemonic=='jmp' and i.operands[0].type==X86_OP_IMM and not a<=i.operands[0].imm<a+n):
   target=i.operands[0].imm;assert target in calls and i.size==5
   assembly.append(('callq ' if i.mnemonic=='call' else 'jmp ')+calls[target]);relocations.append(dict(address=hex(i.address),kind='call',target=calls[target]))
  else:
   if i.mnemonic.startswith('j'):assert a<=i.operands[0].imm<a+n
   assembly.append('.byte '+','.join(hex(v) for v in i.bytes))
 assembly+=['_reference_'+name+'_end:']
 records.append(dict(name=name,address=hex(a),length=n,sha256=hashlib.sha256(m['read'](a,n)).hexdigest(),relocations=relocations))
build=root/'runtime/mobilegestalt-reference';build.mkdir(parents=True,exist_ok=True)
source='runtime/mobilegestalt-reference/reference.S';out='logs/mobilegestalt-version-native-abi.log'
(root/source).write_text('\n'.join(assembly)+'\n');(root/out).write_text('\n'.join(log)+'\n')
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=digest('runtime/fullsystem-libraries'+provider),questions=questions,functions=records,reference_source=source,reference_source_sha256=digest(source),log=out,log_sha256=digest(out),reference_installed=False,
 scope='Original computational instructions, internal branches and CF operations; only external call relocations and constant-object address loads are adapted for controlled dictionary input. This is a differential test oracle, not a production MobileGestalt replacement.')
(root/'artifacts/mobilegestalt-version-callback-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print('Recovered original version and human-readable callbacks with bounded relocations')
