#!/usr/bin/env python3
"""Build OpenCombine's real publisher implementation as a resilient Combine ABI."""
import json
from pathlib import Path
import re
import subprocess

project=Path(__file__).resolve().parent.parent
source=project/'vendor/OpenCombine'
build=project/'runtime/build-combine'
build.mkdir(parents=True,exist_ok=True)
sdk=project/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang++-19','-target','x86_64-apple-macos14.0','-isysroot',str(sdk),
    '-std=c++17','-fPIC','-O2','-I',str(source/'Sources/COpenCombineHelpers/include'),
    '-c',str(source/'Sources/COpenCombineHelpers/COpenCombineHelpers.cpp'),
    '-o',str(build/'helpers.o')],check=True)

def darwin(path):
    return '/Volumes/SystemRoot/workspace/'+str(path.relative_to(project))

inputs=[]
for original in sorted((source/'Sources/OpenCombine').rglob('*.swift')):
    target=build/'Sources'/original.relative_to(source/'Sources/OpenCombine')
    target.parent.mkdir(parents=True,exist_ok=True)
    contents=re.sub(r'\bOpenCombine\b','Combine',original.read_text())
    # These layouts are also frozen/fixed in Apple's SDK interface. Inlined
    # clients allocate the boxes directly, so preserve both layout and names.
    if original.name in ('AnyPublisher.swift','AnySubscriber.swift'):
        contents=contents.replace('public struct Any','@frozen public struct Any')
        contents=re.sub(r'(?m)^(internal (?:final )?class (?:PublisherBox|AnySubscriber|ClosureBasedAnySubscriber))',
                        r'@_fixed_layout \1',contents)
    if original.name == 'AnyPublisher.swift':
        contents=contents.replace('PublisherBox(base: publisher)','PublisherBox(publisher)')
        contents=contents.replace('internal init(base: PublisherType)', 'internal init(_ base: PublisherType)')
    if original.name == 'Subscribers.Demand.swift':
        contents=contents.replace('public struct Demand:', '@frozen public struct Demand:')
    if original.name == 'ImmediateScheduler.swift':
        # The SDK does not expose this initializer's body or freeze Stride.
        contents=contents.replace('@inlinable\n            public init(_ value: Int)',
                                  'public init(_ value: Int)')
    target.write_text(contents)
    inputs.append(darwin(target))
args=['-c','-whole-module-optimization','-parse-as-library','-Onone',
    '-enable-library-evolution','-swift-version','5','-module-name','Combine',
    '-target','x86_64-apple-macos14.0','-sdk',darwin(sdk),
    '-I',darwin(source/'Sources/COpenCombineHelpers/include'),
    '-emit-module-path',darwin(build/'Combine.swiftmodule'),'-o',darwin(build/'Combine.o'),*inputs]
response=build/'Combine.rsp'
response.write_text('\n'.join(json.dumps(arg) for arg in args)+'\n')
frontend='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift-frontend'
print(f'Compiling {len(inputs)} Combine Swift files',flush=True)
with (project/'logs/build-combine-swift.log').open('wb') as log:
    subprocess.run(['timeout','180',str(project/'bin/darling'),'shell',frontend,'@'+darwin(response)],
        cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Combine core compiled',flush=True)
