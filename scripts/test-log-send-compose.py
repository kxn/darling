#!/usr/bin/env python3
"""Check the original Intel wrapper ABI and exercise the real source implementation."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
original='runtime/fullsystem-libraries/usr/lib/system/libsystem_trace.dylib'
assert digest(original)==json.loads((root/'config/cache-image-pins.json').read_text())['native-trace']['sha256']
data=(root/original).read_bytes();at=32;segments=[]
for _ in range(struct.unpack_from('<I',data,16)[0]):
    cmd,length=struct.unpack_from('<II',data,at)
    if cmd==0x19:segments.append(struct.unpack_from('<QQQQ',data,at+24))
    at+=length
start=0x7ff802bcbc62;length=0x153
segment=next(s for s in segments if s[0]<=start and start+length<=s[0]+s[3])
code=data[segment[2]+start-segment[0]:segment[2]+start-segment[0]+length]
cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True;calls=[];rip=[]
for ins in cs.disasm(code,start):
    if ins.mnemonic=='call':
        assert ins.size==5 and ins.operands[0].type==X86_OP_IMM
        calls.append(dict(offset=ins.address-start,target=hex(ins.operands[0].imm)))
    for op in ins.operands:
        if op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP:
            address=ins.address+ins.size+op.mem.disp
            s=next(s for s in segments if s[0]<=address<s[0]+s[3]);assert data[s[2]+address-s[0]]==0
            rip.append(dict(displacement=ins.address-start+ins.disp_offset,next=ins.address-start+ins.size,target=hex(address)))
assert len(calls)==4 and len(rip)==1
assert [c['target'] for c in calls]==['0x7ff802bcd9b0','0x7ff802bb65dd','0x7ff802bcdda0','0x7ff802bcc4a0']
folder=root/'runtime/log-compose-tests';folder.mkdir(exist_ok=True)
header=folder/'native-compose-oracle.h';header.write_text('static const unsigned char native_compose_code[]={'+','.join(hex(b) for b in code)+'};\nstatic const unsigned native_call_sites[]={'+','.join(str(c['offset']) for c in calls)+'};\nstatic const unsigned native_empty_displacement='+str(rip[0]['displacement'])+',native_empty_next='+str(rip[0]['next'])+';\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/log-send-compose.m';obj=folder/'test.o';binary=folder/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/external/libtrace/include'),'-I'+str(folder),'-fblocks','-O0','-Wno-format-zero-length','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem',str(obj),'-undefined','dynamic_lookup','-o',str(binary)],check=True)
m=runpy.run_path(str(root/'scripts/log-compose-runtime-profile.py'));p=m['profile']()
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
result=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=result.stdout+result.stderr
log='logs/log-send-compose-test.log';(root/log).write_text(text)
match=re.search(r'SOURCE_LOG_SEND_COMPOSE_REAL_FORMAT_OWNERSHIP_DELIVERY_OK checks=(\d+) oracle_wrapper_cases=(\d+) sends=(\d+)',text)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=result.returncode,
            source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),
            log=log,log_sha256=digest(log),original=original,original_sha256=digest(original),
            oracle_wrapper_code_sha256=hashlib.sha256(code).hexdigest(),oracle_wrapper_start=hex(start),oracle_wrapper_bytes=length,
            oracle_call_relocations=calls,oracle_data_relocations=rip,oracle_callees_replaced_by_spies=True,
            native_full_logging_backend_executed=False,checks=int(match[1]) if match else 0,oracle_cases=int(match[2]) if match else 0,
            source_log_compose=p['source_log_compose'],runtime_execution_verified=result.returncode==0 and match is not None,full_xcode_build_ready=False)
(root/'artifacts/log-send-compose-test.json').write_text(json.dumps(report,indent=2)+'\n');print(result.returncode,text[-6000:]);assert report['runtime_execution_verified']
