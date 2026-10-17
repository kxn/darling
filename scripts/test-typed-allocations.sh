#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang++" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/fixtures/hello/typed-allocation.cpp" \
    -o "$workspace/artifacts/typed-allocation-smoke" > logs/typed-allocation-client-compile.log 2>&1
timeout -k 5 30 bin/darling shell "$workspace/artifacts/typed-allocation-smoke" \
    "$workspace/runtime/rebuilt-der/libDarlingDER.dylib" > logs/typed-allocation-client-execute.log 2>&1
rg -q '^TYPED_CXX_NEW_ARRAY_DELETE_AND_BAD_ALLOC_OK$' logs/typed-allocation-client-execute.log
echo 'Typed C++ single/array allocation and deletion work; impossible allocation throws real bad_alloc.'
