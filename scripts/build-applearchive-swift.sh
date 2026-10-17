#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 90 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c -whole-module-optimization \
    -parse-as-library -Onone -enable-library-evolution -swift-version 5 -module-name AppleArchive \
    -target x86_64-apple-macos14.4 -sdk "$sdk" -I "$workspace/scripts/applearchive-swift-c" \
    "$workspace/scripts/applearchive-swift.swift" \
    -emit-module-path "$workspace/runtime/build-applearchive/AppleArchive.swiftmodule" \
    -o "$workspace/runtime/build-applearchive/AppleArchive.o" > logs/build-applearchive-swift.log 2>&1
timeout 60 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib \
    -target x86_64-apple-macos14.4 -isysroot "$sdk" \
    "$workspace/runtime/build-applearchive/AppleArchive.o" \
    -L/usr/lib/swift -L"$toolchain/usr/lib/swift/macosx" \
    -lswiftCore -lswiftSwiftOnoneSupport -lswiftSystem -lAppleArchive \
    -Wl,-install_name,/usr/lib/swift/libswiftAppleArchive.dylib \
    -Wl,-compatibility_version,1.0 -Wl,-current_version,450.100.3 \
    -o "$workspace/runtime/build-applearchive/libswiftAppleArchive.dylib" \
    > logs/link-applearchive-swift.log 2>&1
timeout 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c \
    "$workspace/fixtures/hello/applearchive.swift" -target x86_64-apple-macos14.4 -sdk "$sdk" \
    -module-name AppleArchiveABISmoke -o "$workspace/artifacts/swift-applearchive-abi-smoke.o" \
    > logs/swift-applearchive-client-compile.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.4 \
    -isysroot "$sdk" "$workspace/artifacts/swift-applearchive-abi-smoke.o" \
    -L/usr/lib/swift -lswiftCore -lswiftSwiftOnoneSupport -lswiftSystem -lswiftAppleArchive \
    -Wl,-rpath,/usr/lib/swift -o "$workspace/artifacts/swift-applearchive-abi-smoke" \
    > logs/swift-applearchive-client-link.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/build-applearchive" \
    "$workspace/artifacts/swift-applearchive-abi-smoke" > logs/swift-applearchive-client-execute.log 2>&1
rg -q '^SWIFT_APPLEARCHIVE_FILE_STREAM_OK_UNSUPPORTED_DECODE_REJECTED$' logs/swift-applearchive-client-execute.log
cp runtime/build-applearchive/libswiftAppleArchive.dylib runtime/state/prefix/usr/lib/swift/libswiftAppleArchive.dylib
python3 - <<'PY'
from pathlib import Path
import hashlib, json
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
Path('artifacts/applearchive-compat.json').write_text(json.dumps({
    'implementation':'project-local byte-stream subset',
    'c_library_sha256':digest('runtime/build-applearchive/libAppleArchive.dylib'),
    'swift_library_sha256':digest('runtime/build-applearchive/libswiftAppleArchive.dylib'),
    'original_sdk_clients':'C and Swift file-stream tests passed',
    'unsupported':['compression/decompression','archive encode/decode/extract','archive processing'],
    'unsupported_swift_factories':'print diagnostic, set ENOTSUP and return nil; processing throws',
    'full_applearchive_compatibility':False
},indent=2)+'\n')
PY
echo 'Installed partial Swift AppleArchive overlay: file streams/flags only; archive processing explicitly fails.'
