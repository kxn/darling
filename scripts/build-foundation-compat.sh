#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
framework=System/Library/Frameworks/Foundation.framework/Versions/C/Foundation
mkdir -p runtime/compat-backups runtime/build-foundation-compat
backup=runtime/compat-backups/Foundation
if [[ ! -e $backup ]]; then
    cp "$guest/$framework" "$backup"
fi
cp "$backup" "$guest/usr/lib/libFND.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/libFND.dylib" /usr/lib/libFND.dylib
sdk="$project/runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fPIC -O2 \
    -c scripts/constant-numbers.m -o runtime/build-foundation-compat/numbers.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /System/Library/Frameworks/Foundation.framework/Versions/C/Foundation \
    -compatibility_version 300.0.0 -current_version 1349.0.0 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -lobjc -rpath /usr/lib/swift \
    -F "$guest/System/Library/Frameworks" -framework CoreFoundation \
    -reexport_library "$guest/usr/lib/libFND.dylib" \
    -reexport_library "$guest/usr/lib/swift/libswiftFoundation.dylib" \
    -o runtime/build-foundation-compat/Foundation runtime/build-foundation-compat/numbers.o
cp runtime/build-foundation-compat/Foundation "$guest/$framework"
