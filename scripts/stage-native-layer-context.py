#!/usr/bin/env python3
"""Build the real bitmap CALayerContext extension and stage explicit class exports."""
from pathlib import Path
import fcntl,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
build=root/'runtime/native-layer-context';libraries=build/'libraries';libraries.mkdir(parents=True,exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling';cocotron=root/'vendor/darling/src/external/cocotron'
source='vendor/darling/src/external/cocotron/QuartzCore/CALayerContextNative.m';header='vendor/darling/src/external/cocotron/QuartzCore/include/QuartzCore/CALayerContext.h';obj=build/'CALayerContextNative.o'
include=build/'include'
for relative,original in [('QuartzCore/CALayerContext.h',root/header),('CoreGraphics/CGSubWindow.h',cocotron/'CoreGraphics/include/CoreGraphics/CGSubWindow.h')]:
 target_header=include/relative;target_header.parent.mkdir(parents=True,exist_ok=True)
 if not target_header.is_symlink():target_header.symlink_to(original)
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(include),'-O2','-fblocks','-c',str(root/source),'-o',str(obj)],check=True)
helper='runtime/native-layer-context/libraries/libDarlingNativeLayerContext.dylib';pending=root/(helper+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-framework','CoreGraphics','-lobjc','-lSystem','-install_name','/usr/lib/libDarlingNativeLayerContext.dylib',str(obj),'-o',str(pending)],check=True)
base='runtime/quartzcore-native/frameworks/QuartzCore.framework/Versions/A/QuartzCore'
api=runpy.run_path(str(root/'scripts/macho-named-reexport.py'))
payload,changes=api['add']((root/base).read_bytes(),'/usr/lib/libDarlingNativeLayerContext.dylib',['_OBJC_CLASS_$_CALayerContext','_OBJC_METACLASS_$_CALayerContext'])
output='runtime/native-layer-context/frameworks/QuartzCore.framework/Versions/A/QuartzCore';target=root/output;target.parent.mkdir(parents=True,exist_ok=True)
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(root/helper);temp=target.with_suffix('.pending');temp.write_bytes(payload);temp.replace(target)
framework=target.parent.parent.parent
for p,t in [(framework/'QuartzCore','Versions/Current/QuartzCore'),(framework/'Versions/Current','A')]:
 if not p.is_symlink():p.symlink_to(t)
report=dict(base=base,base_sha256=digest(base),library=output,library_sha256=digest(output),helper=helper,helper_sha256=digest(helper),source=source,source_sha256=digest(source),header=header,header_sha256=digest(header),export_changes=changes,installed=False,runtime_execution_verified=False,full_xcode_build_ready=False)
(root/'artifacts/native-layer-context-stage.json').write_text(json.dumps(report,indent=2)+'\n');print('Staged source bitmap CALayerContext alongside original QuartzCore')
