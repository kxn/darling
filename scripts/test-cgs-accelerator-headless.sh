#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/cgs-accelerator-headless.c -o artifacts/cgs-accelerator-headless.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L runtime/foundation-native-library-stage -L runtime/native-library-stage \
    -F runtime/foundation-native-framework-stage -F "$guest/System/Library/Frameworks" \
    -lSystem -framework CoreGraphics artifacts/cgs-accelerator-headless.o -o artifacts/cgs-accelerator-headless
timeout -k 5 45 bin/darling shell /usr/bin/env OBJC_DISABLE_TAGGED_POINTERS=YES \
    DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-framework-stage:/Volumes/SystemRoot/workspace/runtime/native-framework-stage \
    DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage:/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift \
    /Volumes/SystemRoot/workspace/artifacts/cgs-accelerator-headless > logs/cgs-accelerator-headless.log 2>&1
rg -q '^CGS_ACCELERATOR_PRODUCTION_REAL_BACKEND_NO_DISPLAY_FAILURE_AND_PROVIDER_OK$' logs/cgs-accelerator-headless.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/cgs-accelerator.json');j=json.loads(p.read_text())
for key in ['stage_framework','stage_backend']:
    assert hashlib.sha256(Path(j[key]).read_bytes()).hexdigest()==j[key+'_sha256']
j.update(real_backend_no_display_execution_verified=True,
    real_backend_checked_at=datetime.now(timezone.utc).isoformat(),real_accelerator_execution_verified=False)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
