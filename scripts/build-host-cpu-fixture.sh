#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib -arch x86_64h -mmacosx-version-min=11 \
    -isysroot "$sdk" "$workspace/fixtures/hello/haswell-library.c" -O2 \
    -o "$workspace/artifacts/libHaswellCPUSmoke.dylib" > logs/haswell-library-compile.log 2>&1
llvm-objdump-19 --disassemble artifacts/libHaswellCPUSmoke.dylib > logs/haswell-library-disassembly.log
rg -q 'vpaddd.*%ymm' logs/haswell-library-disassembly.log
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos11 -isysroot "$sdk" \
    "$workspace/fixtures/hello/host-cpu.c" -o "$workspace/artifacts/host-cpu-smoke" > logs/host-cpu-compile.log 2>&1
