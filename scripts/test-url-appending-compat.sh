#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    -target x86_64-apple-macos15.4 -sdk "$sdk" -module-name OriginalURLAppendingProbe \
    "$workspace/fixtures/hello/url-appending-compat.swift" -o "$workspace/runtime/url-appending-compat/test.o" \
    > logs/url-appending-compat-test-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" "$workspace/runtime/url-appending-compat/test.o" -L/usr/lib/swift \
    -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftFoundation -lswiftSwiftOnoneSupport -lswiftDarwin \
    -framework Foundation -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/url-appending-compat" \
    > logs/url-appending-compat-test-link.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/url-appending-compat" > logs/url-appending-compat-test-execute.log 2>&1
rg -q '^URL_APPENDING_GENERIC_PATH_COMPONENTS_ENCODING_HINTS_REAL_FILESYSTEM_OK 19$' logs/url-appending-compat-test-execute.log
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
 'source_reference':json.loads(Path('config/url-appending-compat.json').read_text()),
 'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingURLCompat.dylib').read_bytes()).hexdigest(),
 'selected_url_api_execution_verified':True,'selected_cases':19,'full_compatibility':False,
 'scope':'Selected original-SDK generic String/Substring path and variadic component APIs; file/HTTP paths, percent encoding, query/fragment, explicit/inferred/real filesystem directory hints. Complete URL parser and all edge-case compatibility unverified.'}
Path('artifacts/url-appending-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
