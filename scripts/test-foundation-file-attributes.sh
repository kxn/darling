#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/foundation-file-attributes.c -o artifacts/foundation-file-attributes.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem artifacts/foundation-file-attributes.o -o artifacts/foundation-file-attributes
timeout -k 5 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/foundation-file-attributes \
    /Volumes/SystemRoot/workspace/runtime/native-library-stage/libDarlingFoundationSystem.dylib \
    > logs/foundation-file-attributes.log 2>&1
rg -q '^FOUNDATION_FILE_ATTRS_REAL_MODE_TYPE_LINKS_UTF8_SYMLINKS_TRUNCATION_AND_ERRORS_OK$' logs/foundation-file-attributes.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/foundation-libc-compat.json');j=json.loads(p.read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libDarlingFoundationSystem.dylib').read_bytes()).hexdigest()==j['library_sha256']
j.update(file_attributes_checked_at=datetime.now(timezone.utc).isoformat(),
    selected_file_attributes_execution_verified=True,
    real_type_mode_hardlinks_utf8_follow_and_nofollow_symlinks_verified=True,
    all_selected_payload_truncations_and_report_fullsize_guards_verified=True,
    missing_path_enoent_invalid_request_and_original_unsupported_delegation_verified=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
