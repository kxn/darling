#!/usr/bin/env python3
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling';build=root/'runtime/launch-debug-gate';build.mkdir(exist_ok=True)
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/'scripts/launch-debug-gate.c'),'-o',str(build/'gate.o')],check=True)
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','-install_name','/usr/lib/libDarlingLaunchDebugGate.dylib',str(build/'gate.o'),'-o',str(build/'libDarlingLaunchDebugGate.dylib')],check=True)
