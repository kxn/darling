#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/apfs-fletcher.c -o artifacts/apfs-fletcher-smoke.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem artifacts/apfs-fletcher-smoke.o -o artifacts/apfs-fletcher-smoke
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
p=Path.cwd();build=p/'runtime/rebuilt-apfs';r=json.loads((build/'reconstruction.json').read_text())
if hashlib.sha256((build/'APFS').read_bytes()).hexdigest()!=r['staged_image_sha256']:
    raise ValueError('APFS checksum test image differs from reconstruction report')
n=runpy.run_path('scripts/dsc-image.py',init_globals={
    'REFERENCE_CACHE_PATH':p/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':p/'runtime/fullsystem-libraries'})
base=n['image']('/System/Library/PrivateFrameworks/APFS.framework/Versions/A/APFS').base
source=p/'runtime/fullsystem-libraries/System/Library/PrivateFrameworks/APFS.framework/Versions/A/APFS'
symbols={line.split()[-1]:int(line.split()[0],16) for line in subprocess.check_output(
    ['llvm-nm-19','--defined-only',str(source)],text=True).splitlines() if len(line.split())==3}
offsets=[hex(symbols['_fletcher64_'+kind]-base) for kind in ('sse','avx1','avx2')]
command=['timeout','-k','5','30','bin/darling','shell',
    '/Volumes/SystemRoot/workspace/artifacts/apfs-fletcher-smoke',
    '/Volumes/SystemRoot/workspace/runtime/rebuilt-apfs/APFS',*offsets]
with Path('logs/apfs-fletcher-execute.log').open('w') as log:
    subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
output=Path('logs/apfs-fletcher-execute.log').read_text()
if 'ORIGINAL_APFS_FLETCHER_SIMD_AGREES_WITH_SCALAR_MODULAR_REFERENCE_OK' not in output:
    raise ValueError('Missing original checksum success marker')
report={'checked_at':datetime.now(timezone.utc).isoformat(),
    'original_image_sha256':r['original_image_sha256'],'staged_image_sha256':r['staged_image_sha256'],
    'installed':False,'load_verified':True,'checksum_execution_verified':True,
    'pinned_vector_constant_ranges':len(r['code_analysis']['constant_ranges']),
    'tests':['independent scalar modulo-2^32-1 reference','17 sizes including vector boundaries',
        'three input alignments','four initial seeds','CPU-supported SSE/AVX/AVX2 variants'],
    'execution_log':output,'full_compatibility':False,
    'scope':'Original checksum routines only; APFS volumes, disk management and encryption services unverified.'}
Path('artifacts/apfs-fletcher-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original APFS Fletcher64 vector routines passed an independent scalar reference.'
