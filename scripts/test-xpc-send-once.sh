#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
scripts/build-xpc-send-once.sh > logs/build-xpc-send-once.log 2>&1
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos11 \
    -isysroot "$sdk" "$workspace/fixtures/hello/xpc-send-once.c" -o "$workspace/artifacts/xpc-send-once-smoke" \
    > logs/xpc-send-once-compile.log 2>&1
timeout -k 5 30 bin/darling shell "$workspace/artifacts/xpc-send-once-smoke" \
    "$workspace/runtime/native-library-stage/libDarlingXPCSendOnce.dylib" > logs/xpc-send-once-execute.log 2>&1
rg -q '^XPC_SEND_ONCE_REAL_RIGHT_COPY_EXTRACTION_DELIVERY_CONSUMPTION_DISPOSAL_WRONG_TYPE_OK$' logs/xpc-send-once-execute.log
status=0
timeout -k 5 30 bin/darling shell "$workspace/artifacts/xpc-send-once-smoke" \
    "$workspace/runtime/native-library-stage/libDarlingXPCSendOnce.dylib" --double-extract \
    > logs/xpc-send-once-double-extract.log 2>&1 || status=$?
if [[ $status == 0 || $status == 99 || $status == 124 || $status == 137 ]]; then
    echo 'Repeated extraction did not fail as a native API misuse.' >&2;exit 1
fi
rg -q '^XPC send-once right extracted more than once$' logs/xpc-send-once-double-extract.log
python3 - "$status" <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
c=json.loads(Path('config/xpc-send-once-abi.json').read_text())
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,'abi':c,
    'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingXPCSendOnce.dylib').read_bytes()).hexdigest(),
    'selected_rights_execution_verified':True,'double_extract_misuse_exit_code':int(sys.argv[1]),
    'wire_serialization_supported':False,'full_compatibility':False}
Path('artifacts/xpc-send-once-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Send-once actual rights adoption, retain-copy, extraction, Mach delivery and disposal passed; repeated extraction terminates.'
