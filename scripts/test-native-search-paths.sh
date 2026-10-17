#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/prepare-native-c-test-stage.py > logs/stage-native-c-test.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/native-search-paths.c -o artifacts/native-search-paths.o
for version in 11 26.6; do
    ld64.lld-19 -arch x86_64 -platform_version macos 11 "$version" -syslibroot "$guest" \
        -L "$guest/usr/lib" -lSystem artifacts/native-search-paths.o -o "artifacts/native-search-paths-sdk-$version"
    timeout -k 5 30 bin/darling shell /usr/bin/env \
        DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/native-c-test-stage:/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift \
        "/Volumes/SystemRoot/workspace/artifacts/native-search-paths-sdk-$version" \
        /Volumes/SystemRoot/workspace/runtime/rebuilt-dirhelper-native/libsystem_coreservices.dylib \
        > "logs/native-search-paths-sdk-$version-execute.log" 2>&1
    rg -q '^ORIGINAL_SEARCH_PATH_ENUMERATION_DOMAINS_ORDER_MASKS_BOUNDS_AND_OWNER_OK$' "logs/native-search-paths-sdk-$version-execute.log"
done
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
r=json.loads(Path('runtime/rebuilt-dirhelper-native/reconstruction.json').read_text())
actual=hashlib.sha256(Path('runtime/rebuilt-dirhelper-native/libsystem_coreservices.dylib').read_bytes()).hexdigest()
assert actual==r['staged_image_sha256']
p={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,'full_compatibility':False,
 'original_image_sha256':r['original_image_sha256'],'library_sha256':actual,
 'selected_search_path_enumeration_execution_verified':True,'program_sdk_versions':['11','26.6'],
 'scope':'Original public sysdir start/next pair, six documented directory paths, domain order, all 16 domain masks, guards and original implementation owner. No private directory-relative ABI, per-user directory creation or filesystem service execution claim.'}
Path('artifacts/native-search-paths.json').write_text(json.dumps(p,indent=2)+'\n')
PY
