#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/swift-os.swift" -target x86_64-apple-macos14.0 -sdk "$sdk" \
    -module-name SwiftOSProbe -o "$workspace/artifacts/swift-os-smoke.o" \
    > logs/swift-os-client-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/artifacts/swift-os-smoke.o" -L/usr/lib/swift \
    -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftSwiftOnoneSupport -lswiftos \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/swift-os-smoke" \
    > logs/swift-os-client-link.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="${SWIFT_OS_LIBRARY_PATH-$workspace/runtime/rebuilt-swift-os:$workspace/runtime/metrics-native-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift}" \
    "$workspace/artifacts/swift-os-smoke" > logs/swift-os-client-execute.log 2>&1
rg -q '^ORIGINAL_SWIFT_OS_LOGGER_INTERPOLATION_REFLECTION_GENERIC_LOCK_OK$' logs/swift-os-client-execute.log
echo 'Original Swift os library passed SDK-client interpolation/reflection, Logger construction/call, and generic lock state mutation.'
