#!/usr/bin/env python3
"""Build the class-enumeration adapter against the pinned existing runtime."""
from pathlib import Path
import hashlib
import json
import subprocess
import argparse
import re

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--test-bad-selector-guard',action='store_true')
args=parser.parse_args()

project=Path(__file__).resolve().parent.parent
config=json.loads((project/'config/objc-class-enumeration.json').read_text())
for folder,commit_key,files_key in [('vendor/darling/src/external/objc4','backend_source_commit','backend_files'),
                                    ('vendor/apple-objc4','apple_source_commit','apple_files')]:
    repo=project/folder
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=config[commit_key]:
        raise ValueError('Changed runtime source revision')
    for relative,digest in config[files_key].items():
        if hashlib.sha256((repo/relative).read_bytes()).hexdigest()!=digest:
            raise ValueError('Changed runtime source contract: '+relative)
if hashlib.sha256((project/config['backend_binary']).read_bytes()).hexdigest()!=config['backend_sha256']:
    raise ValueError('Changed existing Objective-C runtime')
build=project/'runtime/objc-class-enumeration';build.mkdir(exist_ok=True)
if args.test_bad_selector_guard:
    build=build/'bad-selector-guard';build.mkdir(exist_ok=True)
selector=config['selector_backend']
probe=bytearray.fromhex(selector['probe_bytes'])
if args.test_bad_selector_guard:probe[0]^=1
def byte_array(name,payload):return 'static const unsigned char '+name+'[]={'+','.join(hex(b) for b in payload)+'};\n'
header=byte_array('selector_backend_uuid',bytes.fromhex(selector['uuid']))
header+=byte_array('selector_probe_bytes',probe)
for name,key in [('selector_set_offset','named_selector_set'),('selector_lock_offset','selector_lock'),('selector_probe_offset','probe_address')]:
    header+='static const uintptr_t '+name+'='+selector[key]+';\n'
source=(project/'vendor/darling/src/external/objc4/runtime/objc-private.h').read_text()
match=re.search(r'static __inline uint32_t _objc_strhash\(const char \*s\) \{.*?\n\}',source,re.S)
if not match:raise ValueError('Pinned original selector hash function is absent')
header+='// Unmodified hash function from pinned Apple/Darling objc-private.h.\n'+match[0]+'\n'
(build/'selector-backend.h').write_text(header)
sdk=project/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=build/'enumeration.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-fblocks','-O2','-c',str(project/'scripts/objc-class-enumeration.c'),'-o',str(obj)],check=True)
selector_obj=build/'selector.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-I',str(build),'-O2','-c',str(project/'scripts/objc-selector-lookup.c'),'-o',str(selector_obj)],check=True)
guest=project/'runtime/rootfs/usr/libexec/darling'
output=project/'runtime/native-library-stage/libDarlingObjCEnumeration.dylib'
if args.test_bad_selector_guard:output=build/'libDarlingObjCEnumeration.dylib'
temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lobjc','-lSystem',
    '-install_name','/usr/lib/libDarlingObjCEnumeration.dylib',str(obj),str(selector_obj),'-o',str(temporary)],check=True)
temporary.replace(output)
report={'installed':False,'execution_verified':False,'full_compatibility':False,
    'library_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'backend_sha256':config['backend_sha256'],'scope':config['scope']}
if not args.test_bad_selector_guard:
    (project/'artifacts/objc-class-enumeration.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built class enumeration over existing runtime snapshots')
