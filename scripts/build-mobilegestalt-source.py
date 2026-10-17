#!/usr/bin/env python3
"""Build the complete source MobileGestalt component with real version metadata."""
from pathlib import Path
import fcntl,hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
repo=root/'vendor/darling/src/libMobileGestalt';build=root/'runtime/mobilegestalt-source';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='vendor/darling/src/libMobileGestalt/src/MobileGestalt.m';header='vendor/darling/src/libMobileGestalt/include/MobileGestalt/MobileGestalt.h'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(repo/'include'),'-fblocks','-O2','-c',str(root/source),'-o',str(build/'MobileGestalt.o')],check=True)
output='runtime/mobilegestalt-source/libraries/libMobileGestalt.dylib';pending=root/(output+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem','-install_name','/usr/lib/libMobileGestalt.dylib','-compatibility_version','1.0.0','-current_version','1.0.0',str(build/'MobileGestalt.o'),'-o',str(pending)],check=True)
exports=lambda p:set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(p)],text=True),re.M))
original='runtime/rootfs/usr/libexec/darling/usr/lib/libMobileGestalt.dylib';old=exports(root/original);new=exports(pending);assert not old-new
assert new-old=={'_MobileGestalt_copy_humanReadableProductVersionString_obj'}
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/output)
record=dict(source=source,source_sha256=digest(source),header=header,header_sha256=digest(header),cmake='vendor/darling/src/libMobileGestalt/CMakeLists.txt',cmake_sha256=digest('vendor/darling/src/libMobileGestalt/CMakeLists.txt'),library=output,library_sha256=digest(output),object='runtime/mobilegestalt-source/MobileGestalt.o',object_sha256=digest('runtime/mobilegestalt-source/MobileGestalt.o'),original=original,original_sha256=digest(original),original_exports_preserved=len(old),added_exports=sorted(new-old),full_component_source_build=True,complete_source_files=1,installed=False,runtime_execution_verified=False,
 scope='Actual CoreFoundation system/supplemental metadata for ProductVersion and HumanReadableProductVersionString, including typed autoreleased wrapper. Existing unrelated hardware, device and notification stubs remain unsupported.')
(root/'artifacts/mobilegestalt-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built complete MobileGestalt source component and preserved',len(old),'existing exports')
