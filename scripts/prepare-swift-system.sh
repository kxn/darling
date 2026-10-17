#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
revision=0b30161977799fd949f7f6848586b82ff6764f73
if [[ ! -d vendor/swift-system/.git ]]; then
    git init -q vendor/swift-system
    git -C vendor/swift-system remote add origin https://github.com/apple/swift-system.git
    git -C vendor/swift-system fetch --depth 1 origin "$revision"
    git -C vendor/swift-system checkout --detach FETCH_HEAD
fi
test "$(git -C vendor/swift-system rev-parse HEAD)" = "$revision"
python3 scripts/build-swift-system.py
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/system.swift" -target x86_64-apple-macos14.4 -sdk "$sdk" \
    -module-name SystemABISmoke -o "$workspace/artifacts/system-abi-smoke.o" \
    > logs/system-client-compile.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.4 \
    -isysroot "$sdk" "$workspace/artifacts/system-abi-smoke.o" \
    -L/usr/lib/swift -lswiftCore -lswiftSwiftOnoneSupport -lswiftSystem \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/system-abi-smoke" \
    > logs/system-client-link.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/build-swift-system" \
    "$workspace/artifacts/system-abi-smoke" > logs/system-client-execute.log 2>&1
rg -q '^SWIFT_SYSTEM_FILEPATH_IO_ERRNO_OK$' logs/system-client-execute.log
cp runtime/build-swift-system/libswiftSystem.dylib runtime/state/prefix/usr/lib/swift/libswiftSystem.dylib
python3 - <<'PY'
from pathlib import Path
import hashlib, json
source=Path('runtime/build-swift-system/libswiftSystem.dylib')
Path('artifacts/swift-system-compat.json').write_text(json.dumps({
    'source_revision':'0b30161977799fd949f7f6848586b82ff6764f73',
    'source_tag':'1.6.6','library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'original_sdk_client_test':'passed','semantic_tests':['FilePath','file IO','errno'],
    'scope':'Swift System implementation; only the listed APIs have been executed against Darling.'
},indent=2)+'\n')
PY
echo 'Installed Swift System 1.6.6 after original SDK client verified paths, file IO and errno.'
