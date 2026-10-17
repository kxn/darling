#!/usr/bin/env python3
"""Build selected Foundation libc entry points over pinned real backends."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy
import subprocess

project=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--test-bad-guard',action='store_true')
args=parser.parse_args()
config=json.loads((project/'config/foundation-libc-compat.json').read_text())
if hashlib.sha256((project/config['backend_binary']).read_bytes()).hexdigest()!=config['backend_sha256']:
    raise ValueError('Changed libc backend')
for relative,digest in config['files'].items():
    if hashlib.sha256((project/relative).read_bytes()).hexdigest()!=digest:
        raise ValueError('Changed SDK/backend contract: '+relative)
native=config['native_receipt']
if hashlib.sha256((project/'runtime/fullsystem-libraries'/native['path'].lstrip('/')).read_bytes()).hexdigest()!=native['sha256']:
    raise ValueError('Changed native receipt reference')
ns=runpy.run_path(str(project/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':project/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':project/'runtime/fullsystem-libraries'})
payload=bytes.fromhex(native['bytes'])
if ns['read'](int(native['address'],0),len(payload))!=payload:
    raise ValueError('Changed native receipt routine')
build=project/'runtime/foundation-libc-compat'
if args.test_bad_guard:build=build/'bad-guard'
build.mkdir(parents=True,exist_ok=True)
def array(name,payload):return 'static const unsigned char '+name+'[]={'+','.join(hex(b) for b in payload)+'};\n'
header=array('libc_backend_uuid',bytes.fromhex(config['backend_uuid']))
for field,name in [('probe','libc_probe'),('environment_lock','environment_lock'),('environment_unlock','environment_unlock')]:
    record=config[field];payload=bytearray.fromhex(record['bytes'])
    if args.test_bad_guard and field=='probe':payload[0]^=1
    header+='static const uintptr_t '+name+'_offset='+record['address']+';\n'
    header+=array(name+'_bytes',payload)
(build/'libc-backend.h').write_text(header)
sdk=project/config['sdk'];obj=build/'libc.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-I',str(build),'-O2','-c',str(project/'scripts/foundation-libc-compat.c'),'-o',str(obj)],check=True)
stack_source=(project/'runtime/thread-stack-pcs-reference.c').read_text()
# Preserve the Apple walker. Its private dependencies have these narrower
# equivalents on the pinned x86_64 backend. No alternate dyld stack exists in
# this old loader, so do not manufacture a range for one.
changes={
    '#include <mach-o/dyld_priv.h>':'#include <stdbool.h>\n#include <stddef.h>\n#include <stdint.h>',
    '#include <pthread/private.h>':'#define __PTK_FRAMEWORK_SWIFT_KEY3 103\n#define _pthread_getspecific_direct pthread_getspecific',
    '#include "stack_logging.h"':'',
    '\t_dyld_stack_range(&dyldstackbot, &dyldstacktop);':'\t/* Pinned legacy dyld does not switch to an alternate dyld stack. */',
    'thread_stack_async_pcs(vm_address_t *buffer, unsigned max, unsigned *nb)':'__attribute__((visibility("default")))\nthread_stack_async_pcs(vm_address_t *buffer, unsigned max, unsigned *nb)',
}
for before,after in changes.items():
    if stack_source.count(before)!=1:raise ValueError('Changed Apple stack-walker adaptation point: '+before)
    stack_source=stack_source.replace(before,after)
stack=build/'thread-stack.c';stack.write_text(stack_source)
stack_obj=build/'thread-stack.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-O2','-fno-omit-frame-pointer','-fvisibility=hidden','-c',str(stack),'-o',str(stack_obj)],check=True)
attributes_obj=build/'file-attributes.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-O2','-c',str(project/'scripts/foundation-file-attributes.c'),'-o',str(attributes_obj)],check=True)
statfs_obj=build/'statfs-ext.o'
if '#define STATFS_EXT_NOBLOCK  0x0001' not in (project/'runtime/statfs-ext-mount-reference.h').read_text():
    raise ValueError('Changed private statfs flag definition')
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-DSTATFS_EXT_NOBLOCK=0x0001','-O2','-c',str(project/'runtime/statfs-ext-reference.c'),'-o',str(statfs_obj)],check=True)
guest=project/'runtime/rootfs/usr/libexec/darling'
output=build/'libDarlingFoundationSystem.dylib' if args.test_bad_guard else \
    project/'runtime/native-library-stage/libDarlingFoundationSystem.dylib'
temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem','-install_name',
    '/usr/lib/libDarlingFoundationSystem.dylib',str(obj),str(stack_obj),str(attributes_obj),str(statfs_obj),'-o',str(temporary)],check=True)
temporary.replace(output)
if not args.test_bad_guard:
    report={'installed':False,'execution_verified':False,'full_compatibility':False,
        'library_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'backend_sha256':config['backend_sha256'],'scope':config['scope'],
        'thread_stack_scope':config['thread_stack_scope'],
        'file_attributes_scope':config['file_attributes_scope'],
        'statfs_ext_scope':config['statfs_ext_scope'],
        'thread_stack_source_commit':config['thread_stack_source_commit']}
    (project/'artifacts/foundation-libc-compat.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built selected Foundation libc adapters')
