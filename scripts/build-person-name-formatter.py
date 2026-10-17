#!/usr/bin/env python3
"""Stage the pinned GNUstep formatter with explicit, limited API adaptations."""
from pathlib import Path
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/person-name-formatter-compat.json').read_text())
source=root/'vendor/gnustep-person-name'
for name,expected in config['files'].items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest()!=expected:
        raise ValueError('Changed pinned GNUstep source: '+name)
text=(source/'NSPersonNameComponentsFormatter.m').read_text()
start=text.index('- (NSString*) stringFromPersonNameComponents:')
end=text.index('- (NSPersonNameComponents*) personNameComponentsFromString:',start)
text=text[:start]+(root/'scripts/person-name-formatter-format.m.inc').read_text()+'\n'+text[end:]
# Preserve the upstream parser/coder as unverified functionality, while fixing
# its unconditional failure return and optional output pointer dereferences.
text=text.replace('      *obj = pnc;','      if (obj) *obj = pnc;').replace('      *obj = nil;','      if (obj) *obj = nil;')
text=text.replace('      *error =','      if (error) *error =')
assert text.count('  return NO;')==1
text=text.replace('  return NO;','  return pnc != nil;')
prefix='''#import <Foundation/Foundation.h>
#define RELEASE(x) [(x) release]
#define AUTORELEASE(x) [(x) autorelease]
@interface NSPersonNameComponentsFormatter () {
    BOOL _phonetic;
    NSPersonNameComponentsFormatterStyle _style;
    NSPersonNameComponentsFormatterOptions _nameOptions;
    NSLocale *_linuxcodeLocale;
}
@end
'''
build=root/'runtime/person-name-formatter';build.mkdir(exist_ok=True)
(build/'formatter.m').write_text(prefix+text)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19','-target','x86_64-apple-macos12','-isysroot',str(sdk),'-O2','-c',str(build/'formatter.m'),'-o',str(build/'formatter.o')],check=True)
destination=root/'runtime/native-library-stage/libDarlingPersonNameFormatter.dylib'
temporary=destination.with_name(destination.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','12','12',
    '-syslibroot',str(guest),'-L',str(root/'runtime/native-library-stage'),'-L',str(guest/'usr/lib'),
    '-lDarlingPersonName','-lSystem','-lobjc','-framework','Foundation',
    '-install_name','/usr/lib/libDarlingPersonNameFormatter.dylib',str(build/'formatter.o'),'-o',str(temporary)],check=True)
temporary.replace(destination)
print('Staged selected person-name formatting; no full locale/parser/annotation compatibility claim.')
