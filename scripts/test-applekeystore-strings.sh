#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/applekeystore-strings.swift" -target x86_64-apple-macos14 \
    -sdk "$sdk" -module-name AppleKeyStoreStrings -o "$workspace/artifacts/applekeystore-strings.o" \
    > logs/applekeystore-strings-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14 \
    -isysroot "$sdk" "$workspace/artifacts/applekeystore-strings.o" -L/usr/lib/swift \
    -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftSwiftOnoneSupport -lswiftDarwin \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/applekeystore-strings-smoke" \
    > logs/applekeystore-strings-link.log 2>&1
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,struct,subprocess
p=Path.cwd();build=p/'runtime/rebuilt-applekeystore';r=json.loads((build/'reconstruction.json').read_text())
if hashlib.sha256((build/'AppleKeyStore').read_bytes()).hexdigest()!=r['staged_image_sha256']:
    raise ValueError('Test image differs from reconstruction report')
ns=runpy.run_path('scripts/dsc-image.py',init_globals={
    'REFERENCE_CACHE_PATH':p/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':p/'runtime/fullsystem-libraries'})
obj=ns['image']('/System/Library/PrivateFrameworks/AppleKeyStore.framework/Versions/A/AppleKeyStore')
anchor=next(name[1:] for name,value in obj.exports.items() if name.startswith('_aks_') and value[0]=='address')
arguments=['bin/darling','shell','/usr/bin/env',
    'DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/native-framework-stage',
    'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift',
    '/Volumes/SystemRoot/workspace/artifacts/applekeystore-strings-smoke',
    '/Volumes/SystemRoot/workspace/runtime/rebuilt-applekeystore/AppleKeyStore',anchor]
literals=r['swift_metadata']['immortal_string_literals']
if not literals:raise ValueError('No restored original literals to validate')
for literal in literals:
    slot=int(literal['slot'],0);value=ns['pointer'](slot)&0x0fffffffffffffff
    payload=ns['read'](value+32,literal['utf8_length'])
    if hashlib.sha256(payload).hexdigest()!=literal['payload_sha256']:raise ValueError('Literal source digest mismatch')
    arguments.extend([format(slot-8-obj.base,'x'),payload.hex()])
with Path('logs/applekeystore-strings-execute.log').open('w') as log:
    subprocess.run(['timeout','-k','5','30',*arguments],stdout=log,stderr=subprocess.STDOUT,check=True)
if 'ORIGINAL_APPLEKEYSTORE_SWIFT_LITERAL_VALUES_UTF8_COPY_ON_WRITE_OK' not in Path('logs/applekeystore-strings-execute.log').read_text():
    raise ValueError('Missing runtime success marker')
report={'checked_at':datetime.now(timezone.utc).isoformat(),
    'original_image_sha256':r['original_image_sha256'],'staged_image_sha256':r['staged_image_sha256'],
    'installed':False,'load_verified':True,'literal_values_verified':len(literals),
    'tests':['actual mapped original String values','exact UTF-8 bytes against reference cache',
        'Swift value equality','copy-on-write append preserves original and second copy'],
    'full_compatibility':False,'scope':'Swift literal relocation only. Key storage, hardware services, security operations and signing unverified.'}
Path('artifacts/applekeystore-string-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original AppleKeyStore Swift literal values and copy-on-write passed.'
