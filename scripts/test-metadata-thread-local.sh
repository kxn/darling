#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -c fixtures/hello/metadata-thread-local.c -o artifacts/metadata-thread-local.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -L runtime/native-library-stage -lSystem -framework Foundation -F runtime/native-framework-stage \
    -framework MetadataUtilities artifacts/metadata-thread-local.o -o artifacts/metadata-thread-local
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/metadata-thread-local" > logs/metadata-thread-local-execute.log 2>&1
rg -q '^ORIGINAL_METADATA_EXPORTED_TLV_THREE_THREADS_ZERO_INITIALIZATION_DISTINCT_STORAGE_ISOLATION_OK$' logs/metadata-thread-local-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
r=json.loads(Path('runtime/rebuilt-metadata-utilities/reconstruction.json').read_text())
assert hashlib.sha256(Path('runtime/native-framework-stage/MetadataUtilities.framework/MetadataUtilities').read_bytes()).hexdigest()==r['staged_image_sha256']
proof={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
 'original_image_sha256':r['original_image_sha256'],'staged_image_sha256':r['staged_image_sha256'],
 'selected_exported_tlv_execution_verified':True,'full_compatibility':False,
 'scope':'Original exported 40-byte TLV template: three concurrent threads, zero initialization, distinct addresses and isolated writes. Spotlight and metadata query services unverified.'}
Path('artifacts/metadata-thread-local-compat.json').write_text(json.dumps(proof,indent=2)+'\n')
PY
