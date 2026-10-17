#!/usr/bin/env python3
"""Record the original message ABI and remaining native logging contracts."""
from pathlib import Path
from datetime import datetime,timezone
from bisect import bisect_right
import hashlib,json,runpy,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
m=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
provider='/usr/lib/system/libsystem_trace.dylib';source=root/'runtime/fullsystem-libraries'/provider.lstrip('/')
build=root/'runtime/native-log-message';build.mkdir(parents=True,exist_ok=True)
starts=runpy.run_path(str(root/'scripts/cache-code-analysis.py'))['reference_with_function_labels'](source,build/'trace.analysis-only.macho')
cs=Cs(CS_ARCH_X86,CS_MODE_64);records=[];lines=[]
names=['_os_log_copy_message_string','_os_log_get_type','_os_log_set_hook','_os_log_set_fault_callback']
addresses=[(s,m['resolve'](provider,s)) for s in names]+[('native-message-buffer-parser',0x7ff802bc8722),('native-hook-registration-body',0x7ff802bcaf16)]
for symbol,a in addresses:
 i=bisect_right(starts,a)-1;assert starts[i]==a
 length=starts[i+1]-a;code=m['read'](a,length);instructions=list(cs.disasm(code,a))
 records.append(dict(symbol=symbol,address=hex(a),length=length,sha256=hashlib.sha256(code).hexdigest()))
 lines.append(symbol+'\n'+'\n'.join(f'{i.address:#x} {i.mnemonic} {i.op_str}' for i in instructions))
 if symbol=='_os_log_copy_message_string':
  text='\n'.join(i.op_str for i in instructions)
  for offset in ['0x50','0x58','0x60','0x68','0x70','0x78']:assert offset in text
log='logs/native-log-message-abi.log';(root/log).write_text('\n\n'.join(lines)+'\n')
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),provider=provider,provider_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),functions=records,
 message_offsets=dict(flags=0x50,format=0x58,public_payload=0x60,public_size=0x68,private_payload=0x70,private_size=0x78),
 log=log,log_sha256=digest(log),scope='Original function boundaries, formatter message layout and hook registration code. No claim of an implemented Darling logging hook or fault callback; those contracts require real event delivery and ownership integration.')
(root/'artifacts/native-log-message-analysis.json').write_text(json.dumps(record,indent=2)+'\n');print('Recorded exact native log-message layout and remaining hook contracts')
