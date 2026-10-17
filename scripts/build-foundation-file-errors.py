#!/usr/bin/env python3
"""Build verified file-error semantics as actual Foundation NSError objects."""
from pathlib import Path
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
c=json.loads((root/'config/foundation-file-errors.json').read_text())
source=root/'runtime/fullsystem-libraries'/c['provider'].lstrip('/')
if hashlib.sha256(source.read_bytes()).hexdigest()!=c['provider_sha256']:raise ValueError('Wrong original Foundation')
ns=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
 'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
 'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
for symbol,record in c['routines'].items():
    address=ns['resolve'](c['provider'],symbol)
    if address!=int(record['address'],0) or hashlib.sha256(ns['read'](address,record['length'])).hexdigest()!=record['sha256']:
        raise ValueError('Native file-error routine changed: '+symbol)
build=root/'runtime/foundation-file-errors';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2',
 '-c',str(root/'scripts/foundation-file-errors.m'),'-o',str(build/'errors.o')],check=True)
destination=root/'runtime/native-library-stage/libDarlingFoundationErrors.dylib';temporary=destination.with_suffix('.dylib.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
 '-install_name','/usr/lib/libDarlingFoundationErrors.dylib','-syslibroot',str(guest),'-L',str(guest/'usr/lib'),
 '-lSystem','-lobjc','-framework','Foundation',str(build/'errors.o'),'-o',str(temporary)],check=True)
temporary.replace(destination)
(root/'artifacts/foundation-file-errors.json').write_text(json.dumps({'source':c,'installed':False,
 'library_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'execution_verified':False,'full_compatibility':False},indent=2)+'\n')
