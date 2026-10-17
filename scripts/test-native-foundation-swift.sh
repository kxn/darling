#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/native-foundation-swift.swift" \
    -target x86_64-apple-macos15.4 -sdk "$sdk" -module-name NativeFoundationSwiftProbe \
    -o "$workspace/artifacts/native-foundation-swift.o" > logs/native-foundation-swift-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" "$workspace/artifacts/native-foundation-swift.o" \
    -L/usr/lib/swift -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftSwiftOnoneSupport -lobjc \
    -framework Foundation -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/native-foundation-swift" \
    > logs/native-foundation-swift-link.log 2>&1
status=0
timeout -k 5 45 bin/darling shell /usr/bin/env OBJC_DISABLE_TAGGED_POINTERS=YES \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/foundation-native-framework-stage:$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/foundation-native-library-stage:$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/native-foundation-swift" > logs/native-foundation-swift-execute.log 2>&1 || status=$?
python3 - "$status" <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
log=Path('logs/native-foundation-swift-execute.log').read_text();status=int(sys.argv[1])
passed=status==0 and 'NATIVE_FOUNDATION_SWIFT_ENUM_METADATA_HASH_RAWVALUES_CODABLE_AND_ATTRIBUTED_STRING_OK' in log
conflicts='is implemented in both' in log
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_compatibility=False,
    exit_status=status,selected_swift_api_execution_verified=passed and not conflicts,
    duplicate_class_conflicts_detected=conflicts,tagged_pointer_optimization_disabled=True,
    log='logs/native-foundation-swift-execute.log',
    reached_markers=[line for line in log.splitlines() if line.startswith('NATIVE_FOUNDATION_SWIFT_')],
    tested_foundation_sha256=hashlib.sha256(Path('runtime/foundation-native-framework-stage/Foundation.framework/Foundation').read_bytes()).hexdigest())
Path('artifacts/native-foundation-swift.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(0 if passed and not conflicts else 1)
PY
