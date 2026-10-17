#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/xpc-modern.c" \
    "$workspace/runtime/rebuilt-der/libDarlingDER.dylib" \
    -o "$workspace/artifacts/xpc-modern-smoke" > logs/xpc-modern-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/xpc-modern-smoke" > logs/xpc-modern-client-execute.log 2>&1
rg -q '^MODERN_XPC_DICTIONARY_ROUNDTRIP_OK$' logs/xpc-modern-client-execute.log
rg -q '^TYPED_ALLOCATION_REALLOC_PRESERVES_BYTES_OK$' logs/xpc-modern-client-execute.log
rg -q '^TYPED_CALLOC_ZEROES_AND_REJECTS_OVERFLOW_OK$' logs/xpc-modern-client-execute.log
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/spindump.c" \
    -framework CoreFoundation -o "$workspace/artifacts/spindump-abi-smoke" \
    > logs/spindump-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/spindump-abi-smoke" "$workspace/runtime/rebuilt-spindump/libspindump.dylib" \
    > logs/spindump-client-execute.log 2>&1
rg -q '^ORIGINAL_SPINDUMP_THRESHOLD_INITIALIZATION_OK$' logs/spindump-client-execute.log
echo 'Original spindump initialized its default Mach-time threshold; genuine XPC dictionary roundtrip passed. Sampling daemon functionality is unverified.'
