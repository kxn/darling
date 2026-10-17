#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p runtime/build-applearchive
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib -std=c11 -O2 \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" \
    "$workspace/scripts/applearchive-bytestream.c" \
    -Wl,-install_name,/usr/lib/libAppleArchive.dylib \
    -Wl,-compatibility_version,1.0 -Wl,-current_version,1.0 \
    -o "$workspace/runtime/build-applearchive/libAppleArchive.dylib" \
    > logs/build-applearchive.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" \
    "$workspace/fixtures/hello/applearchive.c" -lAppleArchive \
    -o "$workspace/artifacts/applearchive-abi-smoke" > logs/applearchive-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/build-applearchive" \
    "$workspace/artifacts/applearchive-abi-smoke" > logs/applearchive-client-execute.log 2>&1
rg -q '^APPLEARCHIVE_FILE_STREAM_OK$' logs/applearchive-client-execute.log
cp runtime/build-applearchive/libAppleArchive.dylib runtime/state/prefix/usr/lib/libAppleArchive.dylib
echo 'Installed tested AppleArchive file/custom byte-stream subset; archive encoding and compression remain absent.'
