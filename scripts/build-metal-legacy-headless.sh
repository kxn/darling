#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
r=Path('vendor/darling/src/external/metal');c=json.loads(Path('config/metal-legacy-headless.json').read_text())
assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()==c['commit']
for f,h in c['files'].items():assert hashlib.sha256((r/f).read_bytes()).hexdigest()==h
Path('runtime/metal-legacy-headless').mkdir(exist_ok=True)
PY
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -std=c++17 -DDARLING_METAL_ENABLED=0 \
    -I vendor/darling/src/external/metal/private-include -I vendor/darling/src/external/metal/include \
    -c vendor/darling/src/external/metal/src/Metal/MTLTexture.mm -o runtime/metal-legacy-headless/texture.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -lobjc -framework Foundation \
    -install_name /usr/lib/libDarlingMetalLegacyHeadless.dylib runtime/metal-legacy-headless/texture.o \
    -o runtime/native-library-stage/libDarlingMetalLegacyHeadless.dylib.pending
mv runtime/native-library-stage/libDarlingMetalLegacyHeadless.dylib.pending runtime/native-library-stage/libDarlingMetalLegacyHeadless.dylib
