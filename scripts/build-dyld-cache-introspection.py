#!/usr/bin/env python3
"""Stage read-only cache SPI and preserve libSystem while adding its reexport."""
from pathlib import Path
import hashlib,json,struct,subprocess

root=Path(__file__).resolve().parent.parent
c=json.loads((root/'config/dyld-cache-introspection.json').read_text());reference=root/'vendor/apple-dyld'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if subprocess.check_output(['git','-C',str(reference),'rev-parse','HEAD'],text=True).strip()!=c['source_commit']:
    raise ValueError('Unexpected dyld source revision')
for path,expected in c['files'].items():
    if digest(reference/path)!=expected:raise ValueError('Changed dyld reference: '+path)
legacy=c['legacy_backend'];legacy_root=root/legacy['root']
if subprocess.check_output(['git','-C',str(legacy_root),'rev-parse','HEAD'],text=True).strip()!=legacy['commit']:
    raise ValueError('Unexpected legacy dyld revision')
for path,expected in legacy['files'].items():
    if digest(legacy_root/path)!=expected:raise ValueError('Changed legacy ABI reference: '+path)
guest=root/'runtime/rootfs/usr/libexec/darling';original=guest/'usr/lib/libSystem.B.dylib'
if digest(guest/'usr/lib/system/libdyld.dylib')!=legacy['library_sha256']:
    raise ValueError('Unexpected existing dyld process-info backend')
if digest(original)!=c['libsystem_sha256']:raise ValueError('Unexpected base libSystem')
build=root/'runtime/dyld-cache-introspection';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos15.4','-isysroot',str(sdk),'-fblocks','-O2',
 '-DTARGET_OS_EXCLAVEKIT=0',
 '-I',str(reference/'include'),'-c',str(root/'scripts/dyld-cache-introspection.c'),'-o',str(build/'compat.o')],check=True)
subprocess.run(['python3',str(root/'scripts/prepare-macho-slices-source.py')],check=True)
cpp_sources=[('architecture',reference/'mach_o/Architecture.cpp'),('arch-api',root/'scripts/macho-arch-compat.cpp'),
    ('universal',root/'runtime/macho-slices-source/Universal-fixed.cpp'),('macho-error',reference/'mach_o/Error.cpp'),
    ('header-selected',root/'runtime/macho-slices-source/UnsafeHeader-selected.cpp'),
    ('slice-api',root/'runtime/macho-slices-source/slice-api.cpp')]
for name,source in cpp_sources:
    subprocess.run(['clang++-19','-target','x86_64-apple-macos15.4','-isysroot',str(sdk),'-std=c++20',
      '-nostdinc++','-I',str(sdk/'usr/include/c++/v1'),'-I',str(reference/'mach_o'),
      '-I',str(reference/'common'),'-fblocks',
      *(['-I',str(root/'vendor/darling/src/external/libplatform/private')] if name=='macho-error' else []),
      '-DTARGET_OS_EXCLAVEKIT=0','-D_LIBCPP_DISABLE_AVAILABILITY','-fno-rtti','-fno-exceptions','-fvisibility=hidden','-O2',
      '-c',str(source),'-o',str(build/(name+'.o'))],check=True)
library=root/'runtime/native-library-stage/libDarlingCacheIntrospection.dylib';temporary=library.with_suffix('.dylib.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','15.4','15.4',
 '-install_name','/usr/lib/libDarlingCacheIntrospection.dylib','-syslibroot',str(guest),'-L',str(guest/'usr/lib'),
 '-lSystem','-dead_strip',str(build/'compat.o'),*[str(build/(name+'.o')) for name,_ in cpp_sources],'-o',str(temporary)],check=True)
adapter=temporary.read_bytes();cursor=32;dependencies=[]
for _ in range(struct.unpack_from('<I',adapter,16)[0]):
    command,length=struct.unpack_from('<II',adapter,cursor)
    if command in (0xc,0x80000018,0x8000001f,0x80000023):
        start=cursor+struct.unpack_from('<I',adapter,cursor+8)[0]
        dependencies.append(adapter[start:adapter.index(0,start)].decode())
    if command==0x19:
        for i in range(struct.unpack_from('<I',adapter,cursor+64)[0]):
            at=cursor+72+80*i;name=adapter[at:at+16].split(b'\0')[0]
            if name==b'__mod_init_func' and struct.unpack_from('<Q',adapter,at+40)[0]:
                raise ValueError('A libSystem bootstrap adapter must not add initializers')
    cursor+=length
if dependencies!=['/usr/lib/libSystem.B.dylib']:
    raise ValueError('Unsafe bootstrap dependency cycle: '+str(dependencies))
exports=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(temporary)],text=True)
for required in ['_macho_for_each_slice','_macho_for_each_slice_in_fd']:
    if not any(line.split()[-1:]==[required] for line in exports.splitlines()):
        raise ValueError('Missing slice API export: '+required)
temporary.replace(library)
source=original.read_bytes()
if source[:4]==bytes.fromhex('cafebabe'):
    for i in range(struct.unpack_from('>I',source,4)[0]):
        cpu,_,offset,length,_=struct.unpack_from('>IIIII',source,8+20*i)
        if cpu==0x1000007:source=source[offset:offset+length];break
if source[:4]!=bytes.fromhex('cffaedfe'):raise ValueError('Expected classic x86_64 Mach-O')
binary=bytearray(source);count,size=struct.unpack_from('<II',binary,16);cursor=32;first=len(binary)
for _ in range(count):
    command,length=struct.unpack_from('<II',binary,cursor)
    if command==0x1d:raise ValueError('Do not preserve a stale libSystem code signature')
    if command==0x19:
        for i in range(struct.unpack_from('<I',binary,cursor+64)[0]):
            at=cursor+72+80*i;offset=struct.unpack_from('<I',binary,at+48)[0]
            if offset:first=min(first,offset)
    cursor+=length
if cursor!=32+size:raise ValueError('Invalid load commands')
name=b'/usr/lib/libDarlingCacheIntrospection.dylib\0';length=(24+len(name)+7)&~7
if cursor+length>first or any(binary[cursor:cursor+length]):raise ValueError('No empty header padding for reexport')
binary[cursor:cursor+length]=struct.pack('<6I',0x8000001f,length,24,0,0x10000,0x10000)+name.ljust(length-24,b'\0')
struct.pack_into('<II',binary,16,count+1,size+length)
if binary[24:cursor]!=source[24:cursor] or binary[cursor+length:]!=source[cursor+length:]:
    raise ValueError('Unexpected mutation outside load-command fields/padding')
destination=root/'runtime/native-library-stage/libSystem.B.dylib';temporary=destination.with_suffix('.dylib.pending')
temporary.write_bytes(binary);temporary.replace(destination)
report={'installed':False,'execution_verified':False,'full_compatibility':False,'source':c,
 'library_sha256':digest(library),'libsystem_stage_sha256':digest(destination),
 'existing_libsystem_code_and_export_trie_unchanged':True,'added_reexport':'/usr/lib/libDarlingCacheIntrospection.dylib',
 'scope':c['scope']}
(root/'artifacts/dyld-cache-introspection.json').write_text(json.dumps(report,indent=2)+'\n')
