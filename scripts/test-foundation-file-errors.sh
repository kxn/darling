#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -c fixtures/hello/foundation-file-errors.m \
    -o runtime/foundation-file-errors/test.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" -L "$guest/usr/lib" \
    -lSystem -lobjc -framework Foundation runtime/foundation-file-errors/test.o -o artifacts/foundation-file-errors
workspace=/Volumes/SystemRoot/workspace
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/foundation-file-errors" > logs/foundation-file-errors-execute.log 2>&1
rg -q '^FOUNDATION_FILE_ERROR_NATIVE_ERRNO_MAPPINGS_PATH_URL_VARIANT_EXTRA_PRECEDENCE_COPY_OK 288$' logs/foundation-file-errors-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
p=Path('artifacts/foundation-file-errors.json');r=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingFoundationErrors.dylib').read_bytes()).hexdigest()==r['library_sha256']
r.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_file_error_execution_verified=True,selected_cases=288,
 tests=['native read/write errno mapping','actual Cocoa/POSIX NSError objects','nil/string/URL paths',
 'variant array and omitted variant','extra userInfo does not replace existing keys','copy preserves fields and custom localized description'],
 known_base_limit='Existing Darling NSError isEqual does not provide value equality for a distinct copy; factory tests compare copied domain/code/userInfo explicitly.')
p.write_text(json.dumps(r,indent=2)+'\n')
PY
