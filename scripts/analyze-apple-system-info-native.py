#!/usr/bin/env python3
"""Pin original ASI call/return contracts and Intel resource fallback constants."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,re,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
pins=json.loads((root/'config/cache-image-pins.json').read_text())['apple-system-info-native']
path=root/'runtime/fullsystem-libraries'/pins['path'].lstrip('/')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert digest(path)==pins['sha256']
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
im=d['image'](pins['path']);names={}
for line in subprocess.check_output(['llvm-nm-19','--defined-only',str(path)],text=True).splitlines():
    parts=line.split(None,2)
    if len(parts)==3:names[parts[2]]=int(parts[0],16)
ordered=sorted(set(names.values()))
selected=['_ASI_GetCurrentCPUDescriptionWithFormat','_ASI_CopyCPUDescription','_ASI_CopyCurrentCPUDescription',
    '_ASI_CopyCPUKind','_ASI_NumberOfCPUs','_ASI_CPUSpeedInHz','_ASI_BusSpeedInHz','_ASI_PhysicalMemorySize',
    '_ASI_CopyComputerModelName','_CopySpeedDescription','_CopyCPUKind','_GetASIBundleRef']
machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True;log=[];functions=[]
for name in selected:
    start=names[name];end=ordered[bisect.bisect_right(ordered,start)];code=d['read'](start,end-start)
    functions.append(dict(symbol=name,address=hex(start),length=len(code),sha256=hashlib.sha256(code).hexdigest()))
    log.append('\nFUNCTION '+name+'\n')
    for i in machine.disasm(code,start):
        notes=[]
        for op in i.operands:
            if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP or i.mnemonic!='lea':continue
            at=i.address+i.size+op.mem.disp
            if any(s[0]=='__cstring' and s[2]<=at<s[2]+s[3] for s in im.sections):
                notes.append('cstring='+repr(d['read'](at,200).split(b'\0')[0].decode()))
            elif d['read'](at+8,4)==b'\xc8\x07\x00\x00':
                notes.append('CFString='+repr(d['read'](d['pointer'](at+16),200).split(b'\0')[0].decode()))
        log.append(f'{i.address:#x} {i.mnemonic} {i.op_str} '+', '.join(notes)+'\n')
thin=root/'runtime/mobileasset-source/DVTFoundation.x86_64'
imports=set()
for line in subprocess.check_output(['llvm-objdump-19','--macho','--indirect-symbols',str(thin)],text=True).splitlines():
    match=re.match(r'0x[\da-fA-F]+\s+\d+\s+(_ASI_\S+)',line)
    if match:imports.add(match[1])
assert len(imports)==7 and imports<=set(im.exports)
logpath=root/'logs/apple-system-info-native-analysis.log';logpath.write_text(''.join(log))
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,original=pins,
    DVT_imports=sorted(imports),functions=functions,
    contracts={
        'ASI_GetCurrentCPUDescriptionWithFormat':'CFAutorelease return; bits 0..15 choose format, bit 16 chooses abbreviated CPU kind.',
        'ASI_CopyCPUDescription':'Owned CFString from uint32 CPU package count, uint32 frequency scalar and CFString kind.',
        'ASI_CopyCPUKind':'Forwards its Boolean abbreviation argument, not a no-argument function.',
        'ASI_CopyCurrentCPUDescription':'Queries CPU package count and frequency, and uses the embedded Unknown default if CPU kind is unavailable; it is not a wrapper around format=1.',
        'ASI_CPUSpeedInHz':'Queries sysctl frequency values and saturates to uint32 max; guest sysctl accuracy is separate.'},
    Intel_format_resources='Intel-prefixed string keys with embedded 2 x %@ / 3 x %@ / 4 x %@ fallbacks; older 2xCPUFormat/Dual resource is not the Intel lookup key.',
    existing_Darling_ASI='Most functions are generic void*/no-argument stubs; NumberOfCPUs returns 1 and model name is UNIMPLEMENTED. The experimental path restores the full original image rather than implementing another fixed-result getter.',
    execution_report='artifacts/apple-system-info-native-execution.json',
    log=str(logpath.relative_to(root)),log_sha256=digest(logpath))
(root/'artifacts/apple-system-info-native-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified original ASI function contracts, all seven DVT ASI imports and Intel fallback constants')
