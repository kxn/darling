#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
scripts/build-person-name-compat.sh > logs/build-person-name-compat.log 2>&1
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14 \
    -isysroot "$sdk" "$workspace/fixtures/hello/person-name-components.m" \
    -L "$workspace/runtime/native-library-stage" -lDarlingPersonName -framework Foundation \
    -o "$workspace/artifacts/person-name-components-smoke" > logs/person-name-components-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:/usr/lib/swift" \
    "$workspace/artifacts/person-name-components-smoke" > logs/person-name-components-execute.log 2>&1
rg -q '^PERSON_NAME_COMPONENTS_COPY_UTF8_PHONETIC_SECURE_ARCHIVE_ROUNDTRIP_OK$' logs/person-name-components-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
c=json.loads(Path('config/person-name-compat.json').read_text())
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,'source':c,
    'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingPersonName.dylib').read_bytes()).hexdigest(),
    'selected_public_api_execution_verified':True,'full_compatibility':False}
Path('artifacts/person-name-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Person-name component values passed copy, UTF-8, phonetic isolation and secure archive roundtrip.'
