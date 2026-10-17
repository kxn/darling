#!/usr/bin/env python3
"""Stage the existing Foundation wrapper with verified immutable ABI additions."""
from pathlib import Path
import hashlib,json,runpy,struct,subprocess

root=Path(__file__).resolve().parent.parent
c=json.loads((root/'config/foundation-staged-additions.json').read_text())
source=root/'runtime/fullsystem-libraries'/c['provider'].lstrip('/')
if hashlib.sha256(source.read_bytes()).hexdigest()!=c['provider_sha256']:
    raise ValueError('Unexpected original Foundation image')
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
build=root/'runtime/foundation-staged-additions';build.mkdir(exist_ok=True)
lines=['#include <stdint.h>'];values={}
for index,symbol in enumerate(c['enum_case_literals']):
    if not symbol.startswith('_$s') or not symbol.endswith('mFWC'):
        raise ValueError('Only Swift enum-case literals accepted')
    address=ns['resolve'](c['provider'],symbol)
    if address is None:raise ValueError('Original enum-case literal not exported')
    value=struct.unpack('<I',ns['read'](address,4))[0]
    if value>65535:raise ValueError('Unexpected enum-case index')
    values[symbol]=value
    lines.append(f'const uint32_t literal_{index} __asm__({json.dumps(symbol)}) = {value}U;')
(build/'enum-cases.c').write_text('\n'.join(lines)+'\n')
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
for name,path in [('enum-cases',build/'enum-cases.c'),('numbers',root/'scripts/constant-numbers.m')]:
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fPIC','-O2',
      '-c',str(path),'-o',str(build/(name+'.o'))],check=True)
destination=root/'runtime/native-framework-stage/Foundation.framework/Versions/C/Foundation'
destination.parent.mkdir(parents=True,exist_ok=True)
temporary=destination.with_name('Foundation.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
 '-install_name',c['provider'],'-compatibility_version','300.0.0','-current_version','1349.0.0',
 '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem','-lobjc','-rpath','/usr/lib/swift',
 '-framework','CoreFoundation','-reexport_library',str(guest/'usr/lib/libFND.dylib'),
 '-reexport_library',str(guest/'usr/lib/swift/libswiftFoundation.dylib'),
 '-reexport_library',str(root/'runtime/native-library-stage/libDarlingConstantFloat.dylib'),
 '-reexport_library',str(root/'runtime/native-library-stage/libDarlingDirectoryHint.dylib'),
 '-reexport_library',str(root/'runtime/native-library-stage/libDarlingURLCompat.dylib'),
 '-reexport_library',str(root/'runtime/native-library-stage/libDarlingFoundationErrors.dylib'),
 str(build/'numbers.o'),str(build/'enum-cases.o'),'-o',str(temporary)],check=True)
symbols=subprocess.check_output(['llvm-nm-19','--defined-only','--extern-only',str(temporary)],text=True)
for symbol in values:
    if symbol not in {line.split()[-1] for line in symbols.splitlines() if line.split()}:
        raise ValueError('Missing generated literal export: '+symbol)
temporary.replace(destination)
bundle=destination.parent.parent.parent
for link,value in [(bundle/'Versions/Current','C'),(bundle/'Foundation','Versions/Current/Foundation')]:
    if link.is_symlink() and link.readlink()==Path(value):continue
    if link.exists() or link.is_symlink():raise ValueError('Unexpected Foundation stage link')
    link.symlink_to(value)
report={'original_foundation_sha256':c['provider_sha256'],'staged_wrapper_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
 'enum_case_literals':values,'installed':False,'execution_verified':False,'full_compatibility':False,'scope':c['scope']}
(root/'artifacts/foundation-staged-additions.json').write_text(json.dumps(report,indent=2)+'\n')
