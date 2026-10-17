#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
sdk="$project/runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
cmake -S "$project/scripts/cryptokit-native" -B "$project/runtime/corecrypto-boringssl" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Darwin -DCMAKE_SYSTEM_PROCESSOR=x86_64 \
    -DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
    -DCMAKE_OSX_SYSROOT="$sdk" -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
    -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_ASM_COMPILER=clang-19 \
    -DCMAKE_C_COMPILER_TARGET=x86_64-apple-macos11.0 \
    -DCMAKE_CXX_COMPILER_TARGET=x86_64-apple-macos11.0 \
    -DCMAKE_ASM_COMPILER_TARGET=x86_64-apple-macos11.0 \
    -DCMAKE_CXX_FLAGS="-fno-exceptions -fno-rtti" \
    -DCMAKE_AR=/usr/bin/llvm-ar-19 -DCMAKE_RANLIB=/usr/bin/llvm-ranlib-19 \
    -DCRYPTO_SOURCE="$project/vendor/swift-crypto-3.15.1"
cmake --build "$project/runtime/corecrypto-boringssl" --parallel 8
