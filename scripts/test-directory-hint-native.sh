#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-directory-hint-native.py > logs/build-directory-hint-native.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -c fixtures/hello/directory-hint-native.c -o runtime/directory-hint-native/test.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" -L "$guest/usr/lib" \
    -lSystem runtime/directory-hint-native/test.o -o artifacts/directory-hint-native
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/directory-hint-native" "$workspace/runtime/native-library-stage/libDarlingDirectoryHint.dylib" \
    > logs/directory-hint-native-execute.log 2>&1
rg -q '^ORIGINAL_DIRECTORY_HINT_METADATA_REFLECTION_CASES_COPY_AND_SINGLE_PAYLOAD_ROUNDTRIPS_OK 40$' logs/directory-hint-native-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
p=Path('artifacts/directory-hint-native.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingDirectoryHint.dylib').read_bytes()).hexdigest()==r['library_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_metadata_and_witness_execution_verified=True,
 full_compatibility=False,selected_single_payload_roundtrip_cases=40)
p.write_text(json.dumps(r,indent=2)+'\n')
PY
