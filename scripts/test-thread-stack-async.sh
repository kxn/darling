#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "runtime/state/prefix$sdk" \
    -O0 -fno-omit-frame-pointer -c fixtures/hello/thread-stack-async.c -o artifacts/thread-stack-ordinary.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem artifacts/thread-stack-ordinary.o -o artifacts/thread-stack-ordinary
timeout -k 5 45 bin/darling shell "$workspace/artifacts/thread-stack-ordinary" \
    "$workspace/runtime/native-library-stage/libDarlingFoundationSystem.dylib" > logs/thread-stack-ordinary.log 2>&1
clang-19 -target x86_64-apple-macos15.4 -isysroot "runtime/state/prefix$sdk" \
    -O0 -fno-omit-frame-pointer -DLINUXCODE_SWIFT_STACK_CLIENT \
    -c fixtures/hello/thread-stack-async.c -o artifacts/thread-stack-bridge.o
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/thread-stack-async.swift" -parse-as-library \
    -import-objc-header "$workspace/fixtures/hello/thread-stack-async.h" \
    -target x86_64-apple-macos15.4 -sdk "$sdk" -module-name AsyncStackProbe \
    -o "$workspace/artifacts/thread-stack-async.o" > logs/thread-stack-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" "$workspace/artifacts/thread-stack-async.o" "$workspace/artifacts/thread-stack-bridge.o" \
    -L/usr/lib/swift -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftSwiftOnoneSupport -lswift_Concurrency \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/thread-stack-async" > logs/thread-stack-link.log 2>&1
timeout -k 5 45 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH=/usr/lib/swift \
    "$workspace/artifacts/thread-stack-async" "$workspace/runtime/native-library-stage/libDarlingFoundationSystem.dylib" \
    > logs/thread-stack-async.log 2>&1
rg -q '^APPLE_THREAD_STACK_ORDINARY_CAPACITY_0_TO_64_AND_FOUR_THREADS_OK$' logs/thread-stack-ordinary.log
rg -q '^APPLE_THREAD_STACK_64_REAL_SWIFT_ASYNC_TASK_IDS_AND_BOUNDED_FRAMES_OK$' logs/thread-stack-async.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/foundation-libc-compat.json');j=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingFoundationSystem.dylib').read_bytes()).hexdigest()==j['library_sha256']
j.update(thread_stack_checked_at=datetime.now(timezone.utc).isoformat(),
    selected_thread_stack_execution_verified=True,
    ordinary_capacity_0_through_64_and_four_threads_verified=True,
    actual_64_swift_async_task_ids_and_capacity_guards_verified=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
