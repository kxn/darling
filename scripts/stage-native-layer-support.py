#!/usr/bin/env python3
"""Stage source-backed CoreGraphics helpers needed by genuine CALayer."""
from pathlib import Path
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
base='runtime/foundation-native-framework-stage/CoreGraphics.framework/Versions/A/CoreGraphics'
build=root/'runtime/native-layer-support';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
source='vendor/darling/src/external/cocotron/CoreGraphics/CGFloat.c';obj=build/'CGFloat.o';helper='runtime/native-layer-support/libraries/libDarlingCGFloat.dylib';pending=root/(helper+'.pending')
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','-install_name','/usr/lib/libDarlingCGFloat.dylib',str(obj),'-o',str(pending)],check=True)
context_source='vendor/darling/src/external/cocotron/CoreGraphics/CGContextNativeLayer.m';context_obj=build/'CGContextNativeLayer.o'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(root/'vendor/darling/src/external/cocotron/Onyx2D/include'),'-fblocks','-O2','-c',str(root/context_source),'-o',str(context_obj)],check=True)
old=json.loads((root/'artifacts/cgs-accelerator.json').read_text());production=root/'runtime/cgs-accelerator/production.o'
assert digest('runtime/cgs-accelerator/production.o')==old['object_sha256']
backend=root/'runtime/foundation-native-library-stage/libDarlingCoreGraphicsBackend.dylib';assert digest(str(backend.relative_to(root)))==old['stage_backend_sha256']
output='runtime/native-layer-support/frameworks/CoreGraphics.framework/Versions/A/CoreGraphics';target=root/output;target.parent.mkdir(parents=True,exist_ok=True)
facade_pending=target.with_suffix('.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','-F',str(guest/'System/Library/Frameworks'),'-framework','IOKit','-F',str(guest/'System/Library/PrivateFrameworks'),'-framework','Onyx2D','-framework','Foundation','-lobjc','-install_name','/System/Library/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics','-compatibility_version','64.0.0','-current_version','1070.22.0','-headerpad','0x1000','-reexport_library',str(backend),str(production),str(obj),str(context_obj),'-o',str(facade_pending)],check=True)
changes=dict(added_names=['_CGFloatIsValid','_CGContextGetBaseCTM','_CGContextSetBaseCTM'],existing_accelerator_source_object_preserved=True,full_backend_reexport_preserved=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);facade_pending.replace(target)
framework=target.parent.parent.parent
for p,t in [(framework/'CoreGraphics','Versions/Current/CoreGraphics'),(framework/'Versions/Current','A')]:
 if not p.is_symlink():p.symlink_to(t)
record=dict(context_source=context_source,context_source_sha256=digest(context_source),accelerator_object_sha256=digest('runtime/cgs-accelerator/production.o'),backend_sha256=digest(str(backend.relative_to(root))),base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),helper=helper,helper_sha256=digest(helper),source=source,source_sha256=digest(source),export_changes=changes,installed=False,runtime_execution_verified=False)
(root/'artifacts/native-layer-support-stage.json').write_text(json.dumps(record,indent=2)+'\n');print('Staged source CGFloat validation in a private CoreGraphics facade')
