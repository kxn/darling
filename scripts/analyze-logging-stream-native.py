#!/usr/bin/env python3
"""Read original Intel logging-stream class metadata; never executes or installs it."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
read,pointer=d['read'],d['pointer']
provider=globals().get('ANALYSIS_PROVIDER','/System/Library/PrivateFrameworks/LoggingSupport.framework/Versions/A/LoggingSupport')
class_names=globals().get('ANALYSIS_CLASS_NAMES',['OSLogDeserializedEventStream','OSLogEventStreamBase','OSLogEventStream','OSLogEventProxy'])
prefix=globals().get('ANALYSIS_PREFIX','logging-stream')
image=d['image'](provider);path=root/'runtime/fullsystem-libraries'/provider.lstrip('/')
data=path.read_bytes();digest=lambda b:hashlib.sha256(b).hexdigest()
symbols=subprocess.check_output(['llvm-nm-19','--defined-only',str(root/'runtime/fullsystem-libraries/usr/lib/libobjc.A.dylib')],text=True)
opt=next(int(line.split()[0],16) for line in symbols.splitlines() if line.split() and line.split()[-1]=='__objc_opt_data')
assert struct.unpack('<I',read(opt,4))[0]==16
selector_base=opt+struct.unpack('<q',read(opt+40,8))[0]
assert read(selector_base,5)==b'\xf0\x9f\xa4\xaf\0'
cursor=image.base+32;starts=[]
for _ in range(struct.unpack_from('<I',read(image.base,32),16)[0]):
    command,size=struct.unpack('<II',read(cursor,8));raw=read(cursor,size)
    if command==0x26:startoff,startsize=struct.unpack_from('<II',raw,8)
    cursor+=size
segment=next(s for s in image.segments if s[0]=='__LINKEDIT');address=image.base;value=shift=0
for byte in read(segment[1]+startoff-segment[3],startsize):
    value|=(byte&127)<<shift
    if byte<128:
        if not value:break
        address+=value;starts.append(address);value=shift=0
    else:shift+=7
def string(address):
    return read(address,4096).split(b'\0')[0].decode(errors='replace') if address else None
def base_list(slot):
    address=pointer(slot)
    if address&1:
        head=address&~1;size,count=struct.unpack('<II',read(head,8));assert size==8 and 1<=count<=4096
        entry=head+8+8*(count-1);delta=struct.unpack('<Q',read(entry,8))[0]>>16
        if delta&(1<<47):delta-=1<<48
        address=entry+delta
    return address
def methods(slot):
    address=base_list(slot)
    if not address:return []
    flags,count=struct.unpack('<II',read(address,8));assert count<=4096
    result=[];stride=12 if flags&0x80000000 else 24
    for index in range(count):
        entry=address+8+index*stride
        if stride==12:
            name_off,type_off,imp_off=struct.unpack('<iii',read(entry,12))
            name=selector_base+name_off if flags&0x40000000 else pointer(entry+name_off)
            types=entry+4+type_off if type_off else 0;implementation=entry+8+imp_off if imp_off else 0
        else:name,types,implementation=(pointer(entry+i) for i in (0,8,16))
        result.append(dict(selector=string(name),types=string(types),implementation=hex(implementation)))
    return result
classes=[];machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.skipdata=True;machine.detail=True;log=[]
selector_refs=next(s for s in image.sections if s[0]=='__objc_selrefs')
def note(instruction):
    if not instruction.id:return ''
    for operand in instruction.operands:
        if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP:
            target=instruction.address+instruction.size+operand.mem.disp
            if selector_refs[2]<=target<selector_refs[2]+selector_refs[3]:
                return 'selector: '+string(pointer(target))
    return ''
for name in class_names:
    address=d['resolve'](provider,'_OBJC_CLASS_$_'+name)
    if address is None:
        # Some framework-internal classes have genuine class-list metadata but
        # deliberately no public class export (for example MAXpcManager).
        section=next((s for s in image.sections if s[0]=='__objc_classlist'),None)
        matches=[]
        if section:
            for slot in range(section[2],section[2]+section[3],8):
                candidate=pointer(slot);candidate_ro=pointer(candidate+32)&~7
                if string(pointer(candidate_ro+24))==name:matches.append(candidate)
        if len(matches)>1:raise ValueError('Ambiguous native class-list name: '+name)
        if matches:address=matches[0]
    if address is None:continue
    ro=pointer(address+32)&~7;assert string(pointer(ro+24))==name
    superclass=pointer(address+8);superro=pointer(superclass+32)&~7
    meta=pointer(address);metaro=pointer(meta+32)&~7
    entries=methods(ro+32);class_entries=methods(metaro+32)
    ivars=[];ivar_list=base_list(ro+48)
    if ivar_list:
        size,count=struct.unpack('<II',read(ivar_list,8));assert size==32 and count<=4096
        for index in range(count):
            entry=ivar_list+8+index*size
            ivars.append(dict(name=string(pointer(entry+8)),type=string(pointer(entry+16)),
                offset=struct.unpack('<I',read(pointer(entry),4))[0],size=struct.unpack('<I',read(entry+28,4))[0]))
    item=dict(name=name,address=hex(address),superclass=string(pointer(superro+24)),
        instance_size=struct.unpack('<I',read(ro+8,4))[0],methods=entries,class_methods=class_entries,ivars=ivars)
    classes.append(item)
    for method in entries+class_entries:
        address=int(method['implementation'],0);index=bisect.bisect_right(starts,address)-1
        if index<0 or starts[index]!=address or index+1==len(starts):continue
        end=starts[index+1];code=read(address,end-address)
        method.update(length=len(code),sha256=digest(code))
        log.append(f'\nMETHOD {name} {method["selector"]} {method["types"]} {address:#x}..{end:#x}\n')
        for i in machine.disasm(code,address):log.append(f'{i.address:#x} {i.mnemonic} {i.op_str} {note(i)}\n')
logpath=root/('logs/'+prefix+'-native-methods.log');logpath.write_text(''.join(log))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=digest(data),
    native_execution=False,source_implementation_added=False,private_native_layout_reused=False,
    image_class_count=next(s[3]//8 for s in image.sections if s[0]=='__objc_classlist'),
    dependencies=image.dependencies,classes=classes,
    log=str(logpath.relative_to(root)),log_sha256=digest(logpath.read_bytes()),
    existing_darling_note=globals().get('ANALYSIS_NOTE','OSLogEventStream and OSLogEventStreamBase currently contain generic forwarding stubs; OSLogDeserializedEventStream is absent. No empty class was added.'))
(root/('artifacts/'+prefix+'-native-analysis.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Native classes:',[(c['name'],c['superclass'],len(c['methods'])) for c in classes])
