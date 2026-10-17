#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
for probe in runtime foundation async; do
    source=$probe
    compile_flags=()
    libraries=()
    case "$probe" in
        runtime) source=main ;;
        foundation) libraries=(-lswiftFoundation -framework Foundation) ;;
        async) compile_flags=(-parse-as-library); libraries=(-lswift_Concurrency) ;;
    esac
    output="$workspace/artifacts/swift-$probe-smoke"
    timeout 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
        "$workspace/fixtures/hello/$source.swift" "${compile_flags[@]}" \
        -target x86_64-apple-macos13.0 -sdk "$sdk" -module-name SwiftRuntimeProbe \
        -o "$output.o" > "logs/swift633-$probe-compile.log" 2>&1
    timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
        -target x86_64-apple-macos13.0 -isysroot "$sdk" "$output.o" \
        -L/usr/lib/swift -lswiftCore -lswiftSwiftOnoneSupport "${libraries[@]}" \
        -Wl,-rpath,/usr/lib/swift -o "$output" > "logs/swift633-$probe-link.log" 2>&1
    timeout 30 bin/darling shell "$output" > "logs/swift633-$probe-execute.log" 2>&1
done
rg -q '^SWIFT_RUNTIME_OK Darling/Swift/Linux$' logs/swift633-runtime-execute.log
rg -q '^SWIFT_FOUNDATION_OK 24$' logs/swift633-foundation-execute.log
rg -q '^SWIFT_CONCURRENCY_OK 36$' logs/swift633-async-execute.log
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" \
    "$workspace/fixtures/hello/demangle.c" -o "$workspace/artifacts/demangle-smoke" \
    > logs/demangle-client-compile.log 2>&1
timeout 30 bin/darling shell "$workspace/artifacts/demangle-smoke" > logs/demangle-client-execute.log 2>&1
rg -q '^ORIGINAL_APPLE_DEMANGLER_OK$' logs/demangle-client-execute.log
echo 'Original Xcode frontend compiled and executed Swift collections, Foundation JSON and an async task group.'
