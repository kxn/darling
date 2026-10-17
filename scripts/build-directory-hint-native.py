#!/usr/bin/env python3
"""Experimental recovery of one original nongeneric Foundation enum.

Copy its actual metadata, value witnesses and bounded instruction closure.
Reject foreign data/calls, unknown indirect jumps and unsupported layouts.
Never installs a system framework and never implements URL operations.
"""
from bisect import bisect_right
from pathlib import Path
import hashlib,json,runpy,struct,subprocess,sys

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
import capstone as cs
from capstone import x86_const as x
c=json.loads((root/'config/foundation-staged-additions.json').read_text())
source=root/'runtime/fullsystem-libraries'/c['provider'].lstrip('/')
if hashlib.sha256(source.read_bytes()).hexdigest()!=c['provider_sha256']:raise ValueError('Wrong Foundation')
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
read,pointer=ns['read'],ns['pointer'];prefix='_$s10Foundation3URLV13DirectoryHintO'
resolve=lambda suffix:ns['resolve'](c['provider'],prefix+suffix)
access,descriptor,metadata=map(resolve,['Ma','Mn','N'])
flags=struct.unpack('<I',read(descriptor,4))[0]
if flags!=0x52 or struct.unpack('<II',read(descriptor+20,8))!=(0,4):raise ValueError('Wrong enum descriptor')
def relative(at):return at+struct.unpack('<i',read(at,4))[0]
if relative(descriptor+4)!=ns['resolve'](c['provider'],'_$s10Foundation3URLVMn'):
    raise ValueError('Unexpected parent context')
if relative(descriptor+12)!=access or read(relative(descriptor+8),14)!=b'DirectoryHint\0':raise ValueError('Wrong enum name/accessor')
if struct.unpack('<Q',read(metadata,8))[0]!=0x201 or pointer(metadata+8)!=descriptor:raise ValueError('Wrong enum metadata')
fields=relative(descriptor+16)
if struct.unpack('<iHHI',read(fields+4,12))!=(0,2,12,4):raise ValueError('Wrong field descriptor')
typeref=relative(fields)
if read(typeref,1)!=b'\1' or relative(typeref+1)!=descriptor or read(typeref+5,1)!=b'\0':
    raise ValueError('Unexpected symbolic type reference')
names=[]
for index in range(4):
    at=fields+16+12*index
    if read(at,8)!=bytes(8):raise ValueError('Unexpected enum payload')
    name=read(relative(at+8),128).split(b'\0')[0].decode('ascii');names.append(name)
if names!=['isDirectory','notDirectory','checkFileSystem','inferFromPath']:raise ValueError('Wrong enum cases')
vwt=pointer(metadata-8);witnesses=[pointer(vwt+8*i) for i in [0,1,2,3,4,5,6,7,11,12,13]]
if struct.unpack('<QQII',read(vwt+64,24))!=(1,1,0x02200000,252):raise ValueError('Unsupported value witness layout')
build=root/'runtime/directory-hint-native';build.mkdir(exist_ok=True)
analysis=runpy.run_path(str(root/'scripts/cache-code-analysis.py'))
analysis_image=build/'Foundation.analysis-only.macho'
starts=analysis['reference_with_function_labels'](source,analysis_image)
decoder=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64);decoder.detail=True
pending=set(witnesses+[access]);functions={};relocations={};all_tables=[]
while pending:
    entry=pending.pop()
    if entry in functions:continue
    index=bisect_right(starts,entry)-1
    if index<0 or starts[index]!=entry or index+1>=len(starts):raise ValueError('Not an original function start')
    end=starts[index+1]
    if end-entry>1024 or len(functions)>24:raise ValueError('Unexpectedly large enum code closure')
    disassembly=subprocess.check_output(['llvm-objdump-19','-d','--start-address='+hex(entry),
        '--stop-address='+hex(end),str(analysis_image)],text=True)
    tables=analysis['tail_jump_tables'](disassembly,starts,read);all_tables.extend(tables)
    table_targets={target for table in tables for target in table['targets']}
    work=[entry];visited=set()
    while work:
        pc=work.pop()
        if pc in visited:continue
        if not entry<=pc<end:raise ValueError('CFG leaves function without a checked branch')
        if any(t['start']<=pc<t['end'] for t in tables):raise ValueError(f'CFG enters data at {pc:#x}, function {entry:#x}, end {end:#x}')
        ins=next(decoder.disasm(read(pc,min(15,end-pc)),pc,count=1),None)
        if ins is None:raise ValueError('Invalid reachable instruction')
        visited.add(pc)
        for op in ins.operands:
            if op.type==x.X86_OP_MEM and op.mem.base==x.X86_REG_RIP:
                target=pc+ins.size+op.mem.disp
                if entry<=target<end:continue
                if entry!=access or ins.id!=x.X86_INS_LEA or target!=metadata or ins.disp_size!=4:
                    raise ValueError('Unknown external RIP reference')
                relocations[pc+ins.disp_offset]=('metadata',4)
        if ins.group(cs.CS_GRP_RET) or ins.id==x.X86_INS_UD2:continue
        if ins.group(cs.CS_GRP_JUMP) or ins.group(cs.CS_GRP_CALL):
            if len(ins.operands)!=1:raise ValueError('Unsupported branch')
            op=ins.operands[0]
            if op.type==x.X86_OP_IMM:
                target=op.imm
                if entry<=target<end:work.append(target)
                else:
                    if ins.imm_size!=4 or target not in starts:raise ValueError('Unknown external direct branch')
                    relocations[pc+ins.imm_offset]=('f_'+hex(target)[2:],4);pending.add(target)
            else:
                if ins.id!=x.X86_INS_JMP or not table_targets:raise ValueError('Unchecked indirect branch')
                work.extend(table_targets)
            if ins.id==x.X86_INS_JMP:continue
        work.append(pc+ins.size)
    functions[entry]=(end,read(entry,end-entry))

lines=['.section __TEXT,__text,regular,pure_instructions']
def emit_bytes(payload):
    if payload:lines.append('.byte '+','.join(str(b) for b in payload))
for entry,(end,payload) in sorted(functions.items()):
    lines.extend(['.p2align 4','f_'+hex(entry)[2:]+':'])
    if entry==access:lines.extend(['.globl "'+prefix+'Ma"','"'+prefix+'Ma":'])
    offset=0
    for address,(label,length) in sorted(relocations.items()):
        if not entry<=address<end:continue
        emit_bytes(payload[offset:address-entry]);lines.append('.long '+label+' - . - 4');offset=address-entry+length
    emit_bytes(payload[offset:])
lines.extend(['.section __DATA,__const','.p2align 3','vwt:'])
for target in witnesses[:8]:lines.append('.quad f_'+hex(target)[2:])
emit_bytes(read(vwt+64,24))
for target in witnesses[8:]:lines.append('.quad f_'+hex(target)[2:])
lines.extend(['.p2align 3','.quad vwt','.globl "'+prefix+'N"','"'+prefix+'N":','metadata:',
 '.quad 513','.quad descriptor','.p2align 3','parent_slot:','.quad "_$s10Foundation3URLVMn"',
 '.section __TEXT,__const','.p2align 2','.globl "'+prefix+'Mn"','"'+prefix+'Mn":','descriptor:',
 '.long 82','.long parent_slot - . + 1','.long enum_name - .','.long f_'+hex(access)[2:]+' - .',
 '.long fields - .','.long 0','.long 4','fields:','.long typeref - .','.long 0','.short 2,12','.long 4'])
for index,name in enumerate(names):lines.extend(['.long 0,0','.long case_'+str(index)+' - .'])
lines.extend(['enum_name:','.asciz "DirectoryHint"','typeref:','.byte 1','.long descriptor - .','.byte 0'])
for index,name in enumerate(names):lines.extend(['case_'+str(index)+':','.asciz '+json.dumps(name)])
lines.extend(['.section __TEXT,__swift5_types,regular,no_dead_strip','.p2align 2',
 '.globl directory_hint_types_record','.private_extern directory_hint_types_record',
 'directory_hint_types_record:','.long "'+prefix+'Mn" - directory_hint_types_record'])
(build/'enum.s').write_text('\n'.join(lines)+'\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-c',str(build/'enum.s'),'-o',str(build/'enum.o')],check=True)
destination=root/'runtime/native-library-stage/libDarlingDirectoryHint.dylib';temporary=destination.with_suffix('.dylib.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
 '-install_name','/usr/lib/libDarlingDirectoryHint.dylib','-syslibroot',str(guest),'-L',str(guest/'usr/lib'),
 '-lSystem','-framework','Foundation',str(build/'enum.o'),'-o',str(temporary)],check=True)
temporary.replace(destination)
report={'original_foundation_sha256':c['provider_sha256'],'installed':False,'execution_verified':False,
 'library_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
 'original_functions':[{'address':hex(a),'length':end-a,'sha256':hashlib.sha256(payload).hexdigest()} for a,(end,payload) in sorted(functions.items())],
 'tail_tables':all_tables,'relocations':{hex(a):v for a,v in relocations.items()},
 'scope':'One original nongeneric enum metadata/value-witness code closure. No URL operations or full Foundation compatibility.'}
(root/'artifacts/directory-hint-native.json').write_text(json.dumps(report,indent=2)+'\n')
print('Original enum closure:',len(functions),'functions,',len(all_tables),'validated tables')
