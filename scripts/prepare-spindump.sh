#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
# Prepare reference readers/cache on a fresh checkout, then rebuild and verify
# the shared adapter together with CoreEntitlements before other consumers.
scripts/prepare-coreentitlements.sh > logs/prepare-coreentitlements.log 2>&1
python3 scripts/rebuild-c-cache-image.py --target spindump --modern-adapter > logs/rebuild-spindump.log 2>&1
scripts/test-rebuilt-spindump.sh
cp runtime/rebuilt-spindump/libspindump.dylib runtime/state/prefix/usr/lib/libspindump.dylib
timeout 30 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/spindump-abi-smoke \
    /usr/lib/libspindump.dylib > logs/spindump-installed-execute.log 2>&1
rg -q '^ORIGINAL_SPINDUMP_THRESHOLD_INITIALIZATION_OK$' logs/spindump-installed-execute.log
python3 - <<'PY'
from pathlib import Path
import hashlib,json
report=json.loads(Path('runtime/rebuilt-spindump/reconstruction.json').read_text())
report.pop('patches')
report.update({'installed':True,'load_verified':True,'execution_verified':True,
    'adapter_sha256':hashlib.sha256(Path('runtime/rebuilt-der/libDarlingDER.dylib').read_bytes()).hexdigest(),
    'tests':['500 ms default threshold initialization and repeat query',
        'installed-path execution without loader overrides','XPC dictionary create/set/get/release',
        'typed allocation and realloc preserve bytes','typed calloc zeroing and overflow rejection'],
    'scope':'Original Apple library is reconstructed. Threshold API tested; sampling daemon/report generation remain unverified.',
    'sampling_ready':False})
Path('artifacts/spindump-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Installed original spindump library after real initialization test. Sampling/report generation remain unverified.'
