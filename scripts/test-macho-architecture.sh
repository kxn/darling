#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos15.4 -isysroot "$sdk" -DTARGET_OS_EXCLAVEKIT=0 -fblocks \
    -c fixtures/hello/macho-architecture.c -o runtime/dyld-cache-introspection/arch-test.o
ld64.lld-19 -arch x86_64 -platform_version macos 15.4 15.4 -syslibroot "$guest" -L "$guest/usr/lib" \
    -L runtime/native-library-stage -lSystem -lDarlingCacheIntrospection \
    runtime/dyld-cache-introspection/arch-test.o -o artifacts/macho-architecture
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/macho-architecture" > logs/macho-architecture-execute.log 2>&1
rg -q '^ORIGINAL_DYLD_ARCHITECTURE_METADATA_NAMES_ALIASES_FLAGS_UNKNOWN_MAIN_HEADER_OK 28$' logs/macho-architecture-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
p=Path('artifacts/dyld-cache-introspection.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingCacheIntrospection.dylib').read_bytes()).hexdigest()==r['library_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_architecture_metadata_execution_verified=True,
 architecture_name_cases=28,architecture_scope='Unmodified original dyld Architecture code, names/aliases/type/subtype/capability bits/unknown names and current header; metadata only, no ARM execution support.')
p.write_text(json.dumps(r,indent=2)+'\n')
PY
