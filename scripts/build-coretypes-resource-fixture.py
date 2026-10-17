#!/usr/bin/env python3
"""Compile the real Foundation metadata reproducer for the selected Intel runtime."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
commands=[['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c','fixtures/hello/coretypes-resource-values.m','-o','artifacts/coretypes-resource-values.o'],
    ['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-F',str(guest/'System/Library/Frameworks'),'-framework','Foundation','-lobjc','-lSystem','artifacts/coretypes-resource-values.o','-o','artifacts/coretypes-resource-values']]
for command in commands:subprocess.run(command,cwd=root,check=True)
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
report=dict(source='fixtures/hello/coretypes-resource-values.m',source_sha256=digest('fixtures/hello/coretypes-resource-values.m'),
    binary='artifacts/coretypes-resource-values',binary_sha256=digest('artifacts/coretypes-resource-values'),commands=commands,
    runtime_execution_verified=False)
(root/'artifacts/coretypes-resource-values-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built genuine Foundation URL/metadata reproducer')
