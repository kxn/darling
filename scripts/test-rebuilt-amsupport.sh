#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/amsupport.m" \
    -framework Foundation -o "$workspace/artifacts/amsupport-abi-smoke" \
    > logs/amsupport-client-compile.log 2>&1
timeout 30 bin/darling shell "$workspace/artifacts/amsupport-abi-smoke" \
    "$workspace/runtime/rebuilt-amsupport/libamsupport.dylib" > logs/amsupport-client-execute.log 2>&1
rg -q '^ORIGINAL_AMSUPPORT_BASE64_KNOWN_VECTORS_OK$' logs/amsupport-client-execute.log
rg -q '^ORIGINAL_AMSUPPORT_LAZY_BINDING_EXECUTED_OK$' logs/amsupport-client-execute.log
rg -q '^ORIGINAL_AMSUPPORT_OBJC_METADATA_REGISTERED_OK$' logs/amsupport-client-execute.log
echo 'Original AMSupport: Base64 vectors, numeric conversion, lazy binding and Objective-C registration passed.'
