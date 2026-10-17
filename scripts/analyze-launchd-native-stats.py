#!/usr/bin/env python3
"""Bounded read-only inspection of launch-service statistics in Intel launchd."""
from pathlib import Path
import bisect,hashlib,json,re,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
path=root/'runtime/launchd-native-recovery/macOS Base System/sbin/launchd'
data=path.read_bytes();segments=[];sections=[];cursor=32;starts_off=starts_size=0
assert data[:4]==b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I',data,4)[0]==0x1000007
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,cursor)
    if command==0x19:
        name=data[cursor+8:cursor+24].split(b'\0')[0].decode()
        address,length,offset,filesize=struct.unpack_from('<QQQQ',data,cursor+24)
        segments.append((name,address,length,offset,filesize))
        for index in range(struct.unpack_from('<I',data,cursor+64)[0]):
            at=cursor+72+80*index;name=data[at:at+16].split(b'\0')[0].decode()
            address,length,offset=struct.unpack_from('<QQI',data,at+32)
            sections.append((name,address,length,offset))
    if command==0x26:starts_off,starts_size=struct.unpack_from('<II',data,cursor+8)
    cursor+=size
base=next(s[1] for s in segments if s[0]=='__TEXT');starts=[];address=base;value=shift=0
for byte in data[starts_off:starts_off+starts_size]:
    value|=(byte&127)<<shift
    if byte<128:
        if not value:break
        address+=value;starts.append(address);value=shift=0
    else:shift+=7
names={}
listing=subprocess.check_output(['llvm-objdump-19','--macho','--indirect-symbols',str(path)],text=True)
for line in listing.splitlines():
    match=re.match(r'(0x[\da-fA-F]+)\s+\d+\s+(\S+)',line)
    if match:names[int(match[1],16)]=match[2]
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True;machine.skipdata=True
text=next(s for s in sections if s[0]=='__text')
instructions=list(machine.disasm(data[text[3]:text[3]+text[2]],text[1]))
strings={}
for target in [b'monitor_id\0',b'shmem\0',b'labels\0',b'dropped-count\0',b'service_stats_\0',b'service stats = {']:
    for match in re.finditer(re.escape(target),data):
        for _,address,length,offset,size in segments:
            if offset<=match.start()<offset+size:
                strings[address+match.start()-offset]=target.decode().rstrip('\0')
notes=dict(strings)
for name,address,length,offset in sections:
    if name=='__cstring':
        position=offset
        for value in data[offset:offset+length].split(b'\0'):
            if value:notes[address+position-offset]=value.decode(errors='replace')
            position+=len(value)+1
selected={}
for instruction in instructions:
    if not instruction.id:continue
    for operand in instruction.operands:
        if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP:
            target=instruction.address+instruction.size+operand.mem.disp
            if target in strings:
                index=bisect.bisect_right(starts,instruction.address)-1
                begin=starts[index];end=starts[index+1] if index+1<len(starts) else text[1]+text[2]
                selected.setdefault((begin,end),set()).add(strings[target])
for argument in sys.argv[1:]:
    address=int(argument,0);index=bisect.bisect_right(starts,address)-1
    begin=starts[index];end=starts[index+1]
    selected.setdefault((begin,end),set()).add('explicit '+argument)
for (begin,end),labels in selected.items():
    print('\nFUNCTION',hex(begin),hex(end),'keys',','.join(sorted(labels)))
    for instruction in instructions:
        if not begin<=instruction.address<end or not instruction.id:continue
        note=''
        if instruction.mnemonic in ('call','jmp') and instruction.operands[0].type==X86_OP_IMM:
            note=names.get(instruction.operands[0].imm,'')
        for operand in instruction.operands:
            if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP:
                target=instruction.address+instruction.size+operand.mem.disp
                note=notes.get(target,names.get(target,note))
        print(hex(instruction.address),instruction.mnemonic,instruction.op_str,note)
print('\nENCODING',re.findall(rb'[^\0]*_launch_service_stats[^\0]*',data))
report=dict(reference_binary=str(path.relative_to(root)),sha256=hashlib.sha256(data).hexdigest(),
    reference_execution=False,functions=[dict(address=hex(a),end=hex(b),keys=sorted(v)) for (a,b),v in selected.items()])
(root/'artifacts/launchd-native-stats-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
