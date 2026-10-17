#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
scripts/build-constant-float-number.sh > logs/build-constant-float-number.log 2>&1
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14 \
    -isysroot "$sdk" -Xclang -fobjc-constant-literals "$workspace/fixtures/hello/constant-float-number.m" \
    -L "$workspace/runtime/native-library-stage" -lDarlingConstantFloat -framework Foundation -framework CoreFoundation \
    -o "$workspace/artifacts/constant-float-number-smoke" > logs/constant-float-number-compile.log 2>&1
llvm-objdump-19 --macho --private-headers artifacts/constant-float-number-smoke > logs/constant-float-number-headers.log
rg -q '__objc_floatobj' logs/constant-float-number-headers.log
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:/usr/lib/swift" \
    "$workspace/artifacts/constant-float-number-smoke" > logs/constant-float-number-execute.log 2>&1
rg -q '^APPLE_CLANG_CONSTANT_FLOAT_LAYOUT_BITS_CF_BRIDGE_EQUALITY_HASH_COPY_OK$' logs/constant-float-number-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
    'abi':json.loads(Path('config/constant-float-abi.json').read_text()),
    'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingConstantFloat.dylib').read_bytes()).hexdigest(),
    'original_apple_clang_literal_execution_verified':True,
    'scope':'Pinned constant float NSNumber ABI and selected conversions, CF bridging, bit preservation, equality/hash, copying and size rejection. Not all NSNumber operations.',
    'full_compatibility':False}
Path('artifacts/constant-float-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Original Apple clang float literals passed binary layout, edge bit patterns, CF bridging, equality/hash, copy and size rejection.'
