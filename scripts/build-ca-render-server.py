#!/usr/bin/env python3
"""Build Darling's source component and a strictly bounded test-only oracle."""
from pathlib import Path
import hashlib,json,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
import capstone as cs
from capstone import x86_const as x
config=json.loads((root/'config/ca-render-server.json').read_text())
repo=root/'vendor/darling/src/external/cocotron'
if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=config['darling_source_commit']:
    raise ValueError('Changed base Darling source revision')
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
source=root/'runtime/fullsystem-libraries'/config['provider'].lstrip('/')
if hashlib.sha256(source.read_bytes()).hexdigest()!=config['provider_sha256']:raise ValueError('Changed native QuartzCore')
read,pointer=ns['read'],ns['pointer'];image=ns['image'](config['provider'])
functions=config['oracle_functions']
for name,symbol in [('query','_CARenderServerGetDebugOption'),('set_option','_CARenderServerSetDebugOption'),('frame_counter','_CARenderServerGetFrameCounter')]:
    record=next(f for f in functions if f['name']==name)
    if int(record['address'],0)!=ns['resolve'](config['provider'],symbol):raise ValueError('Changed bounded native entry')
service=config['service_name'];text=service['value'].encode()+b'\0'
if read(int(service['address'],0),len(text))!=text:raise ValueError('Changed actual service name')
data=source.read_bytes();imports={};at=32
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,length=struct.unpack_from('<II',data,at)
    if command==2:
        symbols,count,strings,size=struct.unpack_from('<IIII',data,at+8)
        for index in range(count):
            offset,kind,section,desc,value=struct.unpack_from('<IBBHQ',data,symbols+index*16)
            if kind&14 or not kind&1:continue
            ordinal=desc>>8
            if not 1<=ordinal<=len(image.dependencies):raise ValueError('Unsupported original import ordinal')
            name=data[strings+offset:data.index(0,strings+offset)].decode();provider=image.dependencies[ordinal-1]
            target=ns['resolve'](provider,name)
            if target is not None:imports[target]=(name,provider)
    at+=length
callbacks={int(config['oracle_callbacks'][kind],0):'_darling_ca_oracle_'+kind for kind in ['lookup','result']}
entries={int(f['address'],0):'_darling_ca_native_'+f['name'] for f in functions}
allowed_providers={'/usr/lib/libSystem.B.dylib','/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation'}
key=config['frame_count_key'];key_address=int(key['address'],0)
key_bytes=read(key_address,32)
if hashlib.sha256(key_bytes).hexdigest()!=key['sha256']:raise ValueError('Changed frame counter key')
if read(pointer(key_address+16),len(key['value'])+1)!=key['value'].encode()+b'\0':raise ValueError('Changed frame counter key value')
decoder=cs.Cs(cs.CS_ARCH_X86,cs.CS_MODE_64);decoder.detail=True
all_fixups={};got={};branches={};lines=['.section __TEXT,__text,regular,pure_instructions']
for record in functions:
    start=int(record['address'],0);raw=read(start,record['length'])
    if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('Changed native function: '+record['name'])
    payload=raw[:record.get('code_length',record['length'])];end=start+len(payload)
    fixups={};tails={};instructions=list(decoder.disasm(payload,start))
    if sum(i.size for i in instructions)!=len(payload):raise ValueError('Undecoded native bytes: '+record['name'])
    for ins in instructions:
        for operand in ins.operands:
            if operand.type==x.X86_OP_MEM and operand.mem.base==x.X86_REG_RIP:
                target=ins.address+ins.size+operand.mem.disp
                if start<=target<end:continue
                if target==key_address:
                    label='L_ca_frame_key'
                else:
                    symbol=imports.get(pointer(target))
                    if not symbol or symbol[1] not in allowed_providers:
                        raise ValueError('Unsupported oracle data reference: '+hex(target))
                    name=symbol[0];label=got.setdefault(name,'L_ca_got_'+str(len(got)))
                if ins.disp_size!=4:raise ValueError('Unsupported data displacement')
                fixups[ins.address+ins.disp_offset]=(label,'data')
                tails[ins.address+ins.disp_offset]=ins.size-ins.disp_offset-4
        if ins.group(cs.CS_GRP_CALL) or ins.group(cs.CS_GRP_JUMP):
            if len(ins.operands)!=1 or ins.operands[0].type!=x.X86_OP_IMM:raise ValueError('Unchecked indirect native branch')
            target=ins.operands[0].imm
            if start<=target<end:continue
            symbol=entries.get(target) or callbacks.get(target)
            if symbol is None:
                stub=read(target,6)
                if stub[:2]!=b'\xff\x25':raise ValueError('Unknown oracle external branch: '+hex(target))
                slot=target+6+struct.unpack('<i',stub[2:])[0];entry=imports.get(pointer(slot))
                if entry is None or entry[1] not in allowed_providers:raise ValueError('Unsupported oracle function import')
                symbol=entry[0]
            if ins.imm_size!=4:raise ValueError('Unsupported oracle branch encoding')
            label=branches.setdefault(symbol,'L_ca_branch_'+str(len(branches)))
            fixups[ins.address+ins.imm_offset]=(label,'branch')
    name=entries[start];lines+=['.p2align 4','.globl '+name,name+':'];offset=0
    for address,(label,kind) in sorted(fixups.items()):
        begin=address-start
        if begin<offset:raise ValueError('Overlapping native oracle relocation')
        if begin>offset:lines.append('.byte '+','.join(str(b) for b in payload[offset:begin]))
        lines.append('.long '+label+' - . - 4 - '+str(tails.get(address,0)));offset=begin+4
    if offset<len(payload):lines.append('.byte '+','.join(str(b) for b in payload[offset:]))
    all_fixups.update(fixups)
for name,label in branches.items():lines += [label+':','jmp '+name]
lines+=['.section __DATA,__const','.p2align 3']
for name,label in got.items():lines += [label+':','.quad '+name]
lines+=['.section __TEXT,__cstring,cstring_literals','L_ca_frame_key_text:',
    '.asciz "'+key['value']+'"','.section __DATA,__cfstring','.p2align 3',
    'L_ca_frame_key:','.quad ___CFConstantStringClassReference',
    '.quad '+str(struct.unpack_from('<Q',key_bytes,8)[0]),'.quad L_ca_frame_key_text',
    '.quad '+str(len(key['value']))]
build=root/'runtime/ca-render-server';build.mkdir(exist_ok=True)
(build/'native-oracle.s').write_text('\n'.join(lines)+'\n')
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-c',str(build/'native-oracle.s'),'-o',str(build/'native-oracle.o')],check=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source=repo/'QuartzCore/CARenderServer.m';obj=build/'CARenderServer.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-I',str(repo/'QuartzCore/private-include'),'-O2','-c',str(source),'-o',str(obj)],check=True)
guest=root/'runtime/rootfs/usr/libexec/darling';output=build/'libDarlingCARenderServer.dylib'
temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem',
    '-F',str(guest/'System/Library/Frameworks'),'-framework','CoreFoundation','-install_name',
    '/usr/lib/libDarlingCARenderServer.dylib',str(obj),'-o',str(temporary)],check=True)
temporary.replace(output)
report=dict(installed=False,full_compatibility=False,selected_api_execution_verified=False,
    native_functions=functions,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
    library_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),oracle_relocations={hex(k):v for k,v in all_fixups.items()},
    oracle_branch_symbols=branches,
    scope=config['scope'])
(root/'artifacts/ca-render-server.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built Darling source and bounded test-only native RPC oracle')
