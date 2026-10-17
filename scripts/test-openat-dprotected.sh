#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-openat-dprotected.py > logs/build-openat-dprotected.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/openat-dprotected.c -o artifacts/openat-dprotected.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem artifacts/openat-dprotected.o -o artifacts/openat-dprotected
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import tempfile,subprocess,shutil,json
project=Path.cwd();directory=Path(tempfile.mkdtemp(prefix='openat-default-',dir=project/'artifacts'))
directory.rmdir()
try:
 with Path('logs/openat-dprotected-execute.log').open('w') as log:
  subprocess.run(['timeout','-k','5','30','bin/darling','shell',
   '/Volumes/SystemRoot/workspace/artifacts/openat-dprotected',
   '/Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingOpenAt.dylib',
   '/Volumes/SystemRoot/workspace/'+str(directory.relative_to(project))],stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
 if directory.exists():shutil.rmtree(directory)
assert 'OPENAT_DEFAULT_ACTUAL_FILES_MODES_CONTENT_FLAGS_ERRORS_AND_PROTECTION_REJECTION_OK' in Path('logs/openat-dprotected-execute.log').read_text()
f=Path('artifacts/openat-dprotected.json');p=json.loads(f.read_text())
p.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_default_filesystem_api_execution_verified=True,
    relative_directory_fd_modes_umask_content_append_truncate_cloexec_verified=True,
    unsupported_protection_fails_before_file_creation=True,
    nonexistent_bad_fd_symlink_nofollow_and_raw_write_errors_verified=True)
f.write_text(json.dumps(p,indent=2)+'\n')
PY
