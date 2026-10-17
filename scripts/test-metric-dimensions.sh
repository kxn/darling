#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/metric-dimensions.c -o artifacts/metric-dimensions-smoke.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem -lobjc artifacts/metric-dimensions-smoke.o -o artifacts/metric-dimensions-smoke
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="${METRICS_LIBRARY_PATH-$workspace/runtime/metrics-native-stage:$workspace/runtime/rebuilt-der}" \
    "$workspace/artifacts/metric-dimensions-smoke" \
    "${1-$workspace/runtime/metrics-native-stage/libDarlingMetrics.dylib}" \
    > logs/metric-dimensions-execute.log 2>&1
rg -q '^NATIVE_METRIC_DIMENSIONS_ADD_CAPACITY_REJECT_LIFECYCLE_OK$' logs/metric-dimensions-execute.log
echo 'Original metric dimensions create/add, capacity rejection and independent object release passed.'
