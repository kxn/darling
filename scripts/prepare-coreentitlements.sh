#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
revision=0e1b35a5f60e7041c51b57a54cc36d815fe7adf2
if [[ ! -d vendor/DyldExtractor/.git ]]; then
    git init -q vendor/DyldExtractor
    git -C vendor/DyldExtractor remote add origin https://github.com/arandomdev/DyldExtractor.git
    git -C vendor/DyldExtractor fetch --depth 1 origin "$revision"
    git -C vendor/DyldExtractor checkout --detach FETCH_HEAD
fi
test "$(git -C vendor/DyldExtractor rev-parse HEAD)" = "$revision"
if [[ ! -f runtime/recovery-libraries/usr/lib/libCoreEntitlements.dylib ]]; then
    scripts/prepare-recovery.sh
fi
scripts/build-der-adapter.sh > logs/build-der-adapter.log 2>&1
python3 scripts/rebuild-coreentitlements.py --modern-adapter > logs/rebuild-coreentitlements.log 2>&1
scripts/test-rebuilt-coreentitlements.sh
scripts/test-typed-allocations.sh
cp runtime/rebuilt-der/libDarlingDER.dylib runtime/state/prefix/usr/lib/libDarlingDER.dylib
cp runtime/rebuilt-coreentitlements/libCoreEntitlements.dylib runtime/state/prefix/usr/lib/libCoreEntitlements.dylib
timeout 45 bin/darling shell /Volumes/SystemRoot/workspace/artifacts/coreentitlements-abi-smoke \
    /usr/lib/libCoreEntitlements.dylib > logs/coreentitlements-installed-execute.log 2>&1
rg -q '^ORIGINAL_APPLE_COREENTITLEMENTS_SEMANTICS_OK$' logs/coreentitlements-installed-execute.log
python3 - <<'PY'
from pathlib import Path
import hashlib,json
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
report=json.loads(Path('runtime/rebuilt-coreentitlements/reconstruction.json').read_text())
report.pop('patches')
report.update({'installed':True,'execution_verified':True,
    'adapter_sha256':digest('runtime/rebuilt-der/libDarlingDER.dylib'),
    'tests':['DER dictionary/array/string/integer/boolean serialization and parsing',
        'positive and negative permission subsets','truncation and out-of-bounds length rejection',
        'duplicate-key rejection','two simultaneous copies at different addresses',
        'independent Python DER decoder','OpenSSL ASN.1 decoder','installed-path execution without loader overrides'],
    'scope':'Original Apple x86_64 CoreEntitlements reconstruction. Only listed APIs/inputs tested; full app signing remains unverified.',
    'allocator_compatibility':'Type metadata is ignored; allocations and C++ bad_alloc behavior forward to the existing allocator.',
    'loader_mode':'RTLD_LAZY as used by xcodebuild. Strict NOW still exposes legacy CoreGraphics gaps.'})
Path('artifacts/coreentitlements-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Installed original Apple CoreEntitlements reconstruction and DER adapter after semantic, relocation and independent decoding checks.'
