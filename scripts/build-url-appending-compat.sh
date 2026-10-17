#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
c=json.loads(Path('config/url-appending-compat.json').read_text());r=Path('vendor/swift-foundation-reference')
assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()==c['commit']
for name,expected in c['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==expected
b=c['backend_reference'];r=Path(b['root'])
assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()==b['commit']
for name,expected in b['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==expected
f=json.loads(Path('config/foundation-xpc-exports.json').read_text())
assert hashlib.sha256(Path(f['source']).read_bytes()).hexdigest()==f['source_sha256']
PY
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
mkdir -p runtime/url-appending-compat
clang-19 -target x86_64-apple-macos15.4 -isysroot "runtime/state/prefix$sdk" \
    -c scripts/url-directory-path-objc.m -o runtime/url-appending-compat/directory-path.o
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/swift-frontend" -c -whole-module-optimization \
    -parse-as-library -O -enable-library-evolution -swift-version 5 -module-name DarlingURLCompat \
    -target x86_64-apple-macos15.4 -sdk "$sdk" "$workspace/scripts/url-appending-compat.swift" \
    -o "$workspace/runtime/url-appending-compat/compat.o" > logs/url-appending-compat-compile.log 2>&1
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" "$workspace/runtime/url-appending-compat/compat.o" \
    "$workspace/runtime/url-appending-compat/directory-path.o" -L/usr/lib/swift \
    -L"$toolchain/usr/lib/swift/macosx" -lswiftCore -lswiftFoundation -lswiftObjectiveC -framework Foundation \
    -Wl,-rpath,/usr/lib/swift -Wl,-install_name,/usr/lib/libDarlingURLCompat.dylib \
    -o "$workspace/runtime/native-library-stage/libDarlingURLCompat.dylib.pending" > logs/url-appending-compat-link.log 2>&1
mv runtime/native-library-stage/libDarlingURLCompat.dylib.pending runtime/native-library-stage/libDarlingURLCompat.dylib
