#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -c fixtures/hello/statfs-ext.c -o artifacts/statfs-ext.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem artifacts/statfs-ext.o -o artifacts/statfs-ext
timeout -k 5 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/statfs-ext \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingFoundationSystem.dylib > logs/statfs-ext.log 2>&1
rg -q '^APPLE_STATFS_EXT_REAL_PATH_FD_NONBLOCK_FALLBACK_BOUNDS_AND_ERRORS_OK$' logs/statfs-ext.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/foundation-libc-compat.json');j=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingFoundationSystem.dylib').read_bytes()).hexdigest()==j['library_sha256']
j.update(statfs_ext_checked_at=datetime.now(timezone.utc).isoformat(),selected_statfs_ext_execution_verified=True,
    real_path_fd_and_original_einval_nonblock_fallback_verified=True,
    statfs_layout_canaries_and_invalid_flag_null_closed_fd_and_missing_path_errors_verified=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
