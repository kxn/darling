#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/native-quarantine-values.c -o artifacts/native-quarantine-values.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem artifacts/native-quarantine-values.o -o artifacts/native-quarantine-values
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/native-quarantine-values \
    /Volumes/SystemRoot/workspace/runtime/rebuilt-quarantine-native/libquarantine.dylib \
    > logs/native-quarantine-values-execute.log 2>&1
rg -q '^ORIGINAL_QUARANTINE_ALLOC_FLAGS_RANGE_CLONE_INDEPENDENCE_AND_RELEASE_OK$' logs/native-quarantine-values-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
r=json.loads(Path('runtime/rebuilt-quarantine-native/reconstruction.json').read_text())
actual=hashlib.sha256(Path('runtime/rebuilt-quarantine-native/libquarantine.dylib').read_bytes()).hexdigest()
assert actual==r['staged_image_sha256']
p={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,'full_compatibility':False,
 'original_image_sha256':r['original_image_sha256'],'library_sha256':actual,
 'selected_quarantine_value_api_execution_verified':True,'flag_and_copy_cases':257,
 'scope':'Actual original allocation/get/set/range rejection/independent clone/release over opaque objects. No filesystem quarantine metadata, process policy, malware scanning, translocation or policy enforcement claim.'}
Path('artifacts/native-quarantine-values.json').write_text(json.dumps(p,indent=2)+'\n')
PY
