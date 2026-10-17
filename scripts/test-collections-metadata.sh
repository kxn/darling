#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/collections-metadata.c -o artifacts/collections-metadata-smoke.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem artifacts/collections-metadata-smoke.o -o artifacts/collections-metadata-smoke
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH=/usr/lib/swift \
    "$workspace/artifacts/collections-metadata-smoke" \
    "$workspace/runtime/rebuilt-collectionsinternal/CollectionsInternal" \
    > logs/collections-metadata-execute.log 2>&1
rg -q '^ORIGINAL_COLLECTIONS_STRUCT_AND_RESILIENT_CLASS_METADATA_REFLECTION_CACHE_OK$' logs/collections-metadata-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
build=Path('runtime/rebuilt-collectionsinternal')
original=json.loads((build/'reconstruction.json').read_text())
actual=hashlib.sha256((build/'CollectionsInternal').read_bytes()).hexdigest()
if actual!=original['staged_image_sha256']:raise ValueError('Metadata test image differs from reconstruction report')
report={'checked_at':datetime.now(timezone.utc).isoformat(),
    'original_image_sha256':original['original_image_sha256'],'staged_image_sha256':actual,
    'installed':False,'load_verified':True,'selected_metadata_api_execution_verified':True,
    'full_compatibility':False,'types':['CollectionsInternal._HashTable.Header',
        'CollectionsInternal._DequeSlot','CollectionsInternal._HashTable.Storage'],
    'tests':['original accessors return complete metadata','repeated access preserves identity',
        'Swift runtime resolves exact original context descriptors','qualified type-name reflection'],
    'scope':'Selected non-generic metadata APIs only; container operations, generic types, noncopyable types and full framework compatibility unverified.'}
Path('artifacts/collections-metadata-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original CollectionsInternal struct and resilient-class metadata access, reflection and cache identity passed.'
