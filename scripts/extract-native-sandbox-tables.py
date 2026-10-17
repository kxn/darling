#!/usr/bin/env python3
"""Extract operation/filter/enum identities from the pinned original compiler."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
root=Path(__file__).resolve().parent.parent
path='runtime/rebuilt-sandbox-compiler-native/libsandbox.1.dylib';b=(root/path).read_bytes();reference=json.loads((root/'runtime/rebuilt-sandbox-compiler-native/reconstruction.json').read_text());assert hashlib.sha256(b).hexdigest()==reference['staged_image_sha256']
segments=[];at=32
for _ in range(struct.unpack_from('<I',b,16)[0]):
    c,n=struct.unpack_from('<II',b,at)
    if c==0x19:
        vm,vs,off,fs=struct.unpack_from('<QQQQ',b,at+24);segments.append((vm,vm+fs,off))
    at+=n
def offset(address):
    for lo,hi,off in segments:
        if lo<=address<hi:return off+address-lo
    raise ValueError('Address not backed by file bytes: '+hex(address))
def string(address):
    off=offset(address);end=b.index(0,off);s=b[off:end].decode();assert len(s)<512 and all(32<=ord(c)<127 for c in s);return s
symbols={m[2]:int(m[1],16) for m in re.finditer(r'^([0-9a-f]+)\s+\S\s+(.+)$',subprocess.check_output(['llvm-nm-19','-an',str(root/path)],text=True),re.M)}
header=(root/'runtime/sandbox-policy-dump/coreservicesd.bin').read_bytes();count=header[4];assert count==198
names=[string(struct.unpack_from('<Q',b,offset(symbols['_operation_names']+i*8))[0]) for i in range(count)];assert len(set(names))==count and names[0]=='default'
filters={}
for i in range(106):
    off=offset(symbols['_filter_info']+i*32);name,category=struct.unpack_from('<QQ',b,off)
    if not name:continue
    enum_pointer=struct.unpack_from('<Q',b,off+24)[0];enums=[]
    if enum_pointer:
        for j in range(1024):
            p,v=struct.unpack_from('<QQ',b,offset(enum_pointer+j*16))
            if not p:break
            enums.append(dict(name=string(p),value=v&65535,metadata=v>>16))
        else:raise ValueError('Unterminated native enum table')
    filters[str(i)]=dict(name=string(name),category=string(category),type=b[off+16],enums=enums)
assert filters['26']['name']=='system-attribute'
assert next(v['value'] for v in filters['26']['enums'] if v['name']=='apple-internal')==0
assert next(v['value'] for v in filters['26']['enums'] if v['name']=='sandbox-debug-mode')==1
assert next(v['value'] for v in filters['43']['enums'] if v['name']=='is-initproc')==3
include='// Intel macOS 26.6 operation order, extracted from the pinned original compiler.\n'+''.join('    '+json.dumps(n)+',\n' for n in names)
assert (root/'vendor/darlingserver/src/sandbox-operation-names.inc').read_text()==include
record=dict(image=path,image_sha256=hashlib.sha256(b).hexdigest(),original_image_sha256=reference['original_image_sha256'],operation_names=names,filters=filters,third_party_decompiler_system_attribute_26_debug_mode_label_is_incomplete=True,layout='Native operation_names array; 32-byte filter_info records; name/u64 enum entries, ordinal in low 16 bits and compiler metadata above it.')
(root/'artifacts/native-sandbox-tables.json').write_text(json.dumps(record,indent=2)+'\n');print('Verified',len(names),'operations and',len(filters),'native filter records')
