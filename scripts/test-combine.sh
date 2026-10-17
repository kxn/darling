#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
stage=runtime/build-combine/Frameworks/Combine.framework
mkdir -p "$stage/Versions/A"
cp runtime/build-combine/Combine "$stage/Versions/A/Combine"
ln -sfn A "$stage/Versions/Current"
ln -sfn Versions/Current/Combine "$stage/Combine"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
# Deliberately import Apple's SDK module, never our emitted Swift module.
timeout 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/combine.swift" -target x86_64-apple-macos14.0 -sdk "$sdk" \
    -module-name CombineABISmoke -o "$workspace/artifacts/combine-abi-smoke.o" \
    > logs/combine-client-compile.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/artifacts/combine-abi-smoke.o" \
    -L/usr/lib/swift -lswiftCore -lswiftSwiftOnoneSupport -framework Combine -framework Foundation \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/combine-abi-smoke" \
    > logs/combine-client-link.log 2>&1
timeout 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/build-combine/Frameworks" \
    "$workspace/artifacts/combine-abi-smoke" > logs/combine-client-execute.log 2>&1
rg -q '^COMBINE_MAP_CATCH_FUTURE_DEMAND_CANCEL_OK$' logs/combine-client-execute.log
echo 'Original Combine SDK client passed map/catch, deferred Future, demand, cancellation and type erasure.'
