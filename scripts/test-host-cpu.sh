#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
scripts/build-host-cpu-fixture.sh > logs/host-cpu-fixture-build.log 2>&1
timeout -k 5 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/host-cpu-smoke --after \
    /Volumes/SystemRoot/workspace/artifacts/libHaswellCPUSmoke.dylib > logs/host-cpu-after.log 2>&1
rg -q '^HOST_CPU_X86_64H_REPORT_AND_ORIGINAL_APPLE_AVX2_LIBRARY_EXECUTION_OK$' logs/host-cpu-after.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
r=json.loads(Path('artifacts/host-cpu-compat.json').read_text())
assert hashlib.sha256(Path(r['config']['runtime_binary']).read_bytes()).hexdigest()==r['patched_sha256']
before=Path('logs/host-cpu-before.log')
r.update({'execution_checked_at':datetime.now(timezone.utc).isoformat(),
    'host_basic_preferred_and_processor_subtypes_verified':True,
    'original_apple_clang_x86_64h_avx2_execution_verified':True,
    'legacy_cpu_report_rejection_log_present':before.exists() and
        'LEGACY_CPU_REPORT_X86_64H_LIBRARY_REJECTION_CONFIRMED' in before.read_text()})
Path('artifacts/host-cpu-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'Guarded host subtype reports and original Apple x86_64h AVX2 execution passed.'
