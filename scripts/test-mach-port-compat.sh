#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos11 \
    -isysroot "$sdk" "$workspace/fixtures/hello/mach-port.m" -L "$workspace/runtime/native-library-stage" \
    -framework Foundation -o "$workspace/artifacts/mach-port-smoke" > logs/mach-port-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:/usr/lib/swift" \
    "$workspace/artifacts/mach-port-smoke" > logs/mach-port-execute.log 2>&1
rg -q '^BASELINE_MACH_PORT_REAL_RIGHTS_RUNLOOP_RAW_AND_OOL_DATA_MESSAGES_INVALIDATION_OK$' logs/mach-port-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
log=Path('logs/mach-port-execute.log').read_text()
observation=re.search(r'MACH_PORT_POST_INVALIDATION_TYPE status=(-?\d+) type=(\d+)',log)
assert observation
r={'checked_at':datetime.now(timezone.utc).isoformat(),'new_implementation_installed':False,
    'existing_provider':'/usr/lib/libFND.dylib',
    'provider_sha256':hashlib.sha256(Path('runtime/rootfs/usr/libexec/darling/usr/lib/libFND.dylib').read_bytes()).hexdigest(),
    'selected_real_ipc_execution_verified':True,
    'post_invalidation_rights_observation':{'status':int(observation[1]),'type':int(observation[2])},
    'scope':'Existing Darling NSMachPort verified by actual method ownership, Mach rights creation, shared reference release, run-loop delivery of raw and out-of-line data messages, and invalidation state. Full right ownership, CF bridging, cross-process messaging and secure capability coding are not asserted.',
    'full_compatibility':False}
Path('artifacts/mach-port-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Existing Darling Mach port passed selected real rights and raw/OOL data message delivery checks.'
