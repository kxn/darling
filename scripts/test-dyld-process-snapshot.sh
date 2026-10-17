#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
printf '%s\n' 'int linuxcode_snapshot_marker(void) { return 731; }' > runtime/dyld-cache-introspection/fixture.c
clang-19 -target x86_64-apple-macos15.4 -isysroot "$sdk" -c runtime/dyld-cache-introspection/fixture.c \
    -o runtime/dyld-cache-introspection/fixture.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 15.4 15.4 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -install_name /usr/lib/libLinuxcodeSnapshotFixture.dylib \
    runtime/dyld-cache-introspection/fixture.o -o runtime/dyld-cache-introspection/fixture.dylib
clang-19 -target x86_64-apple-macos15.4 -isysroot "$sdk" -DTARGET_OS_EXCLAVEKIT=0 -fblocks \
    -c fixtures/hello/dyld-process-snapshot.c -o runtime/dyld-cache-introspection/process-test.o
ld64.lld-19 -arch x86_64 -platform_version macos 15.4 15.4 -syslibroot "$guest" -L "$guest/usr/lib" \
    -L runtime/native-library-stage -lSystem -lDarlingCacheIntrospection \
    runtime/dyld-cache-introspection/process-test.o -o artifacts/dyld-process-snapshot
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 45 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/dyld-process-snapshot" "$workspace/runtime/dyld-cache-introspection/fixture.dylib" \
    > logs/dyld-process-snapshot-execute.log 2>&1
rg -q '^REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK ' logs/dyld-process-snapshot-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
p=Path('artifacts/dyld-cache-introspection.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingCacheIntrospection.dylib').read_bytes()).hexdigest()==r['library_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_current_process_snapshot_execution_verified=True,
 process_tests=['actual current Mach task via existing legacy dyld backend','invalid task propagates kernel failure',
  'main image UUID/slid segments/disk content match actual loader','dlopen/dlclose update new snapshots',
  'older snapshots preserve their image set','snapshot survives process-handle disposal','task send-right counts balance'],
 remote_task_snapshots_execution_verified=False)
p.write_text(json.dumps(r,indent=2)+'\n')
PY
