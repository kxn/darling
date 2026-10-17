#!/usr/bin/env python3
"""Build the pinned upstream policy constructor using the genuine Security factory.

This compiles the complete selected constructor/helper component, not all of
Security.framework. The staged original framework keeps its code and original
exports, and reexports the new constructor from this source component.
"""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,re,struct,subprocess
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/security-external-developer-policy.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
repo=root/'vendor/apple-security';legacy=root/'vendor/darling/src/external/security'
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==config['modern_source_commit']
assert subprocess.check_output(['git','-C',str(legacy),'rev-parse','HEAD'],text=True).strip()==config['source_revision']
def function(text,name):
    match=re.search(r'(?m)^(?:static\s+inline\s+|static\s+)?(?:void|bool|SecPolicyRef|CFNumberRef|CFMutableDictionaryRef)\s+'+re.escape(name)+r'\s*\([^;]*?\)\s*\{',text)
    assert match,name
    at=text.index('{',match.start())+1;depth=1
    while depth:
        if text[at]=='{':depth+=1
        elif text[at]=='}':depth-=1
        at+=1
    return text[match.start():at]
upstream={}
for path,value in config['modern_source_files'].items():
    payload=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+path])
    assert hashlib.sha256(payload).hexdigest()==value;upstream[path]=payload.decode()
source=legacy/'OSX/sec/Security/SecPolicyExternalDeveloper.c';text=source.read_text()
for name,value in config['selected_upstream_functions'].items():
    actual=function(text,name)
    assert hashlib.sha256(actual.encode()).hexdigest()==value
    assert actual==function(upstream[config['function_providers'][name]],name)
original=root/config['base'];assert digest(original)==config['base_sha256']
exports_listing=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie','--arch=x86_64',str(original)],text=True)
old_names=set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',exports_listing,re.M))
assert all('_'+name in old_names for name in config['constants'] if name not in config['local_constant'])
assert config['public_symbol'] not in old_names
build=root/'runtime/security-policy-source';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
obj=build/'SecPolicyExternalDeveloper.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fvisibility=hidden',
    '-c',str(source),'-o',str(obj)],check=True)
library=libraries/'libDarlingExternalDeveloperPolicy.dylib';pending=library.with_name(library.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),
    '-F',str(guest/'System/Library/Frameworks'),'-framework','Security','-framework','CoreFoundation','-lSystem',
    '-install_name','/usr/lib/libDarlingExternalDeveloperPolicy.dylib','-exported_symbol',config['public_symbol'],
    str(obj),'-o',str(pending)],check=True)
pending.replace(library)
helper_exports=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(library)],text=True)
assert set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',helper_exports,re.M))=={config['public_symbol']}
data=original.read_bytes()
if data[:4]==b'\xca\xfe\xba\xbe':
    slices=[struct.unpack_from('>IIIII',data,8+20*i) for i in range(struct.unpack_from('>I',data,4)[0])]
    arch=next(a for a in slices if a[0]==0x1000007);data=data[arch[2]:arch[2]+arch[3]]
assert hashlib.sha256(data).hexdigest()==config['base_x86_64_sha256']
assert data[:4]==b'\xcf\xfa\xed\xfe'
binary=bytearray(data);at=32;dependencies=[];ranges=[];file_sections=[];export_command=None
for _ in range(struct.unpack_from('<I',data,16)[0]):
    command,size=struct.unpack_from('<II',data,at)
    if command==0x19:
        name=data[at+8:at+24].split(b'\0')[0]
        if name==b'__TEXT':text_base=struct.unpack_from('<Q',data,at+24)[0]
        if name==b'__LINKEDIT':linkedit=at
        for j in range(struct.unpack_from('<I',data,at+64)[0]):
            section=at+72+80*j;length=struct.unpack_from('<Q',data,section+40)[0]
            offset=struct.unpack_from('<I',data,section+48)[0];flags=struct.unpack_from('<I',data,section+64)[0]
            if offset:file_sections.append(offset)
            if flags&0x80000400:ranges.append((offset,length))
    elif command==2:symoff,count,stroff,strsize=struct.unpack_from('<IIII',data,at+8)
    elif command in (0x22,0x80000022):export_command=at+40
    elif command==0x80000033:export_command=at+8
    elif command in (0xc,0x80000018,0x8000001f,0x80000023,0x20):dependencies.append(at)
    elif command==0x1d:raise ValueError('Refuse to leave a stale code signature on modified Security')
    at+=size
assert export_command is not None
name=b'/usr/lib/libDarlingExternalDeveloperPolicy.dylib\0';size=(24+len(name)+7)&~7
assert at+size<=min(file_sections) and not any(data[at:at+size])
binary[at:at+size]=struct.pack('<IIIIII',0x8000001f,size,24,2,0x10000,0x10000)+name.ljust(size-24,b'\0')
struct.pack_into('<I',binary,16,struct.unpack_from('<I',data,16)[0]+1)
struct.pack_into('<I',binary,20,struct.unpack_from('<I',data,20)[0]+size)
def uleb(value):
    result=bytearray()
    while value>=128:result.append((value&127)|128);value>>=7
    return bytes(result+bytes([value]))
def take(blob,cursor):
    result=shift=0
    while True:
        value=blob[cursor];cursor+=1;result|=(value&127)<<shift
        if value<128:return result,cursor
        shift+=7;assert shift<64
def parse(blob):
    entries={}
    def visit(cursor,prefix):
        length,c=take(blob,cursor)
        if length:entries[prefix]=blob[c:c+length]
        c+=length;children=blob[c];c+=1
        for _ in range(children):
            end=blob.index(0,c);edge=blob[c:end];offset,c=take(blob,end+1);visit(offset,prefix+edge)
    visit(0,b'');return entries
offset,length=struct.unpack_from('<II',data,export_command)
exports=parse(data[offset:offset+length]);original_exports=dict(exports)
assert set(k.decode() for k in exports)==old_names
accessor=None
for j in range(count):
    nameoff,kind,section,desc,value=struct.unpack_from('<IBBHQ',data,symoff+16*j)
    n=data[stroff+nameoff:data.index(0,stroff+nameoff)].decode()
    if n==config['existing_hidden_accessor']:
        assert kind&0xe==0xe and accessor is None;accessor=value
assert accessor is not None and config['existing_hidden_accessor'].encode() not in exports
exports[config['existing_hidden_accessor'].encode()]=uleb(0)+uleb(accessor-text_base)
exports[config['public_symbol'].encode()]=uleb(8)+uleb(len(dependencies)+1)+b'\0'
nodes=[]
def node(items,prefix):
    result=dict(terminal=exports.get(prefix,b''),children=[],offset=0);nodes.append(result)
    remaining=[n for n in items if n!=prefix]
    for first in sorted(set(n[len(prefix)] for n in remaining)):
        group=[n for n in remaining if n[len(prefix)]==first];common=group[0]
        for name in group[1:]:
            j=len(prefix)
            while j<min(len(common),len(name)) and common[j]==name[j]:j+=1
            common=common[:j]
        result['children'].append((common[len(prefix):],node(group,common)))
    return result
node(list(exports),b'')
def encode(n):
    return uleb(len(n['terminal']))+n['terminal']+bytes([len(n['children'])])+b''.join(edge+b'\0'+uleb(child['offset']) for edge,child in n['children'])
for _ in range(100):
    cursor=0;changed=False
    for n in nodes:
        changed|=n['offset']!=cursor;n['offset']=cursor;cursor+=len(encode(n))
    if not changed:break
else:raise ValueError('Export trie did not converge')
fresh=b''.join(encode(n) for n in nodes)
binary.extend(bytes(-len(binary)%8));offset=len(binary);binary.extend(fresh)
struct.pack_into('<II',binary,export_command,offset,len(fresh))
fileoff=struct.unpack_from('<Q',data,linkedit+40)[0];filesize=len(binary)-fileoff
struct.pack_into('<Q',binary,linkedit+48,filesize);struct.pack_into('<Q',binary,linkedit+32,(filesize+4095)&~4095)
allowed=set(range(16,24))|set(range(at,at+size))|set(range(export_command,export_command+8))|set(range(linkedit+32,linkedit+40))|set(range(linkedit+48,linkedit+56))
assert all(before==after or j in allowed for j,(before,after) in enumerate(zip(data,binary)))
for offset,length in ranges:assert binary[offset:offset+length]==data[offset:offset+length]
assert all(parse(fresh)[key]==value for key,value in original_exports.items())
framework=build/'frameworks/Security.framework';destination=framework/'Versions/A/Security';destination.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending=destination.with_name('Security.pending');pending.write_bytes(binary);pending.replace(destination)
for path,target in [(framework/'Versions/Current','A'),(framework/'Security','Versions/Current/Security')]:
    if not path.is_symlink():path.symlink_to(target)
files=[source,legacy/'OSX/sec/Security/CMakeLists.txt',legacy/'trust/headers/SecPolicyPriv.h']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_security_source_build=False,
    source_component='Complete upstream optional-expiry developer-policy constructor and its 11 helper bodies',
    source_configuration=config,source_files={str(p.relative_to(root)):digest(p) for p in files},
    upstream_function_bodies_unchanged=True,library=str(library.relative_to(root)),library_sha256=digest(library),
    staged_framework=str(destination.relative_to(root)),staged_framework_sha256=digest(destination),
    original_exports_preserved=len(original_exports),source_exports=len(exports),
    promoted_existing_accessor=dict(symbol=config['existing_hidden_accessor'],address=hex(accessor)),
    original_security_instructions_unchanged=True,original_bytes_outside_header_updates_unchanged=True,
    appended_source_component_reexport=True,original_framework_ID_preserved=True,
    private_policy_layout_access_added=False,runtime_execution_verified=False,
    scope='Genuine existing SecPolicy object factory and typed CoreFoundation constraints. No certificate-trust success stub or new trust evaluator. Existing old trust backend duplicate-extension and other modern-check enforcement remains unverified.',
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/security-policy-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built source developer-policy constructor; staged original Security code with',len(original_exports),'old exports preserved')
