#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-security-session-values.py > logs/build-security-session-values.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -I runtime/security-session-values \
    -c fixtures/hello/security-session-values.m -o artifacts/security-session-values.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L runtime/native-library-stage -L "$guest/usr/lib" -framework Foundation -lobjc -lSystem \
    artifacts/security-session-values.o -o artifacts/security-session-values
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/security-session-values \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingSecuritySessionValues.dylib \
    > logs/security-session-values-execute.log 2>&1
rg -q '^APPLE_SECURITY_SESSION_VALUES_NATIVE_LAYOUT_COPY_RETAIN_PROPERTIES_AND_ALIASES_OK$' logs/security-session-values-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json
f=Path('artifacts/security-session-values.json');p=json.loads(f.read_text())
p.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_value_api_execution_verified=True,
    native_instance_sizes_and_ivar_offsets_verified=True,session_integer_boundary_cases=20)
f.write_text(json.dumps(p,indent=2)+'\n')
PY
