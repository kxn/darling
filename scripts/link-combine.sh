#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 60 bin/darling shell "$toolchain/usr/bin/clang++" \
    -dynamiclib -target x86_64-apple-macos14.0 -isysroot "$sdk" \
    "$workspace/runtime/build-combine/Combine.o" "$workspace/runtime/build-combine/helpers.o" \
    -L/usr/lib/swift -L"$toolchain/usr/lib/swift/macosx" \
    -lswiftCore -lswiftSwiftOnoneSupport -framework Foundation \
    -Wl,-dead_strip_dylibs \
    -Wl,-install_name,/System/Library/Frameworks/Combine.framework/Versions/A/Combine \
    -Wl,-compatibility_version,1.0 -Wl,-current_version,1.0 \
    -o "$workspace/runtime/build-combine/Combine"
