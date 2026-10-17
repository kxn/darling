#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fno-objc-arc -fblocks \
    -c fixtures/hello/dispatch-executor.m -o artifacts/dispatch-executor-smoke.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem -lobjc artifacts/dispatch-executor-smoke.o -o artifacts/dispatch-executor-smoke
timeout -k 5 30 bin/darling shell \
    /Volumes/SystemRoot/workspace/artifacts/dispatch-executor-smoke \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingQueueExecutor.dylib \
    > logs/dispatch-executor-execute.log 2>&1
rg -q '^DISPATCH_EXECUTOR_REAL_QUEUE_DATA_EVENT_AND_UNSUPPORTED_EXCLAVES_REJECTION_OK$' logs/dispatch-executor-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
file=Path('runtime/native-library-stage/libDarlingQueueExecutor.dylib')
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
    'load_mode':'RTLD_LAZY',
    'library_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
    'abi_inputs':json.loads(Path('config/dispatch-executor-abi.json').read_text()),
    'tests':['fieldless marker and serial ancestry','real serial queue and synchronous state',
        'real data-add source delivers 7','unsupported Exclaves source returns NULL and ENOTSUP'],
    'full_compatibility':False,
    'scope':'Opt-in process-local queue ancestry and source rejection. C backend remains Darling libdispatch; no Exclaves notification capability is provided.'}
Path('artifacts/dispatch-executor-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Fieldless executor ancestry preserves real queue/events; unsupported Exclaves creation returns ENOTSUP.'
