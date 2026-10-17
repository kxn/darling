#!/usr/bin/env python3
"""Add the default-protection openat API over Darling's real filesystem calls."""
from pathlib import Path
import hashlib
import json
import subprocess

project=Path(__file__).resolve().parent.parent
config=json.loads((project/'config/openat-dprotected.json').read_text())
for relative,digest in config['files'].items():
    if hashlib.sha256((project/relative).read_bytes()).hexdigest()!=digest:
        raise ValueError('Changed openat SDK/source/backend contract: '+relative)
build=project/'runtime/openat-dprotected';build.mkdir(exist_ok=True)
sdk=project/config['sdk'];guest=project/'runtime/rootfs/usr/libexec/darling'
obj=build/'openat.o';output=project/'runtime/native-library-stage/libDarlingOpenAt.dylib'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),
    '-O2','-c',str(project/'scripts/openat-dprotected-compat.c'),'-o',str(obj)],check=True)
temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib'),'-lSystem','-install_name',
    '/usr/lib/libDarlingOpenAt.dylib',str(obj),'-o',str(temporary)],check=True)
temporary.replace(output)
report={'installed':False,'execution_verified':False,'full_compatibility':False,
    'library_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'scope':config['scope'],'existing_open_dprotected_backend_limit':config['existing_backend_limit']}
(project/'artifacts/openat-dprotected.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built default-protection openat forwarding with explicit protection failures')
