#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
python3 - <<'PY'
from pathlib import Path
import plistlib
p=Path('runtime/ca-render-server/vectors');p.mkdir(exist_ok=True)
values=[0,1,42,0xffffffff,-1,0x80000000,0x7fffffff,True,False,'not a number',None]
vectors=[[{'kCADisplayFrameCount':v}] for v in values]+[[{}],[],b'not a property list',[{'kCADisplayFrameCount':7},{'kCADisplayFrameCount':999}]]
for i,v in enumerate(vectors):
    (p/(str(i)+'.plist')).write_bytes(v if isinstance(v,bytes) else plistlib.dumps(v,fmt=plistlib.FMT_BINARY))
PY
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/ca-render-server.c -o artifacts/ca-render-server-test.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -F "$guest/System/Library/Frameworks" -framework CoreFoundation artifacts/ca-render-server-test.o \
    runtime/ca-render-server/native-oracle.o runtime/ca-render-server/CARenderServer.o \
    -o artifacts/ca-render-server-test
timeout -k 5 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/ca-render-server-test \
    /Volumes/SystemRoot/workspace/runtime/ca-render-server/vectors \
    > logs/ca-render-server-test.log 2>&1
rg -q '^CA_RENDER_SOURCE_REAL_IPC_DISCOVERY_MALFORMED_REPLIES_DEAD_PORT_AND_RIGHTS_OK$' logs/ca-render-server-test.log
rg -q '^CA_RENDER_DEBUG_GET_SET_STATISTICS_OOL_BPLIST_NATIVE_DIFFERENTIAL_90_EXCHANGES_OK$' logs/ca-render-server-test.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/ca-render-server.json');j=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/ca-render-server/libDarlingCARenderServer.dylib').read_bytes()).hexdigest()==j['library_sha256']
assert hashlib.sha256(Path('vendor/darling/src/external/cocotron/QuartzCore/CARenderServer.m').read_bytes()).hexdigest()==j['source_sha256']
assert hashlib.sha256(Path('runtime/ca-render-server/CARenderServer.o').read_bytes()).hexdigest()==j['object_sha256']
j.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_api_execution_verified=True,
    real_mach_ipc_native_query_set_and_statistics_differential_exchanges=90,
    malformed_replies_send_once_death_discovery_and_port_refs_verified=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
