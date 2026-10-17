#!/usr/bin/env python3
"""Pin original registration, message, fault and real XCTest consumer evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/usr/lib/system/libsystem_trace.dylib';cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
records=[];lines=[]
for name,a,n in [
 ('os_log_set_hook',m['resolve'](provider,'_os_log_set_hook'),10),
 ('registration_body',0x7ff802bcaf16,186),
 ('os_log_get_type',m['resolve'](provider,'_os_log_get_type'),5),
 ('os_log_set_fault_callback',m['resolve'](provider,'_os_log_set_fault_callback'),24),
 ('fault_info_builder',0x7ff802bcbabe,188),
 ('native_hook_message_and_invoke',0x7ff802bb8b44,691)]:
 code=m['read'](a,n);instructions=list(cs.disasm(code,a))
 lines.append(name+'\n'+'\n'.join(f'{i.address:#x} {i.mnemonic} {i.op_str}' for i in instructions))
 records.append(dict(name=name,address=hex(a),length=n,sha256=hashlib.sha256(code).hexdigest()))
 if name=='os_log_get_type':assert code.hex()=='0fb64701c3'
 if name=='os_log_set_fault_callback':
  i=next(i for i in instructions if i.mnemonic=='xchg');op=i.operands[0];assert op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP
  slot=i.address+i.size+op.mem.disp;default=m['pointer'](slot);assert default==m['resolve'](provider,'_os_log_fault_default_callback') and m['read'](default,1)==b'\xc3'
i=next(cs.disasm(m['read'](0x7ff802bcaf3d,8),0x7ff802bcaf3d));op=i.operands[1];level_slot=i.address+i.size+op.mem.disp;assert m['read'](level_slot,1)==b'\x11'
client='runtime/state/prefix/Applications/Xcode.app/Contents/SharedFrameworks/XCTestCore.framework/Versions/A/XCTestCore'
all_text=subprocess.check_output(['llvm-objdump-19','--macho','--arch=x86_64','--disassemble',str(root/client)],text=True).splitlines()
selected=set()
for index,line in enumerate(all_text):
 if any(s in line for s in ['symbol stub for: _os_log_set_hook','symbol stub for: _os_log_get_type','symbol stub for: _os_log_set_fault_callback']):selected.update(range(max(0,index-20),min(len(all_text),index+30)))
start=next(i for i,line in enumerate(all_text) if line=='_runtime_issue_os_log_fault_callback:');end=next(i for i in range(start+1,len(all_text)) if all_text[i].startswith('-['));selected.update(range(start,end))
client_log='logs/xctestcore-log-hook-callers.log';(root/client_log).write_text('\n'.join(all_text[i] for i in sorted(selected))+'\n')
text=(root/client_log).read_text();assert '0x80(%rbx)' in text and '0x28(%r14)' in text and '0x20(%r14)' in text
log='logs/log-hooks-native-abi.log';(root/log).write_text('\n\n'.join(lines)+'\n')
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
ref=json.loads((root/'vendor/webkit-oslog-reference/reference.json').read_text());assert digest('vendor/webkit-oslog-reference/OSLogSPI.h')==ref['sha256']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=digest('runtime/fullsystem-libraries'+provider),functions=records,native_initial_minimum_level=17,
 native_default_fault_callback_is_single_ret=True,client=client,client_sha256=digest(client),client_log=client_log,client_log_sha256=digest(client_log),
 log=log,log_sha256=digest(log),public_declaration_reference=ref,
 scope='Source Block copy/exchange and minimum-level behavior follow the original Intel implementation; message fields agree with primary WebKit declarations and real XCTestCore consumers. Fault records include the actual formatted message and source caller PC. Opaque trace metadata, stackshots and unified logd service are not implemented by this change.')
(root/'artifacts/log-hooks-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n');print('Pinned original hook ABI, initial level, fault callback and real XCTestCore consumers')
