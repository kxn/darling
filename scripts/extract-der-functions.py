#!/usr/bin/env python3
"""Stage original x86_64 DER routines, preserving their internal code offsets.

Generates an assembly object from the verified local Apple recovery cache. No
runtime installation. External calls are rebound to named Darwin imports.
"""
import bisect
import hashlib
import json
from pathlib import Path
import re
import runpy
import struct
import subprocess

project=Path(__file__).resolve().parent.parent
ns=runpy.run_path(str(project/'scripts/dsc-image.py'))
read,pointer,u=ns['read'],ns['pointer'],ns['uleb_read']
source=project/'runtime/recovery-libraries/usr/lib/system/libcorecrypto.dylib'
data=source.read_bytes();obj=ns['image']('/usr/lib/system/libcorecrypto.dylib')
if hashlib.sha256(data).hexdigest()!='5c882125929900553cf60879c2f1ccd4db9a429711f47baa2e070c14d1afffa7':
    raise SystemExit('Unexpected corecrypto reference image; review function extraction before using another version')
build=project/'runtime/rebuilt-der';build.mkdir(parents=True,exist_ok=True)
names={};undefined=[];data_ranges=[];stub_ranges=[];cursor=32
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,cursor)
    if command==2:
        symoff,count,stroff,strsize=struct.unpack_from('<IIII',data,cursor+8)
        for i in range(count):
            start,kind,section,desc,value=struct.unpack_from('<IBBHQ',data,symoff+16*i)
            name=data[stroff+start:data.index(0,stroff+start)].decode()
            if kind&0xe==0xe and value:names.setdefault(value,name)
            if kind&0xe==0 and kind&1:undefined.append((name,desc>>8))
    elif command==0x26:starts_offset,starts_size=struct.unpack_from('<II',data,cursor+8)
    elif command==0x29:
        off,length=struct.unpack_from('<II',data,cursor+8)
        data_ranges=list(struct.iter_unpack('<IHH',data[off:off+length]))
    elif command==0x19:
        for i in range(struct.unpack_from('<I',data,cursor+64)[0]):
            at=cursor+72+80*i
            section_name=data[at:at+16].split(b'\0')[0]
            address,length=struct.unpack_from('<QQ',data,at+32)
            if section_name==b'__stubs':stub_ranges.append((address,address+length))
    cursor+=size
starts=[];at=0;addr=obj.base;payload=data[starts_offset:starts_offset+starts_size]
while at<len(payload):
    delta,at=u(payload,at)
    if not delta:break
    addr+=delta;starts.append(addr)
end_for={a:b for a,b in zip(starts,starts[1:])}
roots={'_ccder_blob_'+name for name in ('decode_len','decode_range','decode_sequence_tl',
    'decode_tag','decode_tl','encode_body_tl','encode_tl','reserve_tl')}
imports={}
for name,ordinal in undefined:
    if not 1<=ordinal<=len(obj.dependencies):continue
    target=ns['resolve'](obj.dependencies[ordinal-1],name)
    if target is not None:imports.setdefault(target,name)
disassembly=subprocess.check_output(['llvm-objdump-19','-d','--disassemble-zeroes',str(source)],text=True)
(build/'original-disassembly.log').write_text(disassembly)
instructions={}
for line in disassembly.splitlines():
    m=re.match(r'^([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(.*)',line)
    if m:instructions[int(m[1],16)]=(bytes.fromhex(m[2]),m[3])

selected={};stubs={};queue=[a for a,name in names.items() if name in roots]
def in_data(address):return any(obj.base+off<=address<obj.base+off+size for off,size,_ in data_ranges)
while queue:
    start=queue.pop()
    if start in selected:continue
    if start not in end_for:raise ValueError(f'Not a bounded function: {start:#x}')
    if not names.get(start,'').startswith('_ccder_'):raise ValueError('Unexpected function dependency '+str(names.get(start)))
    end=end_for[start]
    selected[start]=(end,read(start,end-start))
    for pc,(code,text) in instructions.items():
        if not start<=pc<end or in_data(pc):continue
        branch=re.search(r'\b(?:callq?|jmpq?|j\w+)\s+(0x[0-9a-f]+)',text)
        if not branch:continue
        target=int(branch[1],16)
        if start<=target<end:continue
        if any(a<=target<b for a,b in stub_ranges):
            raw=read(target,6)
            if raw[:2]!=b'\xff\x25':raise ValueError('Unsupported external stub')
            slot=target+6+struct.unpack_from('<i',raw,2)[0]
            external=imports.get(pointer(slot))
            if not external:raise ValueError('Unresolved external stub import')
            stubs[target]=external
        else:
            index=bisect.bisect_right(starts,target)-1
            destination=starts[index]
            if index+1>=len(starts):raise ValueError('External branch outside supported code')
            queue.append(destination)

base=min(selected)
chunks={};fixups={};got={}
for start,(end,code) in selected.items():chunks[start]=code
for address,name in stubs.items():
    chunks[address]=b'\xff\x25'+bytes(4)
    got.setdefault(name,'L_der_got_'+str(len(got)))
    fixups[address+2]=got[name]
for start,(end,code) in selected.items():
    for pc,(encoded,text) in instructions.items():
        if not start<=pc<end or in_data(pc) or '(%rip)' not in text:continue
        ref=re.search(r'## (0x[0-9a-f]+)',text)
        if not ref:raise ValueError('Missing RIP target')
        target=int(ref[1],16)
        if any(a<=target<b for a,(b,_) in selected.items()):continue
        symbol=imports.get(pointer(target))
        if not symbol:raise ValueError(f'Unsupported external data reference {target:#x}')
        got.setdefault(symbol,'L_der_got_'+str(len(got)))
        old=struct.pack('<i',target-pc-len(encoded))
        matches=[i for i in range(len(encoded)-3) if encoded[i:i+4]==old]
        if len(matches)!=1:raise ValueError('Ambiguous RIP displacement')
        fixups[pc+matches[0]]=got[symbol]

lines=['// Generated from original Apple recovery code, x86_64 only.',
       '.section __TEXT,__der_blob,regular,pure_instructions','L_der_original_base:']
for address,code in sorted(chunks.items()):
    lines.append(f'.org {address-base}')
    if names.get(address) in roots:lines.extend(['.globl '+names[address],names[address]+':'])
    cursor=0
    while cursor<len(code):
        fixup=fixups.get(address+cursor)
        if fixup:
            lines.append('.long '+fixup+' - . - 4');cursor+=4
        else:
            end=min(len(code),cursor+24)
            while any(address+i in fixups for i in range(cursor+1,end)):
                end=min(i for i in range(cursor+1,end) if address+i in fixups)
            lines.append('.byte '+','.join(hex(b) for b in code[cursor:end]));cursor=end
lines.extend(['.section __DATA,__der_got','.p2align 3'])
for symbol,label in got.items():lines.extend([label+':','.quad '+symbol])
assembly=build/'der.S';assembly.write_text('\n'.join(lines)+'\n')
subprocess.run(['clang-19','-target','x86_64-apple-macos14.0','-c',str(assembly),'-o',str(build/'der.o')],check=True)
report={'source_sha256':hashlib.sha256(data).hexdigest(),'public_functions':sorted(roots),
        'original_functions_copied':[names[a] for a in sorted(selected)],
        'external_functions':sorted(got),'original_offsets_preserved':True,
        'execution_verified':False,'installed':False}
(build/'extraction.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
