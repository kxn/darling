#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/stage-foundation-xpc-exports.py > logs/stage-foundation-xpc-exports.log 2>&1
llvm-nm-19 --defined-only runtime/native-library-stage/libFND.dylib > logs/foundation-xpc-symbols.log
llvm-objdump-19 --macho --exports-trie runtime/native-library-stage/libFND.dylib > logs/foundation-xpc-export-trie.log
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos11 \
    -isysroot "$sdk" "$workspace/fixtures/hello/foundation-xpc.m" -framework Foundation \
    -o "$workspace/artifacts/foundation-xpc-smoke" > logs/foundation-xpc-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:/usr/lib/swift" \
    "$workspace/artifacts/foundation-xpc-smoke" "$workspace/runtime/native-library-stage/libFND.dylib" \
    > logs/foundation-xpc-execute.log 2>&1
rg -q '^EXISTING_NSXPC_CLASS_EXPORT_IDENTITIES_BPLIST16_SCALAR_INVOCATION_ROUNDTRIP_MALFORMED_REJECTION_OK$' logs/foundation-xpc-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
r=json.loads(Path('artifacts/foundation-xpc-exports.json').read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libFND.dylib').read_bytes()).hexdigest()==r['staged_sha256']
r.update({'execution_checked_at':datetime.now(timezone.utc).isoformat(),'selected_xpc_scalar_execution_verified':True,
    'scope':'Existing class/metaclass identities, original method ownership, bplist16 scalar invocation encode/decode/invoke and malformed-envelope rejection. Not full object/proxy/capability or cross-process XPC compatibility.'})
Path('artifacts/foundation-xpc-exports.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Existing Darling NSXPC classes exported and selected real bplist16 scalar invocation checks passed.'
