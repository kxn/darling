#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
    -c fixtures/hello/native-foundation-values.m -o artifacts/native-foundation-values.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -F runtime/foundation-native-framework-stage -L runtime/native-library-stage -L "$guest/usr/lib" -lSystem -lobjc \
    -framework Foundation -framework CoreFoundation artifacts/native-foundation-values.o -o artifacts/native-foundation-values
status=0
timeout -k 5 45 bin/darling shell /usr/bin/env \
    OBJC_DISABLE_TAGGED_POINTERS=YES \
    DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-framework-stage:/Volumes/SystemRoot/workspace/runtime/native-framework-stage \
    DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage:/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift \
    /Volumes/SystemRoot/workspace/artifacts/native-foundation-values > logs/native-foundation-values.log 2>&1 || status=$?
python3 - "$status" <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib
p=Path('artifacts/native-foundation-values.json');log=Path('logs/native-foundation-values.log').read_text()
status=int(sys.argv[1]);passed=status==0 and 'NATIVE_FOUNDATION_STRINGS_COLLECTIONS_JSON_DATE_ERROR_CF_AND_FILES_OK' in log
conflicts='is implemented in both' in log
p.write_text(json.dumps(dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,exit_status=status,
    selected_api_execution_verified=passed and not conflicts,duplicate_class_conflicts_detected=conflicts,
    tagged_pointer_optimization_disabled=True,
    known_backend_limit='Existing libobjc C++ object_getClass/objc_opt_isKindOfClass paths dereference tagged pointers; native values currently require the runtime-supported OBJC_DISABLE_TAGGED_POINTERS setting.',
    tested_images_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [
        Path('runtime/foundation-native-framework-stage/Foundation.framework/Foundation'),
        Path('runtime/foundation-native-framework-stage/CoreFoundation.framework/CoreFoundation'),
        Path('artifacts/native-foundation-values')]},
    full_compatibility=False,log='logs/native-foundation-values.log',
    reached_markers=[line for line in log.splitlines() if line.startswith('NATIVE_FOUNDATION_API_')]),indent=2)+'\n')
raise SystemExit(0 if passed and not conflicts else 1)
PY
