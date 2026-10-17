#!/usr/bin/env python3
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent.parent
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
folder=root/'runtime/legacy-volume-probe';folder.mkdir(exist_ok=True)
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-O0','-c',str(root/'fixtures/hello/legacy-volume-refs.c'),'-o',str(folder/'native.o')],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem','-framework','CoreServices','-framework','CoreFoundation',str(folder/'native.o'),'-o',str(folder/'native')],check=True)
