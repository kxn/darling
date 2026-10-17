#!/usr/bin/env python3
"""Read the pinned Intel sandbox extension wrappers and their data object ABI."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,runpy,struct,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
pins=json.loads((root/'config/cache-image-pins.json').read_text())['sandbox-native']
digest=lambda b:hashlib.sha256(b).hexdigest()
original=root/'runtime/fullsystem-libraries/usr/lib/system/libsystem_sandbox.dylib'
assert digest(original.read_bytes())==pins['sha256']
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
image=d['image'](pins['path']);header=d['read'](image.base,32)
commands=d['read'](image.base+32,struct.unpack_from('<I',header,20)[0]);cursor=0;function_data=None
for _ in range(struct.unpack_from('<I',header,16)[0]):
    command,length=struct.unpack_from('<II',commands,cursor)
    if command==0x26:function_data=struct.unpack_from('<II',commands,cursor+8)
    cursor+=length
segment=next(s for s in image.segments if s[0]=='__LINKEDIT')
encoded=d['read'](segment[1]+function_data[0]-segment[3],function_data[1])
cursor=0;address=image.base;starts=[]
while cursor<len(encoded):
    delta,cursor=d['uleb_read'](encoded,cursor)
    if not delta:break
    address+=delta;starts.append(address)
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.skipdata=True;functions=[]
names=['_sandbox_extension_issue_file','_sandbox_extension_issue_file_to_process',
       '_sandbox_extension_issue_file_to_process_by_pid','_sandbox_extension_issue_file_to_self',
       '_sandbox_extension_consume','_sandbox_extension_release']
log=root/'logs/sandbox-extension-native-abi.log'
with log.open('w') as stream:
    for name,address in [(name,d['resolve'](pins['path'],name)) for name in names]+[('shared_file_issue',0x7ff810896102)]:
        index=bisect.bisect_right(starts,address)-1
        assert starts[index]==address
        end=starts[index+1];code=d['read'](address,end-address)
        instructions=list(machine.disasm(code,address))
        assert sum(i.size for i in instructions)==len(code)
        functions.append(dict(symbol=name,address=hex(address),size=len(code),sha256=digest(code)))
        print('\nFUNCTION',name,hex(address),hex(end),file=stream)
        for i in instructions:print(hex(i.address),i.mnemonic,i.op_str,file=stream)
constants={}
for name,expected in [('SANDBOX_EXTENSION_DEFAULT',0),('SANDBOX_EXTENSION_CANONICAL',2),
                       ('SANDBOX_EXTENSION_PREFIXMATCH',4),('SANDBOX_EXTENSION_NO_REPORT',16)]:
    address=d['resolve'](pins['path'],'_'+name)
    value=struct.unpack('<I',d['read'](address,4))[0]
    assert value==expected
    constants[name]=dict(address=hex(address),type='uint32_t',value=value)
for name in ['APP_SANDBOX_READ','APP_SANDBOX_READ_WRITE','APP_SANDBOX_MACH','APP_SANDBOX_IOKIT_CLIENT']:
    address=d['resolve'](pins['path'],'_'+name);text_address=d['pointer'](address)
    text=d['read'](text_address,128).split(b'\0')[0].decode()
    assert text.startswith('com.apple.app-sandbox.')
    constants[name]=dict(address=hex(address),type='const char* const',text=text)
stub=0x7ff81089aaf0;code=d['read'](stub,6)
assert code[:2]==b'\xff\x25'
target=d['pointer'](stub+6+struct.unpack_from('<i',code,2)[0])
assert target==d['resolve']('/usr/lib/system/libsystem_c.dylib','___strlcpy_chk')
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=pins['path'],provider_sha256=pins['sha256'],
    functions=functions,constants=constants,log=str(log.relative_to(root)),log_sha256=digest(log.read_bytes()),
    policy='Sandbox',issue_opcode=5,consume_opcode=6,release_opcode=7,token_buffer_size=0x3ff0,
    issue_argument_slots=['class pointer','resource type (0=file)','path pointer','uint32 flags in uint64 slot',
                          'token output pointer','signed PID in uint64 slot','PID version in uint64 slot'],
    consume_argument_slots=['token pointer','strlen(token)+1','int64 handle output pointer'],
    release_argument_slots=['int64 handle','zero','zero'],
    target_pid_flag=0x10000,target_pid_version_flag=0x20000,
    unresolved_marker=dict(flag=1,text='invalid',copy='__strlcpy_chk',consume_result=0,grants_access=False),
    execution_report='artifacts/sandbox-source.json',read_only=True,native_macos_kernel_execution=False,
    real_token_grants_implemented=False,
    reference_header='https://github.com/WebKit/WebKit/blob/main/Source/WTF/wtf/spi/darwin/SandboxSPI.h',
    scope='Original user-space ABI and constants only. An issue failure from absent Sandbox policy and the unresolved marker are not capability issuance or enforcement.')
(root/'artifacts/sandbox-extension-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Inspected pinned native sandbox extension ABI:',log)
