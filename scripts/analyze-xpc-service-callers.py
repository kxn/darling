#!/usr/bin/env python3
"""Inspect actual Intel DVT service call sites and original launchd handlers."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,re,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True;machine.skipdata=True
reports=[];output=[]
for relative in ['runtime/launchd-source/DVTInstrumentsFoundation.x86_64',
        'runtime/launchd-native-recovery/macOS Base System/sbin/launchd']:
    path=root/relative;data=path.read_bytes();segments=[];sections=[];cursor=32;startoff=startsize=0
    assert data[:4]==b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I',data,4)[0]==0x1000007
    original_fat=None
    if relative.endswith('.x86_64'):
        original_fat=root/'runtime/state/prefix/Applications/Xcode.app/Contents/SharedFrameworks/DVTInstrumentsFoundation.framework/Versions/A/DVTInstrumentsFoundation'
        fat=original_fat.read_bytes();assert fat[:4]==b'\xca\xfe\xba\xbe'
        slices=[struct.unpack_from('>IIIII',fat,8+index*20) for index in range(struct.unpack_from('>I',fat,4)[0])]
        intel=next(a for a in slices if a[0]==0x1000007)
        assert fat[intel[2]:intel[2]+intel[3]]==data
    else:
        assert hashlib.sha256(data).hexdigest()=='687c9472ec21bdb5e81ce57ceba4aeec531e26923abd5d545ae33ad38ac8b832'
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        command,size=struct.unpack_from('<II',data,cursor)
        if command==0x19:
            name=data[cursor+8:cursor+24].split(b'\0')[0].decode()
            address,length,offset,filesize=struct.unpack_from('<QQQQ',data,cursor+24)
            segments.append((name,address,length,offset,filesize))
            for index in range(struct.unpack_from('<I',data,cursor+64)[0]):
                at=cursor+72+index*80;name=data[at:at+16].split(b'\0')[0].decode()
                address,length,offset=struct.unpack_from('<QQI',data,at+32)
                sections.append((name,address,length,offset))
        if command==0x26:startoff,startsize=struct.unpack_from('<II',data,cursor+8)
        cursor+=size
    base=next(s[1] for s in segments if s[0]=='__TEXT');starts=[];address=base;value=shift=0
    for byte in data[startoff:startoff+startsize]:
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
    strings={}
    for name,address,length,offset in sections:
        if name in ('__cstring','__objc_methname'):
            position=address
            for value in data[offset:offset+length].split(b'\0'):
                if value:strings[position]=value.decode(errors='replace')
                position+=len(value)+1
    text=next(s for s in sections if s[0]=='__text')
    instructions=list(machine.disasm(data[text[3]:text[3]+text[2]],text[1]))
    selected={};calls=[]
    for i in instructions:
        if not i.id:continue
        reason=None
        if i.mnemonic in ('call','jmp') and i.operands[0].type==X86_OP_IMM:
            symbol=names.get(i.operands[0].imm,'')
            if relative.endswith('.x86_64') and symbol.startswith('_xpc_service'):
                reason=symbol;calls.append(dict(address=hex(i.address),symbol=symbol))
        if not relative.endswith('.x86_64'):
            for op in i.operands:
                if op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP:
                    key=strings.get(i.address+i.size+op.mem.disp)
                    if key in ('suspended','unthrottle','service-ctl-reply-port'):
                        reason=key
        if reason:
            index=bisect.bisect_right(starts,i.address)-1
            begin=starts[index];end=starts[index+1]
            selected.setdefault((begin,end),set()).add(reason)
    output.append('\nIMAGE '+relative+'\n')
    for (begin,end),reasons in selected.items():
        output.append(f'\nFUNCTION {begin:#x}..{end:#x} '+','.join(sorted(reasons))+'\n')
        for i in instructions:
            if not begin<=i.address<end or not i.id:continue
            note=''
            if i.mnemonic in ('call','jmp') and i.operands[0].type==X86_OP_IMM:
                note=names.get(i.operands[0].imm,'')
            for op in i.operands:
                if op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP:
                    target=i.address+i.size+op.mem.disp
                    note=strings.get(target,names.get(target,note))
            output.append(f'{i.address:#x} {i.mnemonic} {i.op_str} {note}\n')
    reports.append(dict(path=relative,sha256=hashlib.sha256(data).hexdigest(),calls=calls,
        installed_original_fat_path=str(original_fat.relative_to(root)) if original_fat else None,
        installed_original_fat_sha256=hashlib.sha256(original_fat.read_bytes()).hexdigest() if original_fat else None,
        intel_slice_matches_original_fat=bool(original_fat),
        functions=[dict(begin=hex(a),end=hex(b),reasons=sorted(v)) for (a,b),v in selected.items()]))
log=root/'logs/xpc-service-native-callers.log';log.write_text(''.join(output))
(root/'artifacts/xpc-service-native-callers.json').write_text(json.dumps(dict(
    checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,images=reports,
    log=str(log.relative_to(root)),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()),indent=2)+'\n')
print('Read-only service caller analysis:',[(len(r['functions']),len(r['calls'])) for r in reports])
