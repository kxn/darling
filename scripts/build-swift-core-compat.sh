#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
mkdir -p runtime/compat-backups runtime/build-swift-core-compat
backup=runtime/compat-backups/libswiftCore.dylib
if [[ ! -e $backup ]]; then
    cp "$guest/usr/lib/swift/libswiftCore.dylib" "$backup"
fi
cp "$backup" "$guest/usr/lib/swift/libswiftC0.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/swift/libswiftC0.dylib" /usr/lib/swift/libswiftC0.dylib
clang-19 -target x86_64-apple-macos11 -c scripts/swift-core-compat.S \
    -o runtime/build-swift-core-compat/compat.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /usr/lib/swift/libswiftCore.dylib -compatibility_version 1.0.0 \
    -current_version 0.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem \
    -rpath /usr/lib/swift -reexport_library "$guest/usr/lib/swift/libswiftC0.dylib" \
    -o runtime/build-swift-core-compat/libswiftCore.dylib runtime/build-swift-core-compat/compat.o
cp runtime/build-swift-core-compat/libswiftCore.dylib "$guest/usr/lib/swift/libswiftCore.dylib"
