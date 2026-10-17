#!/usr/bin/env python3
"""Check real source-matched tables and reject damaged/ambiguous/code inputs."""
from pathlib import Path
import copy,hashlib,json,runpy,struct
root=Path(__file__).resolve().parent.parent
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
source=root/'runtime/fullsystem-libraries/usr/lib/libcrypto.42.dylib';obj=ns['image']('/usr/lib/libcrypto.42.dylib');base=next(s[1] for s in obj.segments if s[0]=='__TEXT');text=next(s for s in obj.sections if s[0]=='__text')
a=runpy.run_path(str(root/'scripts/cache-code-analysis.py'));functions=a['reference_with_function_labels'](source,root/'runtime/crypto42-assembly-literals/analysis-only.macho');module=runpy.run_path(str(root/'scripts/source-assembly-literals.py'));records=json.loads((root/'runtime/crypto42-assembly-literals/candidate-ranges.json').read_text());disassembly=(root/'runtime/rebuilt-crypto42-device-native/original-disassembly.log').read_text();read=ns['read']
def validate(d=disassembly,r=records,reader=read,f=functions):return module['validate'](d,r,base,reader,f,source,root)
result=validate();assert len(result)==10 and sum(r['end']-r['start'] for r in result)==17696
negative=[]
def reject(name,call,message):
 try:call()
 except ValueError as error:
  assert message in str(error),(name,str(error));negative.append(dict(name=name,reason=str(error)));return
 raise AssertionError('Accepted invalid literal input: '+name)
start=result[0]['start'];original_read=read
def corrupt(address,length):
 data=bytearray(original_read(address,length))
 if address<=start<address+length:data[start-address]^=1
 return bytes(data)
reject('damaged native literal byte',lambda:validate(reader=corrupt),'Native bytes differ')
changed=copy.deepcopy(records);changed[0]['offset']=hex(int(changed[0]['offset'],0)+1)
reject('shifted native extent',lambda:validate(r=changed),'Native bytes differ')
changed=copy.deepcopy(records);changed[0]['source_sha256']='0'*64
reject('changed upstream source',lambda:validate(r=changed),'Upstream assembly source changed')
fixture=root/'runtime/crypto42-assembly-literals/not-literal.S';lines=(root/records[0]['source']).read_text().splitlines();lines[records[0]['first_line']-1]='nop';fixture.write_text('\n'.join(lines)+'\n');changed=copy.deepcopy(records);changed[0]['source']=str(fixture.relative_to(root));changed[0]['source_sha256']=hashlib.sha256(fixture.read_bytes()).hexdigest()
reject('instruction in claimed source literal slice',lambda:validate(r=changed),'other than literal data')
reject('unexplained native function entry in data',lambda:validate(f=functions+[start+1]),'Unexplained function entry')
address=text[2];encoded=b'\xe9'+struct.pack('<i',start-address-5);branch=f"{address:x}: {' '.join(f'{b:02x}' for b in encoded)} \tjmpq\t0x{start:x}\n"
reject('direct branch into literal data',lambda:validate(d=disassembly+'\n'+branch),'Direct code branch')
encoded=b'\x48\x89\x05'+struct.pack('<i',start-address-7);store=f"{address:x}: {' '.join(f'{b:02x}' for b in encoded)} \tmovq\t%rax, {start-address-7}(%rip)\n"
reject('code writes to literal data',lambda:validate(d=disassembly+'\n'+store),'not an in-bounds data read')
reject('missing native data readers',lambda:validate(d=''),'no native data reader')
def duplicate(address,length):
 data=bytearray(original_read(address,length))
 if address==text[2] and length==text[3]:
  payload=original_read(start,result[0]['end']-start);data[:len(payload)]=payload
 return bytes(data)
reject('ambiguous second matching literal block',lambda:validate(reader=duplicate),'not unique')
# Inspect actual emitted Mach-O bytes: literal data must not be rewritten.
binary=root/'runtime/rebuilt-crypto42-device-native/libcrypto.42.dylib';raw=binary.read_bytes();cursor=32;segments=[]
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 command,size=struct.unpack_from('<II',raw,cursor)
 if command==0x19:
  vm,length,off,filesize=struct.unpack_from('<QQQQ',raw,cursor+24);segments.append((vm,length,off,filesize))
 cursor+=size
for region in result:
 at=region['start']-base;n=region['end']-region['start'];segment=next(s for s in segments if s[0]<=at<at+n<=s[0]+s[3]);off=segment[2]+at-segment[0];assert raw[off:off+n]==read(region['start'],n)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(literal_regions=len(result),literal_bytes=17696,native_data_readers=sum(len(r['readers']) for r in result),valid_native_data_symbols=sum(len(r['source_data_entries']) for r in result),rejections=negative,analysis=result,all_emitted_literal_bytes_unchanged=True,binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),validator='scripts/source-assembly-literals.py',validator_sha256=digest('scripts/source-assembly-literals.py'),source='scripts/test-source-assembly-literals.py',source_sha256=digest('scripts/test-source-assembly-literals.py'),scope='Pinned upstream literal/data classification and real native references, not universal control-flow proof')
(root/'artifacts/crypto42-source-literal-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Validated 10 source literal blocks / 17696 bytes,',len(negative),'negative controls; emitted literal bytes unchanged')
