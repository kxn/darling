#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,shutil,subprocess
c=json.loads(Path('config/person-name-compat.json').read_text());source=Path('vendor/vibe-foundation')
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==c['commit']
for name,expected in c['files'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==expected
destination=Path('runtime/foundation-additions/include/Foundation');destination.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source/'include/Foundation/NSPersonNameComponents.h',destination/'NSPersonNameComponents.h')
PY
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -I runtime/foundation-additions/include -O2 \
    -c vendor/vibe-foundation/src/NSPersonNameComponents.m -o runtime/foundation-additions/person-name-components.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -lobjc -framework Foundation \
    -install_name /usr/lib/libDarlingPersonName.dylib runtime/foundation-additions/person-name-components.o \
    -o runtime/native-library-stage/libDarlingPersonName.dylib.pending
mv runtime/native-library-stage/libDarlingPersonName.dylib.pending runtime/native-library-stage/libDarlingPersonName.dylib
