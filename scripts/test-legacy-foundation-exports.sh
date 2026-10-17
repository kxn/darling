#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -I runtime/legacy-foundation-exports \
    -fblocks -c fixtures/hello/legacy-foundation-exports.m -o artifacts/legacy-foundation-exports.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -F runtime/foundation-native-framework-stage -L runtime/native-library-stage -L "$guest/usr/lib" \
    -lDarlingLegacyFoundation -lSystem -lobjc -framework Foundation \
    artifacts/legacy-foundation-exports.o -o artifacts/legacy-foundation-exports
timeout -k 5 45 bin/darling shell /usr/bin/env OBJC_DISABLE_TAGGED_POINTERS=YES \
    DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-framework-stage:/Volumes/SystemRoot/workspace/runtime/native-framework-stage \
    DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage:/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift \
    /Volumes/SystemRoot/workspace/artifacts/legacy-foundation-exports > logs/legacy-foundation-exports.log 2>&1
rg -q '^LEGACY_FOUNDATION_REAL_SUFFIX_REGISTRY_DELEGATION_AND_UNSUPPORTED_EXCEPTION_OK$' logs/legacy-foundation-exports.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/legacy-foundation-exports.json');j=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingLegacyFoundation.dylib').read_bytes()).hexdigest()==j['library_sha256']
j.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_api_execution_verified=True,
    real_registry_type_and_delegate_override_abi_verified=True,unsupported_spelling_raises_exception=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
