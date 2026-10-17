#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos12 -isysroot "$sdk" \
    -c fixtures/hello/iokit-main-port.c -o artifacts/iokit-main-port-test.o
ld64.lld-19 -arch x86_64 -platform_version macos 12 12 -syslibroot "$guest" \
    -L runtime/foundation-native-library-stage -L runtime/native-library-stage \
    -F runtime/foundation-native-framework-stage -F "$guest/System/Library/Frameworks" \
    -lSystem -framework IOKit -framework CoreFoundation \
    artifacts/iokit-main-port-test.o -o artifacts/iokit-main-port-test
timeout -k 5 45 bin/darling shell /usr/bin/env OBJC_DISABLE_TAGGED_POINTERS=YES \
    DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-framework-stage:/Volumes/SystemRoot/workspace/runtime/native-framework-stage \
    DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage:/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift \
    /Volumes/SystemRoot/workspace/artifacts/iokit-main-port-test > logs/iokit-main-port-test.log 2>&1
rg -q '^IOKIT_REAL_DEFAULT_PORT_CONSTANT_AND_ORIGINAL_MATCHING_PROVIDER_OK$' logs/iokit-main-port-test.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/iokit-main-port.json');j=json.loads(p.read_text())
for prefix in ['stage_framework','stage_backend']:
    assert hashlib.sha256(Path(j[prefix]).read_bytes()).hexdigest()==j[prefix+'_sha256']
j.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_constant_execution_verified=True,
    old_default_port_and_matching_provider_preserved=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
