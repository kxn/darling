#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-objc-class-enumeration.py > logs/build-objc-class-enumeration.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
for name in objc-enumeration-plugin objc-class-enumeration; do
    clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fblocks \
        -c "fixtures/hello/$name.m" -o "artifacts/$name.o"
done
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lobjc -lSystem artifacts/objc-enumeration-plugin.o \
    -install_name /Volumes/SystemRoot/workspace/artifacts/objc-enumeration-plugin.dylib \
    -o artifacts/objc-enumeration-plugin.dylib
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lobjc -lSystem artifacts/objc-class-enumeration.o \
    -o artifacts/objc-class-enumeration
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/objc-class-enumeration \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingObjCEnumeration.dylib \
    /Volumes/SystemRoot/workspace/artifacts/objc-enumeration-plugin.dylib \
    > logs/objc-class-enumeration-execute.log 2>&1
rg -q '^OBJC_ENUMERATION_CALLER_HEADER_HANDLES_FILTERS_DYNAMIC_STOP_AND_LAZY_METADATA_OK$' logs/objc-class-enumeration-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json
f=Path('artifacts/objc-class-enumeration.json');p=json.loads(f.read_text())
p.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_enumeration_execution_verified=True,
    caller_header_normal_and_first_handle_verified=True,protocol_inheritance_and_superclass_filters_verified=True,
    registered_dynamic_classes_and_unregistered_exclusion_verified=True,
    name_only_enumeration_realizes_no_classes=True,early_stop_verified=True)
f.write_text(json.dumps(p,indent=2)+'\n')
PY
