#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
unset LINUXCODE_DARLING_SERVER LINUXCODE_LIBXPC LINUXCODE_LAUNCHD LINUXCODE_LIBSYSTEM_KERNEL LINUXCODE_QUARANTINE LINUXCODE_SANDBOX
python3 scripts/build-xpc-rich-error.py > logs/build-xpc-rich-error.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/xpc-rich-error.c -o artifacts/xpc-rich-error.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -L "$guest/usr/lib/system" -lSystem -lxpc \
    artifacts/xpc-rich-error.o -o artifacts/xpc-rich-error
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/xpc-rich-error \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingXPCRichError.dylib \
    > logs/xpc-rich-error-execute.log 2>&1
rg -q '^XPC_RICH_ERROR_ACTUAL_OBJECTS_COPY_RETRY_RETAIN_AND_PEER_ERROR_OK$' logs/xpc-rich-error-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json
f=Path('artifacts/xpc-rich-error-compat.json');p=json.loads(f.read_text())
p.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_error_api_execution_verified=True,
    selected_error_cases=160,peer_error_global_type_description_retain_verified=True,
    peer_error_copied_dictionary_contents_isolation_verified=True,
    known_base_limit='Existing Darling OS_xpc_error.copy produces OS_xpc_dictionary; error type preservation is not fixed by this adapter.')
f.write_text(json.dumps(p,indent=2)+'\n')
PY
