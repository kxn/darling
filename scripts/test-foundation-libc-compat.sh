#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-foundation-libc-compat.py > logs/build-foundation-libc-compat.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/foundation-libc-compat.c -o artifacts/foundation-libc-compat.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem artifacts/foundation-libc-compat.o -o artifacts/foundation-libc-compat
timeout -k 5 60 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/foundation-libc-compat \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingFoundationSystem.dylib \
    > logs/foundation-libc-compat-execute.log 2>&1
rg -q '^FOUNDATION_LIBC_REAL_ENV_LOCK_THREADS_ZONE_ALLOCATIONS_AND_RECEIPT_QUERY_OK$' logs/foundation-libc-compat-execute.log
python3 scripts/build-foundation-libc-compat.py --test-bad-guard > logs/build-foundation-libc-bad-guard.log 2>&1
status=0
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/foundation-libc-compat \
    /Volumes/SystemRoot/workspace/runtime/foundation-libc-compat/bad-guard/libDarlingFoundationSystem.dylib --guard-only \
    > logs/foundation-libc-bad-guard-execute.log 2>&1 || status=$?
if [[ $status == 0 || $status == 99 || $status == 124 || $status == 137 ]]; then
    echo 'Bad libc guard did not terminate before private-function invocation.' >&2;exit 1
fi
rg -q '^Foundation libc backend UUID/code guard rejected incompatible runtime$' logs/foundation-libc-bad-guard-execute.log
python3 - "$status" <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,sys
text=Path('logs/foundation-libc-compat-execute.log').read_text()
assert text.index('FOUNDATION_LIBC_REAL_ENV_LOCK_THREADS_ZONE_ALLOCATIONS_AND_RECEIPT_QUERY_OK')<text.index('FOUNDATION_LIBC_EXIT_SECOND')<text.index('FOUNDATION_LIBC_EXIT_FIRST')
f=Path('artifacts/foundation-libc-compat.json');p=json.loads(f.read_text())
p.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_libc_api_execution_verified=True,
    existing_setenv_exclusion_and_4000_concurrent_snapshots_verified=True,
    default_zone_type_hint_allocation_reallocation_zeroing_and_overflow_verified=True,
    actual_unsupported_receipt_query_and_existing_exit_callback_order_verified=True,
    damaged_runtime_guard_rejected=True,damaged_guard_exit_status=int(sys.argv[1]))
f.write_text(json.dumps(p,indent=2)+'\n')
PY
