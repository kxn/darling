#!/usr/bin/env bash
# Builds an opt-in experiment library; never installs into the prefix.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import hashlib,json
c=json.loads(Path('config/dispatch-executor-abi.json').read_text())
for file,key in [('runtime/rootfs/usr/libexec/darling/usr/lib/system/libdispatch.dylib','darling_dispatch_sha256'),
                 ('runtime/fullsystem-libraries/usr/lib/system/libdispatch.dylib','reference_dispatch_sha256')]:
    if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=c[key]:
        raise ValueError('Unexpected dispatch ABI input: '+file)
PY
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
mkdir -p runtime/build-dispatch-executor runtime/native-library-stage
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fno-objc-arc \
    -c scripts/dispatch-executor-compat.m -o runtime/build-dispatch-executor/marker.o
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c scripts/dispatch-job-compat.c -o runtime/build-dispatch-executor/job.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11 11 \
    -install_name /usr/lib/libDarlingQueueExecutor.dylib \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem -lobjc -lFND runtime/build-dispatch-executor/marker.o runtime/build-dispatch-executor/job.o \
    -o runtime/build-dispatch-executor/libDarlingQueueExecutor.dylib
cp runtime/build-dispatch-executor/libDarlingQueueExecutor.dylib runtime/native-library-stage/libDarlingQueueExecutor.dylib.pending
mv runtime/native-library-stage/libDarlingQueueExecutor.dylib.pending runtime/native-library-stage/libDarlingQueueExecutor.dylib
