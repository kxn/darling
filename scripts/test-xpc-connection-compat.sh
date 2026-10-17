#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
unset LINUXCODE_DARLING_SERVER LINUXCODE_LIBXPC LINUXCODE_LAUNCHD LINUXCODE_LIBSYSTEM_KERNEL LINUXCODE_QUARANTINE LINUXCODE_SANDBOX
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/xpc-connection-compat.c -o artifacts/xpc-connection-compat.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -L "$guest/usr/lib/system" -lSystem -lxpc \
    artifacts/xpc-connection-compat.o -o artifacts/xpc-connection-compat
timeout -k 5 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-connection-compat \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingXPCRichError.dylib \
    > logs/xpc-connection-compat.log 2>&1
rg -q '^XPC_32_REAL_CONNECTION_INVALIDATIONS_OWNED_REASONS_AND_UNSUPPORTED_REQUIREMENTS_OK$' logs/xpc-connection-compat.log
python3 scripts/build-xpc-rich-error.py --test-bad-connection-guard > logs/build-xpc-bad-connection-guard.log 2>&1
status=0
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-connection-compat \
    /Volumes/SystemRoot/workspace/runtime/xpc-rich-error/bad-connection-guard/libDarlingXPCRichError.dylib --guard-only \
    > logs/xpc-bad-connection-guard.log 2>&1 || status=$?
if [[ $status == 0 || $status == 99 || $status == 124 || $status == 137 ]]; then
    echo 'Bad XPC runtime guard did not terminate before private state access.' >&2;exit 1
fi
rg -q '^XPC connection backend UUID/code/layout guard rejected incompatible runtime$' logs/xpc-bad-connection-guard.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/xpc-rich-error-compat.json');j=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingXPCRichError.dylib').read_bytes()).hexdigest()==j['library_sha256']
j.update(connection_checked_at=datetime.now(timezone.utc).isoformat(),
    selected_connection_invalidation_execution_verified=True,
    actual_cancel_events_independent_owned_reason_buffers_verified=32,
    peer_signing_requirement_explicitly_unsupported=True,
    damaged_connection_runtime_guard_rejected=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
