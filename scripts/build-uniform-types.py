#!/usr/bin/env python3
"""Derive documented UTI values from the installed Apple SDK, then build Swift ABI."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

project=Path(__file__).resolve().parent.parent
build=project/'runtime/build-uniform-types'
build.mkdir(parents=True,exist_ok=True)
sdk_relative='Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
sdk=project/'runtime/state/prefix'/sdk_relative
header=sdk/'System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Headers/UTCoreTypes.h'
text=header.read_text()
entries=[]
for block in re.split(r'(?=\*\s+kUTType\w+\s+\*\*\* DEPRECATED)',text):
    name=re.search(r'^\*\s+(kUTType\w+)\s+',block)
    uti=re.search(r'\*\s+UTI:\s*([\w.-]+)',block)
    if not name or not uti: continue
    declaration=re.search(r'extern const CFStringRef '+name[1]+r'\s+API_DEPRECATED\("([^"\n]+)',text)
    property_name=re.search(r'UTType\.([\w]+)',declaration[1]) if declaration else None
    parents=re.search(r'\*\s+conforms to:\s*([^\n]+)',block)
    parent_names=re.findall(r'\b(?:public|com|org)\.[\w.-]+',parents[1]) if parents else []
    entries.append({'constant':name[1],'identifier':uti[1],
                    'swift_property':property_name[1] if property_name else None,'parents':parent_names})
if len(entries) != 128: raise SystemExit('SDK UTI parser found an unexpected number of definitions')
lines=['// Generated from the user-provided SDK UTCoreTypes.h.',
       'internal let documentedTypes: [String: [String]] = [']
lines += [f'    {json.dumps(e["identifier"])}: {json.dumps(e["parents"])},' for e in entries]
lines += [']','extension UTType {']
lines += [f'    public static var {e["swift_property"]}: UTType {{ UTType(knownIdentifier: {json.dumps(e["identifier"])}) }}'
          for e in entries if e['swift_property']]
lines += ['}']
generated=build/'DocumentedTypes.swift'
generated.write_text('\n'.join(lines)+'\n')
(build/'sdk-types.json').write_text(json.dumps({'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
                                             'entries':entries},indent=2)+'\n')
def darwin(path):return '/Volumes/SystemRoot/workspace/'+str(path.relative_to(project))
toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain'
with (project/'logs/build-uniform-types.log').open('wb') as log:
    subprocess.run(['timeout','90',str(project/'bin/darling'),'shell',toolchain+'/usr/bin/swift-frontend',
      '-c','-whole-module-optimization','-parse-as-library','-Onone','-enable-library-evolution',
      '-swift-version','5','-module-name','UniformTypeIdentifiers','-target','x86_64-apple-macos14.0',
      '-sdk','/'+sdk_relative,darwin(project/'scripts/uniform-types.swift'),darwin(generated),
      '-o',darwin(build/'UniformTypeIdentifiers.o')],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
with (project/'logs/link-uniform-types.log').open('wb') as log:
    subprocess.run(['timeout','60',str(project/'bin/darling'),'shell',toolchain+'/usr/bin/clang',
      '-dynamiclib','-target','x86_64-apple-macos14.0','-isysroot','/'+sdk_relative,
      darwin(build/'UniformTypeIdentifiers.o'),'-L/usr/lib/swift','-L'+toolchain+'/usr/lib/swift/macosx',
      '-lswiftCore','-lswiftSwiftOnoneSupport',
      '-Wl,-install_name,/usr/lib/swift/libswiftUniformTypeIdentifiers.dylib',
      '-Wl,-compatibility_version,1.0','-Wl,-current_version,877.5.1',
      '-o',darwin(build/'libswiftUniformTypeIdentifiers.dylib')],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Built Swift UTI values from 128 SDK definitions; Objective-C bridging remains absent.')
