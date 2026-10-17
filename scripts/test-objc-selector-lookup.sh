#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
# The enumeration test also rebuilds the combined adapter and checks that the
# selector addition preserves its existing class-enumeration behavior.
bash scripts/test-objc-class-enumeration.sh > logs/objc-class-enumeration-test.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/objc-selector-lookup.c -o artifacts/objc-selector-lookup.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lobjc -lSystem artifacts/objc-selector-lookup.o -o artifacts/objc-selector-lookup
timeout -k 5 60 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/objc-selector-lookup \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingObjCEnumeration.dylib \
    > logs/objc-selector-lookup-execute.log 2>&1
rg -q '^OBJC_SELECTOR_EXISTING_IDENTITY_UNKNOWN_NO_REGISTRATION_UTF8_AND_CONCURRENT_GROWTH_OK$' logs/objc-selector-lookup-execute.log
python3 scripts/build-objc-class-enumeration.py --test-bad-selector-guard \
    > logs/build-objc-selector-bad-guard.log 2>&1
status=0
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/objc-selector-lookup \
    /Volumes/SystemRoot/workspace/runtime/objc-class-enumeration/bad-selector-guard/libDarlingObjCEnumeration.dylib \
    > logs/objc-selector-bad-guard-execute.log 2>&1 || status=$?
if [[ $status == 0 || $status == 124 || $status == 137 ]]; then
    echo 'Bad runtime guard did not terminate before selector-table access.' >&2;exit 1
fi
rg -q '^Objective-C selector backend UUID/code/layout guard rejected incompatible runtime$' logs/objc-selector-bad-guard-execute.log
python3 - "$status" <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,sys
f=Path('artifacts/objc-class-enumeration.json');p=json.loads(f.read_text())
p.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_selector_lookup_execution_verified=True,
    concurrent_selector_growth_cases=12000,selector_worker_threads=4,
    unknown_selector_lookup_does_not_register=True,utf8_empty_and_independent_buffer_identity_verified=True,
    damaged_runtime_code_guard_rejected=True,damaged_guard_exit_status=int(sys.argv[1]))
f.write_text(json.dumps(p,indent=2)+'\n')
PY
