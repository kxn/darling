#!/usr/bin/env python3
"""Keep existing Darling private exports alongside the genuine Foundation."""
from pathlib import Path
import hashlib,json,re,subprocess
project=Path(__file__).resolve().parent.parent
config=json.loads((project/'config/legacy-foundation-exports.json').read_text())
source=project/'vendor/darling/src/external/foundation'
if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=config['source_commit']:
    raise ValueError('Changed legacy Foundation source revision')
for relative,digest in config['files'].items():
    if hashlib.sha256((source/relative).read_bytes()).hexdigest()!=digest:raise ValueError('Changed legacy Foundation source: '+relative)
build=project/'runtime/legacy-foundation-exports';headers=build/'Foundation';headers.mkdir(parents=True,exist_ok=True)
(headers/'NSSpellEngine.h').write_bytes((source/'include/Foundation/NSSpellEngine.h').read_bytes())
# The original base class only logs unimplemented spelling operations. Retain
# its registry/delegation implementation but make those unsupported operations
# raise rather than returning success-shaped empty results.
(headers/'NSRaise.h').write_text('#import <Foundation/Foundation.h>\n#define NSUnimplementedMethod() '
    '[NSException raise:NSInternalInconsistencyException format:@"Darling spelling operation unavailable"]\n')
(build/'prefix.h').write_text('#import <Foundation/Foundation.h>\n#include <objc/runtime.h>\n')
platform=(source/'src/NSPlatform_darwin.m').read_text()
matches=re.findall(r'^NSString \*const NSPlatformResourceNameSuffix = @"darwin";$',platform,re.M)
if len(matches)!=1:raise ValueError('Changed actual platform resource suffix')
(build/'platform.m').write_text('#import <Foundation/Foundation.h>\n'+matches[0]+'\n')
sdk=project/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
objects=[]
for path,name in [(source/'src/NSSpellEngine.m','spell-engine'),(build/'platform.m','platform')]:
    obj=build/(name+'.o');objects.append(str(obj))
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I',str(build),
        '-include',str(build/'prefix.h'),'-fblocks','-O2','-c',str(path),'-o',str(obj)],check=True)
guest=project/'runtime/rootfs/usr/libexec/darling';output=project/'runtime/native-library-stage/libDarlingLegacyFoundation.dylib'
temporary=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-F',str(project/'runtime/foundation-native-framework-stage'),
    '-L',str(guest/'usr/lib'),'-lSystem','-lobjc','-framework','Foundation',
    '-install_name','/usr/lib/libDarlingLegacyFoundation.dylib',*objects,'-o',str(temporary)],check=True)
temporary.replace(output)
(project/'artifacts/legacy-foundation-exports.json').write_text(json.dumps(dict(installed=False,
    full_compatibility=False,selected_api_execution_verified=False,scope=config['scope'],
    source_commit=config['source_commit'],library_sha256=hashlib.sha256(output.read_bytes()).hexdigest()),indent=2)+'\n')
print('Built existing private Foundation base class and platform suffix')
