#!/usr/bin/env python3
"""Build Apple's Swift System implementation for the Darwin System module ABI."""
import json
from pathlib import Path
import re
import subprocess

project=Path(__file__).resolve().parent.parent
source=project/'vendor/swift-system'
build=project/'runtime/build-swift-system'
build.mkdir(parents=True,exist_ok=True)
def darwin(path): return '/Volumes/SystemRoot/workspace/'+str(path.relative_to(project))
sdk='/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain'
inputs=[darwin(p) for p in sorted((source/'Sources/System').rglob('*.swift')) if 'IORing' not in p.parts]
args=['-c','-whole-module-optimization','-parse-as-library','-Onone',
      '-enable-library-evolution','-swift-version','5','-module-name','System',
      '-target','x86_64-apple-macos14.4','-sdk',sdk,
      '-D','SYSTEM_PACKAGE_DARWIN','-enable-experimental-feature','Lifetimes',
      '-emit-module-path',darwin(build/'System.swiftmodule'),'-o',darwin(build/'System.o')]
for version,availability in re.findall(r'Available\("([^"]+)", "([^"]+)"\)',(source/'Package.swift').read_text()):
    args+=['-enable-experimental-feature',f'AvailabilityMacro=System {version}:{availability}']
args+=inputs
response=build/'System.rsp'
response.write_text('\n'.join(json.dumps(a) for a in args)+'\n')
with (project/'logs/build-swift-system.log').open('wb') as log:
    subprocess.run(['timeout','180',str(project/'bin/darling'),'shell',toolchain+'/usr/bin/swift-frontend',
                    '@'+darwin(response)],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
with (project/'logs/link-swift-system.log').open('wb') as log:
    subprocess.run(['timeout','60',str(project/'bin/darling'),'shell',toolchain+'/usr/bin/clang',
       '-dynamiclib','-target','x86_64-apple-macos14.4','-isysroot',sdk,darwin(build/'System.o'),
       '-L/usr/lib/swift','-L'+toolchain+'/usr/lib/swift/macosx','-lswiftCore','-lswiftSwiftOnoneSupport',
       '-Wl,-install_name,/usr/lib/swift/libswiftSystem.dylib',
       '-Wl,-compatibility_version,1.0','-Wl,-current_version,75.0',
       '-o',darwin(build/'libswiftSystem.dylib')],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Swift System compiled and linked; installation requires SDK client test.')
