#!/usr/bin/env python3
"""Stage actual libc++ float/double formatting alongside the existing wrapper."""
from pathlib import Path
import hashlib,json,re,subprocess,runpy

root=Path(__file__).resolve().parent.parent
c=json.loads((root/'config/libcxx-to-chars.json').read_text());reference=root/'vendor/llvm-charconv'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if subprocess.check_output(['git','-C',str(reference),'rev-parse','HEAD'],text=True).strip()!=c['commit']:
    raise ValueError('Unexpected libc++ source revision')
for path,expected in c['files'].items():
    if digest(reference/path)!=expected:raise ValueError('Changed official source: '+path)
for path,expected in c['existing_objects'].items():
    if digest(root/path)!=expected:raise ValueError('Changed original wrapper object: '+path)
native=c['native_long_double_reference']
if digest(root/'runtime/fullsystem-libraries'/native['provider'].lstrip('/'))!=native['provider_sha256']:
    raise ValueError('Wrong native long-double reference image')
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
for symbol,payload in native['entry_prefixes'].items():
    address=ns['resolve'](native['provider'],symbol)
    if address is None or ns['read'](address,len(bytes.fromhex(payload))).hex()!=payload:
        raise ValueError('Native long-double conversion differs: '+symbol)
guest=root/'runtime/rootfs/usr/libexec/darling'
base=guest/'usr/lib/libc++.1.dylib';backend=guest/'usr/lib/libc++0.dylib'
if digest(base)!=c['existing_wrapper_sha256'] or digest(backend)!=c['existing_backend_sha256']:
    raise ValueError('Unexpected existing libc++ wrapper/backend')
build=root/'runtime/libcxx-to-chars';build.mkdir(exist_ok=True)
original=(reference/'libcxx/src/charconv.cpp').read_text()
selected=[]
pattern=r'to_chars_result to_chars\(char\* __first, char\* __last, (?:float|double|long double) __value(?:, chars_format __fmt(?:, int __precision)?)?\) \{'
for match in re.finditer(pattern,original):
    depth=1;end=match.end()
    while depth:
        if end>=len(original):raise ValueError('Unterminated official overload')
        depth+=(original[end]=='{')-(original[end]=='}');end+=1
    selected.append(original[match.start():end])
if len(selected)!=9:raise ValueError('Expected nine official to_chars overloads')
text=original[:original.index('#include')]+'''#include <charconv>
#include <string.h>
#include "include/to_chars_floating_point.h"
_LIBCPP_BEGIN_NAMESPACE_STD
'''+ '\n\n'.join(selected)+'\n_LIBCPP_END_NAMESPACE_STD\n'
(build/'to-chars.cpp').write_text(text)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
inputs=[build/'to-chars.cpp',*[reference/'libcxx/src/ryu'/name for name in ['d2s.cpp','d2fixed.cpp','f2s.cpp']]]
objects=[]
for source in inputs:
    destination=build/(source.stem+'.o');objects.append(destination)
    subprocess.run(['clang++-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
      '-nostdinc++','-I',str(sdk/'usr/include/c++/v1'),'-I',str(reference/'libcxx/src'),
      '-D_LIBCPP_BUILDING_LIBRARY=1','-D_LIBCPP_DISABLE_AVAILABILITY','-DNDEBUG',
      '-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_NONE','-std=c++20','-O2','-fPIC',
      '-c',str(source),'-o',str(destination)],check=True)
destination=root/'runtime/native-library-stage/libc++.1.dylib';temporary=destination.with_suffix('.dylib.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
 '-install_name','/usr/lib/libc++.1.dylib','-compatibility_version','1.0.0','-current_version','1.0.0',
 '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem','-reexport_library',str(backend),
 *[str(root/path) for path in c['existing_objects']],*[str(p) for p in objects],'-o',str(temporary)],check=True)
def exports(path):
    output=subprocess.check_output(['llvm-nm-19','--defined-only','--extern-only',str(path)],text=True)
    return {line.split()[-1] for line in output.splitlines() if line.split()}
old,new=exports(base),exports(temporary)
if old-new:raise ValueError('Existing libc++ exports lost: '+str(sorted(old-new)))
required={'__ZNSt3__18to_charsEPcS0_'+type_name+suffix
    for type_name in ['d','f','e'] for suffix in ['', 'NS_12chars_formatE','NS_12chars_formatEi']}
if not required<=new:raise ValueError('Missing actual default formatting APIs')
temporary.replace(destination)
r={'installed':False,'execution_verified':False,'full_compatibility':False,
 'source':c,'library_sha256':digest(destination),'old_exports_preserved':len(old),'new_exports':len(new),
 'scope':c['scope']}
(root/'artifacts/libcxx-to-chars.json').write_text(json.dumps(r,indent=2)+'\n')
