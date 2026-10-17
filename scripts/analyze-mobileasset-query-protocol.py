#!/usr/bin/env python3
"""Inspect Intel query wire schema, callbacks and result-code tables."""
from pathlib import Path
import bisect,hashlib,json,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_OP_IMM,X86_REG_RIP
runpy.run_path(str(root/'scripts/analyze-logging-stream-native.py'),init_globals={'ANALYSIS_PROVIDER':'/System/Library/PrivateFrameworks/MobileAsset.framework/Versions/A/MobileAsset','ANALYSIS_CLASS_NAMES':['MAAssetQuery'],'ANALYSIS_PREFIX':'mobileasset-query','ANALYSIS_NOTE':'Original query metadata; completion and daemon behavior need separate execution tests.'})
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
read,pointer=d['read'],d['pointer'];provider='/System/Library/PrivateFrameworks/MobileAsset.framework/Versions/A/MobileAsset';im=d['image'](provider);path=root/'runtime/fullsystem-libraries'/provider.lstrip('/')
names={}
for line in subprocess.check_output(['llvm-nm-19','--defined-only',str(path)],text=True).splitlines():
 f=line.split(None,2)
 if len(f)==3:names[f[2]]=int(f[0],16)
inverse={v:k for k,v in names.items()};starts=sorted(set(names.values()));machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True
wanted=['_stringForMAAssetState','-[MAAsset initWithAttributes:]','-[MAAsset getLocalFilePath]','-[MAAsset getLocalFileUrl]','-[MAAsset wasLocal]','-[MAAsset wasPreinstalled]','-[MAAsset wasPurgeable]','-[MAXpcManager sendAsync:clientHandler:taskDescriptor:]','_isQueryResultFailure','__getClientCallbackQueue','____MAsendQueryMetaData_block_invoke','-[MAAssetQuery queryMetaDataSync]','___30-[MAAssetQuery queryMetaData:]_block_invoke','___39-[MAAssetQuery queryMetaDataWithError:]_block_invoke','_stringForMAQueryResult','_errorStringForMAQueryResult','_stringForMAQueryReturnTypes','-[MAAssetQuery addKeyValuePair:with:]','-[MAAssetQuery addKeyValueArray:with:]','-[MAAssetQuery addKeyValueNull:]','-[MAAssetQuery getResultsFromMessage:]']
# Include the real async helper reached by both query wrappers.
extra=[0x7ff8177b005d]
log=[];records=[]
for start in sorted({names[n] for n in wanted if n in names}|set(extra)):
 end=starts[bisect.bisect_right(starts,start)];code=read(start,end-start);log.append('\nFUNCTION '+inverse.get(start,hex(start))+'\n');records.append(dict(name=inverse.get(start),address=hex(start),length=len(code),sha256=hashlib.sha256(code).hexdigest()))
 for i in machine.disasm(code,start):
  notes=[]
  for o in i.operands:
   at=None
   if o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP:at=i.address+i.size+o.mem.disp
   elif o.type==X86_OP_IMM and i.mnemonic in ['call','jmp']:
    target=o.imm
    if target in inverse:notes.append(inverse[target])
    # Cache symbol stubs resolve via their RIP-relative GOT pointer.
    try:
     stub=next(machine.disasm(read(target,6),target))
     if stub.mnemonic=='jmp' and stub.operands[0].type==X86_OP_MEM and stub.operands[0].mem.base==X86_REG_RIP:
      dest=pointer(stub.address+stub.size+stub.operands[0].mem.disp)
      for dep in im.dependencies:
       for n,v in d['image'](dep).exports.items():
        if v[0]=='address' and v[1]==dest:notes.append(n)
    except (ValueError,StopIteration):pass
   if at is None:continue
   sec=next((s for s in im.sections if s[2]<=at<s[2]+s[3]),None)
   try:
    if sec and sec[0]=='__cstring':notes.append(repr(read(at,400).split(b'\0')[0].decode()))
    elif sec and sec[0]=='__cfstring':notes.append('CFString='+repr(read(pointer(at+16),400).split(b'\0')[0].decode()))
    elif sec and sec[0]=='__objc_selrefs':notes.append('SEL='+repr(read(pointer(at),400).split(b'\0')[0].decode()))
    elif at in inverse:notes.append(inverse[at])
   except (ValueError,UnicodeDecodeError):pass
  log.append(f'{i.address:#x} {i.mnemonic} {i.op_str} '+ '; '.join(notes)+'\n')
state_instructions=list(machine.disasm(read(names['_stringForMAAssetState'],60),names['_stringForMAAssetState']))
state_lea=next(i for i in state_instructions if i.mnemonic=='lea' and any(o.type==X86_OP_MEM and o.mem.base==X86_REG_RIP for o in i.operands))
state_address=state_lea.address+state_lea.size+state_lea.operands[1].mem.disp
tables={}
for label,address,count in [('results',0x7ff8177c378a+0x2ab44d26,15),('returns',0x7ff8177c37d5+0x2ab44d53,7),('states',state_address,7)]:
 tables[label]=[]
 for i in range(count):
  value=pointer(address+8*i)
  tables[label].append(dict(code=i,pointer=hex(value),value=(read(pointer(value+16),300).split(b'\0')[0].decode() if value<0x8000000000000000 else 'tagged NSString')))
log.append('\nTABLES '+json.dumps(tables,indent=2)+'\n')
output=root/'logs/mobileasset-query-protocol-native.log';output.write_text(''.join(log));digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(root/'artifacts/mobileasset-query-protocol-native.json').write_text(json.dumps(dict(provider=str(path.relative_to(root)),provider_sha256=digest(path),functions=records,log=str(output.relative_to(root)),log_sha256=digest(output),native_execution=False),indent=2)+'\n')
print('Recorded',len(records),'query functions')
