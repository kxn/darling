#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos11 \
    -isysroot "$sdk" -fobjc-arc -fblocks "$workspace/fixtures/hello/coreml-feature-values.m" \
    -framework Foundation -o "$workspace/artifacts/coreml-feature-values-smoke" \
    > logs/coreml-feature-values-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/coreml-feature-values-smoke" \
    "$workspace/runtime/native-framework-stage/CoreML.framework/CoreML" \
    > logs/coreml-feature-values-execute.log 2>&1
rg -q '^ORIGINAL_COREML_INT64_LIMITS_DOUBLE_STRING_UNDEFINED_EQUALITY_COPY_OK$' logs/coreml-feature-values-execute.log
echo 'Original CoreML feature-value factories, boundaries, typed values, equality and copy passed.'
