#!/usr/bin/env python3
"""Record actual Intel Pallas ABI, XPC schema, response and client-name paths."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/System/Library/PrivateFrameworks/MobileAsset.framework/Versions/A/MobileAsset'
path=root/'runtime/fullsystem-libraries'/provider.lstrip('/');im=d['image'](provider)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(path)=='50f840c3ea81c25e8270e45fd654bc5e39eabd3be98e7336a399f2e8dc340085'
listing=subprocess.check_output(['llvm-nm-19','--defined-only',str(path)],text=True)
names={line.split()[-1]:int(line.split()[0],16) for line in listing.splitlines() if len(line.split())==3}
symbols=['_MAGetPallasEnabled','__MAsendGetPallasEnabled',
    '_MAGetPallasAudience','__MAsendGetPallasAudience',
    '_MASetPallasEnabled','__MAsendSetPallasEnabled',
    '_MASetPallasAudience','_MASetPallasAudienceForType','__MAsendSetPallasAudience',
    '_MASetPallasUrl','_MASetPallasUrlForType','__MAsendSetPallasUrl','__MAsendSetPallasUrlForType',
    '-[MAXpcManager sendSync:gettingResponseCode:codeForXpcError:loggingName:]',
    '___73-[MAXpcManager sendSync:gettingResponseCode:codeForXpcError:loggingName:]_block_invoke',
    '+[MAAsset getClientIdentifierForSelf]','-[MAXpcConnection initWithServiceName:]']
# Objective-C nm symbols contain spaces; parse the complete name after its type.
for line in listing.splitlines():
    fields=line.split(None,2)
    if len(fields)==3:names[fields[2]]=int(fields[0],16)
cursor=im.base+32;starts=[]
for _ in range(struct.unpack_from('<I',d['read'](im.base,32),16)[0]):
    command,size=struct.unpack('<II',d['read'](cursor,8))
    if command==0x26:off,length=struct.unpack('<II',d['read'](cursor+8,8))
    cursor+=size
link=next(s for s in im.segments if s[0]=='__LINKEDIT');address=im.base;value=shift=0
for byte in d['read'](link[1]+off-link[3],length):
    value|=(byte&127)<<shift
    if byte<128:
        if not value:break
        address+=value;starts.append(address);value=shift=0
    else:shift+=7
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True
functions=[];log=[]
for symbol in symbols:
    address=names[symbol];assert address in starts
    end=starts[starts.index(address)+1];code=d['read'](address,end-address)
    functions.append(dict(symbol=symbol,address=hex(address),length=len(code),sha256=hashlib.sha256(code).hexdigest()))
    log.append('\nFUNCTION '+symbol+'\n')
    for i in machine.disasm(code,address):
        notes=[]
        for operand in i.operands:
            if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP and i.mnemonic=='lea':
                at=i.address+i.size+operand.mem.disp
                if any(s[0]=='__cstring' and s[2]<=at<s[2]+s[3] for s in im.sections):
                    notes.append('cstring='+repr(d['read'](at,200).split(b'\0')[0].decode()))
                elif any(s[0]=='__cfstring' and s[2]<=at<s[2]+s[3] for s in im.sections):
                    if d['read'](at+8,4)==b'\xc8\x07\x00\x00':
                        notes.append('CFString='+repr(d['read'](d['pointer'](at+16),200).split(b'\0')[0].decode()))
        log.append(f'{i.address:#x} {i.mnemonic} {i.op_str} '+', '.join(notes)+'\n')
strings={}
for at,value in {0x7ff8178559c9:'com.apple.mobileassetd.v2',0x7ff8178559e3:'AssetType',
        0x7ff8178559ed:'messageAction',0x7ff817855ac9:'pallasEnabled',
        0x7ff8178561b1:'clientName',0x7ff81785f26d:'connectionIdentifier',
        0x7ff81785f282:'requestType',0x7ff81785f28e:'requestTypeSync',0x7ff817855a95:'Result'}.items():
    assert d['read'](at,len(value)+1)==value.encode()+b'\0',(hex(at),value)
    strings[value]=hex(at)
wrapper=list(machine.disasm(d['read'](names['_MAGetPallasEnabled'],38),names['_MAGetPallasEnabled']))
assert any(i.mnemonic=='call' and i.operands[0].type==X86_OP_IMM and i.operands[0].imm==names['__MAsendGetPallasEnabled'] for i in wrapper)
body=list(machine.disasm(d['read'](names['__MAsendGetPallasEnabled'],320),names['__MAsendGetPallasEnabled']))
assert any(i.mnemonic=='mov' and i.op_str=='edx, 0x20' for i in body)
assert any(i.mnemonic=='mov' and i.op_str=='r8d, 1' for i in body)
operations={
    '__MAsendGetPallasEnabled':32,'__MAsendSetPallasEnabled':33,
    '__MAsendGetPallasAudience':20,'__MAsendSetPallasAudience':10,
    '__MAsendSetPallasUrlForType':9}
for symbol,action in operations.items():
    record=next(f for f in functions if f['symbol']==symbol)
    instructions=list(machine.disasm(d['read'](names[symbol],record['length']),names[symbol]))
    assert any(i.mnemonic=='mov' and i.op_str==f'edx, {hex(action) if action>=10 else action}' for i in instructions),(symbol,action)
logpath=root/'logs/mobileasset-pallas-native-analysis.log';logpath.write_text(''.join(log))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=digest(path),
    native_execution=False,functions=functions,protocol_strings=strings,
    public_signature='int64_t MAGetPallasEnabled(NSString *assetType, bool *enabled)',
    request_action_signed_int64=32,response_code_signed_int64_key='Result',response_bool_key='pallasEnabled',
    response_bool_written_only_on_success=True,output_initialized_false_by_internal_getter=True,
    xpc_error_response_code=1,allocation_error_response_code=1,
    operations=operations,
    additional_public_signatures={
        'MAGetPallasAudience':'NSString * (NSString *assetType); autoreleased return, nil on service failure',
        'MASetPallasEnabled':'int64_t (NSString *assetType, 8-bit enabled); public wrapper normalizes any nonzero input',
        'MASetPallasAudienceForType':'int64_t (NSString *audience, NSString *assetType)',
        'MASetPallasUrlForType':'int64_t (NSURL *url, NSString *assetType)'},
    audience_getter_allocation_failure_empty_string=True,
    audience_setter_non_nil_non_string_error=1,
    url_setter_non_nil_non_NSURL_error=5,url_nil_sets_boolean='serverOverrideClear',
    audience_nil_omits_key='pallasAudience',url_payload_key='pallasUrl',audience_payload_key='pallasAudience',
    client_name='main bundle identifier, otherwise NSString %s/getprogname(), otherwise UnknownClient',
    notes=['Public return value is a status code, not the enabled flag.',
        'Internal MAXpcManager is present in class-list metadata but is not an exported class.',
        'Native synchronous manager retries one interrupted connection; other errors retain codeForXpcError=1.',
        'This is static evidence. The actual Apple mobileassetd daemon is not running or emulated by these analyses.'],
    log=str(logpath.relative_to(root)),log_sha256=digest(logpath))
(root/'artifacts/mobileasset-pallas-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Recorded all five DVT MobileAsset Pallas ABI and native XPC operation codes')
