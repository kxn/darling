#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos15.4 -isysroot "runtime/state/prefix$sdk" \
    -c fixtures/hello/swift-executor-query.c -o artifacts/swift-executor-query.o
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/swift-dispatch.swift" -target x86_64-apple-macos15.4 -sdk "$sdk" \
    -module-name OriginalDispatchProbe -o "$workspace/artifacts/swift-dispatch-smoke.o" \
    > logs/swift-dispatch-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" "$workspace/artifacts/swift-dispatch-smoke.o" "$workspace/artifacts/swift-executor-query.o" -L/usr/lib/swift \
    -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftSwiftOnoneSupport -lswiftDispatch -lswift_Concurrency \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/swift-dispatch-smoke" \
    > logs/swift-dispatch-link.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    LINUXCODE_DISPATCH_TEST_TRACE=1 \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/swift-dispatch-smoke" > logs/swift-dispatch-execute.log 2>&1
rg -q '^ORIGINAL_SWIFT_DISPATCH_QUEUE_SPECIFIC_ASYNC_GROUP_TIMEOUT_THROW_OK$' logs/swift-dispatch-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
build=Path('runtime/rebuilt-swift-dispatch');r=json.loads((build/'reconstruction.json').read_text())
staged=Path('runtime/native-library-stage/libswiftDispatch.dylib')
if hashlib.sha256(staged.read_bytes()).hexdigest()!=r['staged_image_sha256']:
    raise ValueError('Executed Swift Dispatch stage differs from reconstruction report')
def exports(file):return {line.split()[-1] for line in subprocess.check_output([
    'llvm-nm-19','--extern-only','--defined-only',str(file)],text=True).splitlines() if line.split()}
old=exports(Path('runtime/rootfs/usr/libexec/darling/usr/lib/swift/libswiftDispatch.dylib'))
new=exports(staged);missing={name for name in old-new if not name.startswith('$ld$')}
if missing:raise ValueError('Original old Dispatch exports missing: '+str(sorted(missing)))
report={'checked_at':datetime.now(timezone.utc).isoformat(),
    'original_image_sha256':r['original_image_sha256'],'staged_image_sha256':r['staged_image_sha256'],
    'transport_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingQueueExecutor.dylib').read_bytes()).hexdigest(),
    'installed':False,'load_verified':True,'selected_api_execution_verified':True,
    'old_exports_preserved':len(old),'backend_role_overrides':r['backend_call_overrides'],
    'tests':['queue-specific values and synchronous result','64 asynchronous group jobs sum to 2080',
        'real semaphore timeout and success','throwing sync preserves Swift error',
        'genuine DispatchSerialQueue creation','64 custom actor updates on the declared serial executor',
        '64 yielding task-group children on the preferred concurrent task executor',
        'actual Swift serial executor ref matches actor and is generic during task execution'],
    'full_compatibility':False,
    'scope':'Selected original SDK APIs with a real GCD/Swift-runtime job transport. Complete QoS behavior, timers, I/O source coverage and full Dispatch compatibility unverified; Exclaves sources explicitly unsupported.'}
Path('artifacts/swift-dispatch-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original Swift Dispatch passed queues/groups, timeouts, errors, custom actor execution and task executor preference.'
