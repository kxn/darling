#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" -Xclang -fobjc-constant-literals \
    "$workspace/fixtures/hello/constant-numbers.m" -framework Foundation -framework CoreFoundation \
    -o "$workspace/artifacts/constant-numbers-smoke" > logs/constant-numbers-compile.log 2>&1
llvm-objdump-19 --macho --private-headers artifacts/constant-numbers-smoke > logs/constant-numbers-headers.log
rg -q '__objc_intobj' logs/constant-numbers-headers.log
rg -q '__objc_doubleobj' logs/constant-numbers-headers.log
timeout -k 5 30 bin/darling shell "$workspace/artifacts/constant-numbers-smoke" \
    > logs/constant-numbers-execute.log 2>&1
rg -q '^APPLE_CLANG_CONSTANT_NUMBERS_CONVERSIONS_CF_BRIDGE_HASH_DICTIONARY_OK$' logs/constant-numbers-execute.log
echo 'Original Apple clang constant NSNumber objects passed conversions, size rejection, CF bridging, equality, hash and dictionary lookup.'
