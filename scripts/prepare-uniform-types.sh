#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/build-uniform-types.py
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/uniform-types.swift" -target x86_64-apple-macos14.0 -sdk "$sdk" \
    -module-name UniformTypesABISmoke -o "$workspace/artifacts/uniform-types-abi-smoke.o" \
    > logs/uniform-types-client-compile.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/artifacts/uniform-types-abi-smoke.o" \
    -L/usr/lib/swift -lswiftCore -lswiftSwiftOnoneSupport -lswiftUniformTypeIdentifiers -framework Foundation \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/uniform-types-abi-smoke" \
    > logs/uniform-types-client-link.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/build-uniform-types" \
    "$workspace/artifacts/uniform-types-abi-smoke" > logs/uniform-types-client-execute.log 2>&1
rg -q '^SWIFT_UTI_IDENTIFIERS_CONFORMANCE_HASH_CODING_OK$' logs/uniform-types-client-execute.log
python3 - <<'PY'
from pathlib import Path
import hashlib, json, re, shutil, subprocess
source=Path('runtime/build-uniform-types/libswiftUniformTypeIdentifiers.dylib')
consumer=Path('runtime/state/prefix/Applications/Xcode.app/Contents/SharedFrameworks/XCTHarness.framework/Versions/A/XCTHarness')
bindings=subprocess.check_output(['llvm-objdump-19','--macho','--chained-fixups',str(consumer)],text=True)
required=sorted({re.search(r'name_offset = \d+ \(([^\n]+)\)',group).group(1)
    for group in bindings.split('dyld chained import[')[1:]
    if re.search(r'lib_ordinal = \d+ \(libswiftUniformTypeIdentifiers\)',group)})
if not required:raise SystemExit('No UTI imports found in original XCTHarness')
exports={x.split()[-1] for x in subprocess.check_output(['llvm-nm-19','--defined-only','--extern-only',str(source)],text=True).splitlines() if x.split()}
if set(required)-exports:raise SystemExit('Missing UTI exports: '+repr(set(required)-exports))
shutil.copyfile(source,'runtime/state/prefix/usr/lib/swift/libswiftUniformTypeIdentifiers.dylib')
data=json.loads(Path('runtime/build-uniform-types/sdk-types.json').read_text())
Path('artifacts/uniform-types-compat.json').write_text(json.dumps({
    'sdk_header_sha256':data['header_sha256'],'documented_identifiers':len(data['entries']),
    'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'xctharness_required_exports':len(required),'original_sdk_client_test':'passed',
    'semantic_tests':['identifiers','documented conformance edges','equality/hash','coding roundtrip'],
    'unsupported':['Objective-C bridging','LaunchServices registration/tag lookup','localized descriptions','device-model UTI lookup'],
    'scope':'Documented SDK value subset only; existing Darling Objective-C UTI stubs remain unmodified.'
},indent=2)+'\n')
PY
echo 'Installed tested Swift UTI value subset derived from 128 SDK definitions.'
