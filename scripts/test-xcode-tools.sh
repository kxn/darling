#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p artifacts logs
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks -O2 \
    -c fixtures/hello/dispatch-lock.c -o artifacts/dispatch-lock.o
ld64.lld-19 -arch x86_64 -platform_version macos 11.0 11.0 \
    -syslibroot runtime/rootfs/usr/libexec/darling \
    -L runtime/rootfs/usr/libexec/darling/usr/lib -lSystem \
    -o artifacts/dispatch-lock artifacts/dispatch-lock.o
timeout 60 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/dispatch-lock \
    > logs/dispatch-lock-regression.log 2>&1
rg -q '^counter=32$' logs/dispatch-lock-regression.log
timeout 60 bin/xcodebuild -version > logs/xcodebuild-version.log 2>&1
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin
developer=/Applications/Xcode.app/Contents/Developer
source_file=/Volumes/SystemRoot/workspace/fixtures/hello/main.c
for platform in ios macos; do
    if [[ $platform == ios ]]; then
        target=arm64-apple-ios15.0
        platform_sdk="$developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk"
    else
        target=x86_64-apple-macos11
        platform_sdk="$developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
    fi
    timeout 60 bin/darling shell "$toolchain/clang" -target "$target" \
        -isysroot "$platform_sdk" "$source_file" \
        -o "/Volumes/SystemRoot/workspace/artifacts/hello-$platform" \
        > "logs/clang-$platform-link.log" 2>&1
done
timeout 60 bin/darling shell "$toolchain/clang++" -target arm64-apple-ios15.0 \
    -isysroot "$developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk" \
    -std=c++17 -g -c /Volumes/SystemRoot/workspace/fixtures/hello/main.cpp \
    -o /Volumes/SystemRoot/workspace/artifacts/hello-cpp-ios.o \
    > logs/clang-cpp-ios-compile.log 2>&1
timeout 60 bin/darling shell "$toolchain/clang++" -target arm64-apple-ios15.0 \
    -isysroot "$developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk" \
    /Volumes/SystemRoot/workspace/artifacts/hello-cpp-ios.o \
    -o /Volumes/SystemRoot/workspace/artifacts/hello-cpp-ios \
    > logs/clang-cpp-ios-link.log 2>&1
if [[ -e artifacts/hello-cpp-ios.dSYM ]]; then
    mv artifacts/hello-cpp-ios.dSYM "runtime/previous-hello-cpp-ios.dSYM.$(date +%s%N)"
fi
timeout 60 bin/darling shell "$toolchain/dsymutil" \
    /Volumes/SystemRoot/workspace/artifacts/hello-cpp-ios \
    -o /Volumes/SystemRoot/workspace/artifacts/hello-cpp-ios.dSYM \
    > logs/dsymutil-ios.log 2>&1
llvm-dwarfdump-19 --debug-info artifacts/hello-cpp-ios.dSYM/Contents/Resources/DWARF/hello-cpp-ios \
    > logs/dsymutil-dwarf.log
rg -q 'DW_TAG_subprogram' logs/dsymutil-dwarf.log
file artifacts/hello-ios | rg -q 'Mach-O 64-bit arm64 executable'
file artifacts/hello-macos | rg -q 'Mach-O 64-bit x86_64 executable'
llvm-objdump-19 --macho --private-headers artifacts/hello-ios > logs/hello-ios-headers.log
rg -q 'platform ios' logs/hello-ios-headers.log
timeout 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/hello-macos \
    > logs/hello-macos-run.log 2>&1
rg -q '^Hello from the original Apple toolchain on Linux$' logs/hello-macos-run.log
timeout 60 bin/darling shell "$toolchain/clang++" -target x86_64-apple-macos11 \
    -isysroot "$developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk" \
    -std=c++17 /Volumes/SystemRoot/workspace/fixtures/hello/bad-function-call.cpp \
    -o /Volumes/SystemRoot/workspace/artifacts/bad-function-call \
    > logs/bad-function-call-compile.log 2>&1
timeout 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/bad-function-call \
    > logs/bad-function-call-execute.log 2>&1
rg -q '^REAL_BAD_FUNCTION_CALL_THROW_CATCH_COPY_WHAT_OK$' logs/bad-function-call-execute.log
echo 'Parallel locks, original xcodebuild version, iOS C/C++ compile/link/dSYM, and macOS compile/link/run passed.'
