#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-person-name-formatter.py > logs/build-person-name-formatter.log 2>&1
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos12 \
    -isysroot "$sdk" "$workspace/fixtures/hello/person-name-formatter.m" \
    -L "$workspace/runtime/native-library-stage" -lDarlingPersonNameFormatter -lDarlingPersonName -framework Foundation \
    -o "$workspace/artifacts/person-name-formatter-smoke" > logs/person-name-formatter-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:/usr/lib/swift" \
    "$workspace/artifacts/person-name-formatter-smoke" > logs/person-name-formatter-execute.log 2>&1
rg -q '^PERSON_NAME_FORMATTER_SELECTED_ENGLISH_STYLES_COPY_PHONETIC_GRAPHEME_AND_UNSUPPORTED_REJECTION_OK$' logs/person-name-formatter-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
c=json.loads(Path('config/person-name-formatter-compat.json').read_text())
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,'source':c,
    'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingPersonNameFormatter.dylib').read_bytes()).hexdigest(),
    'selected_formatting_api_execution_verified':True,'full_compatibility':False}
Path('artifacts/person-name-formatter-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Selected English-locale name formatting passed; other locales and annotations are explicitly unsupported.'
