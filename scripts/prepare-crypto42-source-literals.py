#!/usr/bin/env python3
"""Match numeric literal blocks from official LibreSSL sources to native code data."""
from pathlib import Path
import hashlib,json,re,struct
root=Path(__file__).resolve().parent.parent
reference_name='artifacts/libressl-assembly-source-reference.json';reference=json.loads((root/reference_name).read_text());source=root/'runtime/libressl-source-reference/libressl-2.6.5/crypto'
native='runtime/fullsystem-libraries/usr/lib/libcrypto.42.dylib';raw=(root/native).read_bytes();cursor=32
for _ in range(struct.unpack_from('<I',raw,16)[0]):
 command,size=struct.unpack_from('<II',raw,cursor)
 if command==0x19:
  if raw[cursor+8:cursor+24].split(b'\0')[0]==b'__TEXT':base=struct.unpack_from('<Q',raw,cursor+24)[0]
  for i in range(struct.unpack_from('<I',raw,cursor+64)[0]):
   at=cursor+72+80*i
   if raw[at:at+16].split(b'\0')[0]==b'__text':vm,length,off=struct.unpack_from('<QQI',raw,at+32);text=raw[off:off+length]
 cursor+=size
specs=[('aes/aes-macosx-x86_64.S','L$AES_Te:',None),('aes/bsaes-macosx-x86_64.S','_bsaes_const:',None),('aes/vpaes-macosx-x86_64.S','_vpaes_consts:',None),('camellia/cmll-macosx-x86_64.S','L$Camellia_SIGMA:','.globl\t_Camellia_cbc_encrypt'),('modes/ghash-macosx-x86_64.S','L$bswap_mask:',None),('sha/sha256-macosx-x86_64.S','K256:',None),('sha/sha512-macosx-x86_64.S','K512:',None),('whrlpool/wp-macosx-x86_64.S','L$table:',None)]
records=[]
for name,anchor,stop in specs:
 path=source/name;relative=str(path.relative_to(root));sha=hashlib.sha256(path.read_bytes()).hexdigest();assert reference['extracted_files'][relative]==sha
 lines=path.read_text().splitlines();first=lines.index(anchor)+1;last=next((i for i in range(first,len(lines)) if stop and lines[i].strip()==stop),len(lines));parts=[];payload=bytearray();begin=first;labels={}
 for i in range(first,last+1):
  line=lines[i].strip() if i<last else ''
  if i==last or line.startswith('.p2align'):
   if payload:parts.append((begin+1,i,bytes(payload),dict(labels)))
   payload=bytearray();labels={};begin=i+1;continue
  if not line:continue
  if re.fullmatch(r'[A-Za-z_.$][\w.$]*:',line):labels[line[:-1]]=len(payload);continue
  match=re.fullmatch(r'\.(byte|value|long|quad)\s+(.+)',line)
  if not match:raise ValueError('Not literal data: '+line)
  width={'byte':1,'value':2,'long':4,'quad':8}[match[1]]
  for token in match[2].split(','):
   if not re.fullmatch(r'\s*(?:0x[0-9a-fA-F]+|[0-9]+)\s*',token):raise ValueError('Not a literal integer')
   payload+=int(token,0).to_bytes(width,'little')
 for begin,end,payload,labels in parts:
  position=text.find(payload)
  if position<0 or text.find(payload,position+1)>=0:raise ValueError('Literal must match native text exactly once: '+name)
  records.append(dict(source=relative,source_sha256=sha,first_line=begin,last_line=end,offset=hex(vm+position-base),length=len(payload),sha256=hashlib.sha256(payload).hexdigest(),labels=labels))
assert len(records)==10 and sum(r['length'] for r in records)==17696
output=root/'runtime/crypto42-assembly-literals/candidate-ranges.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(records,indent=2)+'\n')
# Validate against the reviewed selection instead of silently changing pins.
pins=json.loads((root/'config/cache-image-pins.json').read_text());assert pins['crypto42-device-native']['source_assembly_literals']==records
print('Matched 10 pinned source literal blocks, 17696 bytes; native source file unchanged')
