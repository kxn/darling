#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,runpy,subprocess
root=Path.cwd();r=json.loads(Path('config/xpc-send-once-abi.json').read_text())
assert hashlib.sha256(Path(r['backend_library']).read_bytes()).hexdigest()==r['backend_sha256']
assert subprocess.check_output(['git','-C','vendor/darling/src/external/libxpc','rev-parse','HEAD'],text=True).strip()==r['backend_source_commit']
n=r['native_reference'];assert hashlib.sha256((root/'runtime/fullsystem-libraries'/n['path'].lstrip('/')).read_bytes()).hexdigest()==n['sha256']
ns=runpy.run_path('scripts/dsc-image.py',init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
for routine in n['routines'].values():
    payload=bytes.fromhex(routine['bytes']);assert ns['read'](int(routine['address'],0),len(payload))==payload
PY
mkdir -p runtime/xpc-send-once
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -O2 -c scripts/xpc-send-once-compat.m -o runtime/xpc-send-once/once.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -L "$guest/usr/lib/system" -lSystem -lobjc -lxpc \
    -install_name /usr/lib/libDarlingXPCSendOnce.dylib runtime/xpc-send-once/once.o \
    -o runtime/native-library-stage/libDarlingXPCSendOnce.dylib.pending
mv runtime/native-library-stage/libDarlingXPCSendOnce.dylib.pending runtime/native-library-stage/libDarlingXPCSendOnce.dylib
