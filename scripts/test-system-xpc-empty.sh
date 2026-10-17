#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos15.4 -isysroot "$sdk" -c fixtures/hello/system-xpc-empty.c \
    -o runtime/dyld-cache-introspection/xpc-test.o
ld64.lld-19 -arch x86_64 -platform_version macos 15.4 15.4 -syslibroot "$guest" -L "$guest/usr/lib" \
    -lSystem runtime/dyld-cache-introspection/xpc-test.o -o artifacts/system-xpc-empty
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/system-xpc-empty" > logs/system-xpc-empty-execute.log 2>&1
rg -q '^SYSTEM_XPC_EMPTY_REAL_DICTIONARY_MUTATION_COPY_VALUES_INDEPENDENT_INSTANCES_OK$' logs/system-xpc-empty-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
p=Path('artifacts/dyld-cache-introspection.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingCacheIntrospection.dylib').read_bytes()).hexdigest()==r['library_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_system_empty_xpc_dictionary_execution_verified=True,
 empty_dictionary_scope='Actual existing libxpc allocation, type/count/string/int64/data/release, copied string input and independent dictionary instances via libSystem reexport.')
p.write_text(json.dumps(r,indent=2)+'\n')
PY
