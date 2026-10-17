#!/usr/bin/env python3
"""Expose four existing hidden NSXPC class symbols in a staged Darling FND.

Preserves every existing export payload, all class metadata, and instruction
bytes. Only a fresh export trie and __LINKEDIT/header sizes are emitted. The
installed runtime remains untouched; this stage supports x86_64 only.
"""
from pathlib import Path
import hashlib
import json
import struct
from datetime import datetime, timezone

root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/foundation-xpc-exports.json').read_text())
original=(root/config['source']).read_bytes()
if hashlib.sha256(original).hexdigest()!=config['source_sha256']:
    raise ValueError('Changed original Darling FND; re-review hidden exports')
data=original
if data[:4]==b'\xca\xfe\xba\xbe':
    for index in range(struct.unpack_from('>I',data,4)[0]):
        cpu,subtype,off,size,align=struct.unpack_from('>5I',data,8+20*index)
        if cpu==0x1000007:
            data=data[off:off+size];break
    else:raise ValueError('Missing x86_64 source slice')
if data[:4]!=b'\xcf\xfa\xed\xfe' or struct.unpack_from('<I',data,4)[0]!=0x1000007:
    raise ValueError('Unsupported source Mach-O')
binary=bytearray(data)

def uleb(value):
    result=bytearray()
    while value>=128:result.append((value&127)|128);value>>=7
    return bytes(result+bytes([value]))

def read_uleb(data,at):
    value=shift=0
    while True:
        byte=data[at];at+=1;value|=(byte&127)<<shift
        if byte<128:return value,at
        shift+=7
        if shift>63:raise ValueError('Invalid ULEB128')

at=32; export_command=None; text_base=None; instruction_ranges=[];install_name=None
for _ in range(struct.unpack_from('<I',data,16)[0]):
    cmd,size=struct.unpack_from('<II',data,at)
    if cmd==0x19:
        name=data[at+8:at+24].split(b'\0')[0]
        if name==b'__TEXT':text_base=struct.unpack_from('<Q',data,at+24)[0]
        if name==b'__LINKEDIT':linkedit=at
        for i in range(struct.unpack_from('<I',data,at+64)[0]):
            section=at+72+80*i
            if struct.unpack_from('<I',data,section+64)[0]&0x80000400:
                off=struct.unpack_from('<I',data,section+48)[0];length=struct.unpack_from('<Q',data,section+40)[0]
                instruction_ranges.append((off,length))
    elif cmd==2:symoff,count,stroff,strsize=struct.unpack_from('<4I',data,at+8)
    elif cmd in (0x22,0x80000022):export_command=at+40
    elif cmd==0x80000033:export_command=at+8
    elif cmd==0xd:
        start=at+struct.unpack_from('<I',data,at+8)[0];install_name=data[start:data.index(0,start)].decode()
    elif cmd==0x1d:raise ValueError('Unexpected signed Darling image; do not emit a stale signature')
    at+=size
assert text_base is not None and export_command is not None and install_name=='/usr/lib/libFND.dylib'
symbols={}
for i in range(count):
    name_at,kind,section,desc,value=struct.unpack_from('<IBBHQ',data,symoff+16*i)
    start=stroff+name_at; name=data[start:data.index(0,start)].decode()
    if name in config['symbols']:
        if kind&0xe!=0xe or value<text_base or name in symbols:raise ValueError('Invalid hidden class definition')
        symbols[name]=value
assert set(symbols)==set(config['symbols'])
off,size=struct.unpack_from('<II',data,export_command);trie=data[off:off+size];exports={}
def visit(at,prefix=b''):
    length,cursor=read_uleb(trie,at)
    if length:exports[prefix]=trie[cursor:cursor+length]
    cursor+=length;children=trie[cursor];cursor+=1
    for _ in range(children):
        end=trie.index(0,cursor);edge=trie[cursor:end];child,cursor=read_uleb(trie,end+1)
        visit(child,prefix+edge)
visit(0);original_exports=dict(exports)
for name,address in symbols.items():
    if name.encode() in exports:raise ValueError('Expected a hidden class, found an existing export')
    exports[name.encode()]=uleb(0)+uleb(address-text_base)
nodes=[]
def node(items,prefix):
    result={'terminal':exports.get(prefix,b''),'children':[],'offset':0};nodes.append(result)
    remaining=[name for name in items if name!=prefix]
    for first in sorted(set(name[len(prefix)] for name in remaining)):
        group=[name for name in remaining if name[len(prefix)]==first];common=group[0]
        for name in group[1:]:
            i=len(prefix)
            while i<min(len(common),len(name)) and common[i]==name[i]:i+=1
            common=common[:i]
        result['children'].append((common[len(prefix):],node(group,common)))
    return result
node(list(exports),b'')
def encode(node):
    result=uleb(len(node['terminal']))+node['terminal']+bytes([len(node['children'])])
    return result+b''.join(edge+b'\0'+uleb(child['offset']) for edge,child in node['children'])
for _ in range(100):
    cursor=0;changed=False
    for item in nodes:
        changed|=item['offset']!=cursor;item['offset']=cursor;cursor+=len(encode(item))
    if not changed:break
else:raise ValueError('Export trie did not converge')
fresh=b''.join(encode(item) for item in nodes)
binary.extend(bytes(-len(binary)%8));offset=len(binary);binary.extend(fresh)
struct.pack_into('<II',binary,export_command,offset,len(fresh))
fileoff=struct.unpack_from('<Q',binary,linkedit+40)[0];filesize=len(binary)-fileoff
struct.pack_into('<Q',binary,linkedit+48,filesize)
struct.pack_into('<Q',binary,linkedit+32,(filesize+4095)&~4095)
for off,length in instruction_ranges:
    assert binary[off:off+length]==data[off:off+length]
allowed=set(range(export_command,export_command+8))|set(range(linkedit+32,linkedit+40))|set(range(linkedit+48,linkedit+56))
assert all(before==after or index in allowed for index,(before,after) in enumerate(zip(data,binary)))
trie=fresh;exports={};visit(0)
assert all(exports.get(name)==payload for name,payload in original_exports.items())
assert set(exports)==set(original_exports)|{n.encode() for n in symbols}
destination=root/'runtime/native-library-stage/libFND.dylib';temporary=destination.with_name(destination.name+'.pending')
temporary.write_bytes(binary);temporary.replace(destination)
report={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
    'source':config,'source_x86_64_sha256':hashlib.sha256(data).hexdigest(),
    'staged_sha256':hashlib.sha256(binary).hexdigest(),'original_exports_preserved':len(original_exports),
    'added_exports':symbols,'instruction_bytes_unchanged':True,
    'original_bytes_outside_load_command_updates_unchanged':True,
    'execution_verified':False,'full_compatibility':False}
(root/'artifacts/foundation-xpc-exports.json').write_text(json.dumps(report,indent=2)+'\n')
print('Staged existing NSXPC class exports; instruction bytes and '+str(len(original_exports))+' original exports preserved.')
