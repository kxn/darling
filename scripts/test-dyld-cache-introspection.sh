#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/prepare-dyld-cache-oracle.py
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos15.4 -isysroot "$sdk" -DTARGET_OS_EXCLAVEKIT=0 -fblocks \
    -I vendor/apple-dyld/include -c fixtures/hello/dyld-cache-introspection.c -o runtime/dyld-cache-introspection/test.o
ld64.lld-19 -arch x86_64 -platform_version macos 15.4 15.4 -syslibroot "$guest" -L "$guest/usr/lib" \
    -L runtime/native-library-stage -lSystem -lDarlingCacheIntrospection \
    runtime/dyld-cache-introspection/test.o -o artifacts/dyld-cache-introspection
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 45 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/dyld-cache-introspection" \
    "$workspace/runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h" \
    "$workspace/runtime/dyld-introspection-fixture" "$workspace/runtime/dyld-introspection-empty" \
    "$workspace/runtime/dyld-cache-introspection/invalid-cache" \
    "$workspace/runtime/dyld-cache-introspection/missing-subcache/dyld_shared_cache_x86_64h" \
    "$workspace/runtime/dyld-cache-introspection/wrong-subcache-uuid/dyld_shared_cache_x86_64h" \
    > logs/dyld-cache-introspection-execute.log 2>&1
rg -q '^REAL_SPLIT_INTEL_CACHE_UUID_FILES_IMAGES_SEGMENTS_CONTENT_EMPTY_BAD_INPUT_DEDUP_OK$' logs/dyld-cache-introspection-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
p=Path('artifacts/dyld-cache-introspection.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingCacheIntrospection.dylib').read_bytes()).hexdigest()==r['library_sha256']
assert hashlib.sha256(Path('runtime/native-library-stage/libSystem.B.dylib').read_bytes()).hexdigest()==r['libsystem_stage_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_read_only_cache_execution_verified=True,
 oracle=json.loads(Path('runtime/dyld-cache-introspection/oracle.json').read_text()),
 tests=['actual empty installed-cache set','empty alternate root','malformed/missing files reject without callback',
  'actual seven-file cache metadata and 3626 image identities','selected original UUID, segments and raw content',
  'alternate-root enumeration deduplicates directory symlinks','libSystem reexport resolves the real implementation',
  'missing subcache and wrong subcache UUID reject without a callback'])
p.write_text(json.dumps(r,indent=2)+'\n')
PY
