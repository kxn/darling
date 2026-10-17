#!/usr/bin/env python3
"""Compile unchanged Apple query/result value classes integrated into Darling."""
from pathlib import Path
import fcntl,hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent;config=json.loads((root/'config/security-out-of-band-values.json').read_text())
repo=root/'vendor/apple-security';legacy=root/'vendor/darling/src/external/security/OSX/sec/Security'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==config['source_commit']
sources={}
for name,sha in config['source_files'].items():
    data=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+name]);assert hashlib.sha256(data).hexdigest()==sha;sources[name]=data.decode()
source=legacy/'SecItemFetchOutOfBandValues.m';header=legacy/'SecItemFetchOutOfBandValues.h'
assert digest(source)==config['implementation_sha256'] and digest(header)==config['header_sha256']
for name in config['classes']:
    assert re.findall(r'@implementation '+name+r'\b.*?@end',source.read_text(),re.S)==re.findall(r'@implementation '+name+r'\b.*?@end',sources['OSX/sec/Security/SecItemFetchOutOfBand.m'],re.S)
    assert re.findall(r'@interface '+name+r'\b.*?@end',header.read_text(),re.S)==re.findall(r'@interface '+name+r'\b.*?@end',sources['keychain/headers/SecItemFetchOutOfBandPriv.h'],re.S)
build=root/'runtime/security-out-of-band-values';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
obj=build/'classes.o';library=build/'libDarlingSecurityOutOfBandValues.dylib';pending=library.with_suffix('.pending')
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fobjc-arc','-O2','-c',str(source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem','-install_name','/usr/lib/libDarlingSecurityOutOfBandValues.dylib',str(obj),'-o',str(pending)],check=True)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(library)
exports=re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(library)],text=True),re.M)
assert len(exports)==8 and all(name.startswith(('_OBJC_CLASS_$_','_OBJC_METACLASS_$_')) for name in exports)
record={'config':config,'sources':{str(p.relative_to(root)):digest(p) for p in [source,header,legacy/'CMakeLists.txt']},'library':str(library.relative_to(root)),'library_sha256':digest(library),'exports':exports,'runtime_execution_verified':False,'cloud_keychain_RPC_implemented':False,'full_Security_source_build':False,'full_xcode_build_ready':False}
(root/'artifacts/security-out-of-band-values-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built four unchanged Apple classes and',len(exports),'class/ivar exports; no RPC operations')
