#!/usr/bin/env python3
"""Read actual Intel DVT CADisplay class-reference callers and selectors."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,struct,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
path=root/'runtime/launchd-source/DVTInstrumentsFoundation.x86_64';data=path.read_bytes()
original=root/'runtime/state/prefix/Applications/Xcode.app/Contents/SharedFrameworks/DVTInstrumentsFoundation.framework/Versions/A/DVTInstrumentsFoundation'
fat=original.read_bytes();assert fat[:4]==b'\xca\xfe\xba\xbe'
arches=[struct.unpack_from('>IIIII',fat,8+i*20) for i in range(struct.unpack_from('>I',fat,4)[0])]
intel=next(a for a in arches if a[0]==0x1000007);assert fat[intel[2]:intel[2]+intel[3]]==data
cursor=32;sections=[];segments=[]
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,cursor)
    if command==0x19:
        va,length,offset,filesize=struct.unpack_from('<QQQQ',data,cursor+24)
        segments.append((va,length,offset,filesize))
        for i in range(struct.unpack_from('<I',data,cursor+64)[0]):
            at=cursor+72+i*80;name=data[at:at+16].split(b'\0')[0].decode()
            sections.append((name,*struct.unpack_from('<QQI',data,at+32)))
    if command==0x26:startoff,startsize=struct.unpack_from('<II',data,cursor+8)
    if command==0x80000034:chainoff,chainsize=struct.unpack_from('<II',data,cursor+8)
    cursor+=size
blob=data[chainoff:chainoff+chainsize]
version,start,imports,symbols,count,kind,compression=struct.unpack_from('<7I',blob)
assert not version and not compression and kind in (1,2,3)
stride={1:4,2:8,3:16}[kind];index=None
for i in range(count):
    packed=struct.unpack_from('<Q' if kind==3 else '<I',blob,imports+i*stride)[0]
    nameoff=packed>>32 if kind==3 else packed>>9
    name=blob[symbols+nameoff:blob.index(0,symbols+nameoff)].decode()
    if name=='_OBJC_CLASS_$_CADisplay':index=i
assert index is not None
refs=[]
for name,address,length,offset in sections:
    if name=='__objc_classrefs':
        for i in range(0,length,8):
            raw=struct.unpack_from('<Q',data,offset+i)[0]
            if raw>>63 and raw&0xffffff==index:refs.append(address+i)
assert refs
starts=[];address=value=shift=0
for byte in data[startoff:startoff+startsize]:
    value|=(byte&127)<<shift
    if byte<128:
        if not value:break
        address+=value;starts.append(address);value=shift=0
    else:shift+=7
def read(address,length):
    for va,size,offset,filesize in segments:
        if va<=address and address+length<=va+filesize:
            return data[offset+address-va:offset+address-va+length]
    raise ValueError('Address outside file-backed segment')
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True;machine.skipdata=True
text=next(s for s in sections if s[0]=='__text')
instructions=list(machine.disasm(data[text[3]:text[3]+text[2]],text[1]));selected=set()
for i in instructions:
    if i.id and any(o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP
            and i.address+i.size+o.mem.disp in refs for o in i.operands):
        n=bisect.bisect_right(starts,i.address)-1;selected.add((starts[n],starts[n+1]))
log=[];functions=[]
for begin,end in sorted(selected):
    selectors=set();log.append(f'\nFUNCTION {begin:#x}..{end:#x}\n')
    for i in instructions:
        if not begin<=i.address<end or not i.id:continue
        note=''
        for o in i.operands:
            if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP:
                target=i.address+i.size+o.mem.disp
                if target in refs:note='class: CADisplay'
                elif any(name=='__objc_selrefs' and va<=target<va+length
                        for name,va,length,offset in sections):
                    raw=struct.unpack('<Q',read(target,8))[0];assert not raw>>63
                    address=(raw&((1<<36)-1))|(((raw>>36)&255)<<56)
                    note=read(address,120).split(b'\0')[0].decode()
                    selectors.add(note)
        log.append(f'{i.address:#x} {i.mnemonic} {i.op_str} {note}\n')
    functions.append(dict(begin=hex(begin),end=hex(end),sha256=hashlib.sha256(read(begin,end-begin)).hexdigest(),
        selectors=sorted(selectors)))
logpath=root/'logs/ca-display-dvt-callers.log';logpath.write_text(''.join(log))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,
    image=str(path.relative_to(root)),image_sha256=hashlib.sha256(data).hexdigest(),
    installed_original_fat=str(original.relative_to(root)),installed_original_fat_sha256=hashlib.sha256(fat).hexdigest(),
    intel_slice_matches_original=True,class_import_index=index,class_refs=[hex(r) for r in refs],functions=functions,
    scope='Static functions referencing CADisplay. Other selectors in those functions also target other objects; no dynamic receiver or execution proof.',
    log=str(logpath.relative_to(root)),log_sha256=hashlib.sha256(logpath.read_bytes()).hexdigest())
(root/'artifacts/ca-display-dvt-callers.json').write_text(json.dumps(report,indent=2)+'\n')
print('Original DVT CADisplay callers:',len(functions))
