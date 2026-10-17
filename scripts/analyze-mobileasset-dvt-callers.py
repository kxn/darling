#!/usr/bin/env python3
"""Inspect all genuine DVTFoundation Pallas imports and their Intel call sites."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,re,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_IMM,X86_OP_MEM,X86_REG_RIP
original=root/'runtime/state/prefix/Applications/Xcode.app/Contents/SharedFrameworks/DVTFoundation.framework/Versions/A/DVTFoundation'
fat=original.read_bytes();assert fat[:4]==b'\xca\xfe\xba\xbe'
slices=[struct.unpack_from('>IIIII',fat,8+20*i) for i in range(struct.unpack_from('>I',fat,4)[0])]
intel=next(a for a in slices if a[0]==0x1000007);data=fat[intel[2]:intel[2]+intel[3]]
thin=root/'runtime/mobileasset-source/DVTFoundation.x86_64';thin.write_bytes(data)
required=['_MAGetPallasAudience','_MAGetPallasEnabled','_MASetPallasAudienceForType','_MASetPallasEnabled','_MASetPallasUrlForType']
symbols={}
listing=subprocess.check_output(['llvm-objdump-19','--macho','--indirect-symbols',str(thin)],text=True)
for line in listing.splitlines():
    m=re.match(r'(0x[\da-fA-F]+)\s+\d+\s+(\S+)',line)
    if m and m[2] in required:symbols[int(m[1],16)]=m[2]
assert set(symbols.values())==set(required)
sections=[];segments=[];cursor=32
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,cursor)
    if command==0x19:
        va,length,offset,filesize=struct.unpack_from('<QQQQ',data,cursor+24)
        segments.append((va,length,offset,filesize))
        for j in range(struct.unpack_from('<I',data,cursor+64)[0]):
            at=cursor+72+80*j;name=data[at:at+16].split(b'\0')[0].decode()
            sections.append((name,*struct.unpack_from('<QQI',data,at+32)))
    if command==0x26:startoff,startsize=struct.unpack_from('<II',data,cursor+8)
    cursor+=size
starts=[];address=value=shift=0
for byte in data[startoff:startoff+startsize]:
    value|=(byte&127)<<shift
    if byte<128:
        if not value:break
        address+=value;starts.append(address);value=shift=0
    else:shift+=7
def read(address,length):
    for va,size,offset,filesize in segments:
        if va<=address and address+length<=va+filesize:return data[offset+address-va:offset+address-va+length]
    raise ValueError('Outside file-backed DVT segment')
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True;machine.skipdata=True
text=next(s for s in sections if s[0]=='__text');calls=[];selected=set()
for i in machine.disasm(data[text[3]:text[3]+text[2]],text[1]):
    if not i.id or i.mnemonic not in ('call','jmp') or len(i.operands)!=1:continue
    op=i.operands[0];target=None
    if op.type==X86_OP_IMM:target=op.imm
    elif op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP:target=i.address+i.size+op.mem.disp
    if target not in symbols:continue
    index=bisect.bisect_right(starts,i.address)-1;assert index>=0
    selected.add((starts[index],starts[index+1]))
    calls.append(dict(address=hex(i.address),symbol=symbols[target],function_begin=hex(starts[index])))
assert set(c['symbol'] for c in calls)==set(required)
log=[];functions=[]
for start,end in sorted(selected):
    code=read(start,end-start);functions.append(dict(begin=hex(start),length=len(code),sha256=hashlib.sha256(code).hexdigest()))
    log.append(f'\nDVT FUNCTION {start:#x}..{end:#x}\n')
    for i in machine.disasm(code,start):log.append(f'{i.address:#x} {i.mnemonic} {i.op_str}\n')
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/System/Library/PrivateFrameworks/MobileAsset.framework/Versions/A/MobileAsset'
native=root/'runtime/fullsystem-libraries'/provider.lstrip('/')
names={}
for line in subprocess.check_output(['llvm-nm-19','--defined-only',str(native)],text=True).splitlines():
    parts=line.split(None,2)
    if len(parts)==3:names[parts[2]]=int(parts[0],16)
ordered=sorted(set(names.values()));native_functions=[]
for symbol in required+['__MAsendGetPallasAudience','__MAsendSetPallasAudience','__MAsendSetPallasEnabled','__MAsendSetPallasUrlForType']:
    start=names[symbol];end=ordered[bisect.bisect_right(ordered,start)]
    code=d['read'](start,end-start);assert len(code)<8192
    native_functions.append(dict(symbol=symbol,address=hex(start),length=len(code),sha256=hashlib.sha256(code).hexdigest()))
    log.append('\nNATIVE FUNCTION '+symbol+'\n')
    for i in machine.disasm(code,start):log.append(f'{i.address:#x} {i.mnemonic} {i.op_str}\n')
logpath=root/'logs/mobileasset-dvt-callers.log';logpath.write_text(''.join(log))
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,
    original_DVTFoundation=str(original.relative_to(root)),original_DVTFoundation_sha256=digest(original),
    intel_slice=str(thin.relative_to(root)),intel_slice_sha256=digest(thin),intel_slice_matches_original=True,
    required_functions=required,calls=calls,caller_functions=functions,
    original_MobileAsset=provider,original_MobileAsset_sha256=digest(native),native_functions=native_functions,
    source_execution_report='artifacts/mobileasset-pallas-source.json',
    note='This is static caller/native ABI evidence. Source execution and protocol results are recorded separately, and must match the current source/framework hashes; a bound name alone does not prove the operation behavior.',
    log=str(logpath.relative_to(root)),log_sha256=digest(logpath))
(root/'artifacts/mobileasset-dvt-callers.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified all five original DVT Pallas imports and',len(calls),'Intel call sites; source execution evidence is separate')
