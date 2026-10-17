#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/extract-der-functions.py > logs/extract-der-functions.log 2>&1
clang++-19 -target x86_64-apple-macos14.0 -O2 -c scripts/der-allocation-compat.cpp \
    -o runtime/rebuilt-der/allocation.o
clang-19 -target x86_64-apple-macos14.0 -O2 -c scripts/xpc-modern-compat.c \
    -o runtime/rebuilt-der/xpc.o
clang-19 -target x86_64-apple-macos14.0 -O2 -c scripts/security-constants-compat.c \
    -o runtime/rebuilt-der/security-constants.o
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang++" -dynamiclib \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" \
    "$workspace/runtime/rebuilt-der/der.o" "$workspace/runtime/rebuilt-der/allocation.o" \
    "$workspace/runtime/rebuilt-der/xpc.o" "$workspace/runtime/rebuilt-der/security-constants.o" \
    -framework CoreFoundation \
    -Wl,-install_name,/usr/lib/libDarlingDER.dylib -Wl,-compatibility_version,1.0 \
    -Wl,-current_version,1.0 -o "$workspace/runtime/rebuilt-der/libDarlingDER.dylib" \
    > logs/link-der-adapter.log 2>&1
echo 'Staged original Apple DER functions with typed-allocation forwarding; not installed.'
