#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -O2 \
    -c fixtures/hello/cgs-accelerator.c -o artifacts/cgs-accelerator-test.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -lSystem -export_dynamic artifacts/cgs-accelerator-test.o -o artifacts/cgs-accelerator-test
timeout -k 5 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/cgs-accelerator-test \
    /Volumes/SystemRoot/workspace/runtime/cgs-accelerator/libDarlingCGSAcceleratorUnit.dylib \
    > logs/cgs-accelerator-test.log 2>&1
rg -q '^CGS_ACCELERATOR_SOURCE_BORROWED_CACHE_ERRORS_ALIASES_1024_CONCURRENT_QUERIES_UNLOAD_REAL_PORT_REFS_OK$' logs/cgs-accelerator-test.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
p=Path('artifacts/cgs-accelerator.json');j=json.loads(p.read_text())
c=json.loads(Path('config/cgs-accelerator.json').read_text())
for file,key in [(c['source'],'source_sha256'),('runtime/cgs-accelerator/production.o','object_sha256'),('runtime/cgs-accelerator/libDarlingCGSAcceleratorUnit.dylib','unit_library_sha256')]:
    assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==j[key]
j.update(checked_at=datetime.now(timezone.utc).isoformat(),selected_backend_ownership_execution_verified=True,
    controlled_backend_with_real_mach_rights=True,concurrent_cached_queries=1024,
    borrowed_port_cache_aliasing_errors_and_unload_cleanup_verified=True)
p.write_text(json.dumps(j,indent=2)+'\n')
PY
