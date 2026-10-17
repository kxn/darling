#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-native-string-constants.py > logs/build-native-string-constants.log 2>&1
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos11 \
    -isysroot "$sdk" "$workspace/fixtures/hello/native-string-constants.c" -framework CoreFoundation \
    -o "$workspace/artifacts/native-string-constants-smoke" > logs/native-string-constants-compile.log 2>&1
timeout -k 5 30 bin/darling shell "$workspace/artifacts/native-string-constants-smoke" \
    "$workspace/runtime/native-library-stage/libDarlingNativeConstants.dylib" \
    > logs/native-string-constants-execute.log 2>&1
rg -q '^ORIGINAL_CFSTRING_IDENTIFIERS_TYPE_EQUALITY_INDEPENDENT_COPY_OK ' logs/native-string-constants-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
config=json.loads(Path('config/native-string-constants.json').read_text())
count=len(config['constants'])
log=Path('logs/native-string-constants-execute.log').read_text()
assert 'ORIGINAL_CFSTRING_IDENTIFIERS_TYPE_EQUALITY_INDEPENDENT_COPY_OK '+str(count)+'\n' in log
extra_count=len(config.get('extra_identifiers',[]))
assert 'ORIGINAL_EXTRA_IDENTIFIERS_TYPED_VALUES_OK '+str(extra_count)+'\n' in log
report={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
    'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingNativeConstants.dylib').read_bytes()).hexdigest(),
    'config_sha256':hashlib.sha256(Path('config/native-string-constants.json').read_bytes()).hexdigest(),
    'verified_identifier_count':count,'type_equality_copy_execution_verified':True,
    'verified_extra_identifier_count':extra_count,'extra_identifier_values_verified':True,
    'scope':config['scope'],'full_compatibility':False}
Path('artifacts/native-string-constants-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original CFString identifiers passed actual type, equality and independent-copy checks.'
