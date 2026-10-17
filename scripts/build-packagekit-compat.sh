#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
framework=System/Library/PrivateFrameworks/PackageKit.framework/Versions/A/PackageKit
mkdir -p runtime/compat-backups runtime/build-packagekit-compat
backup=runtime/compat-backups/PackageKit
if [[ ! -e $backup ]]; then
    cp "$guest/$framework" "$backup"
fi
cp "$backup" "$guest/usr/lib/libPK.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/libPK.dylib" /usr/lib/libPK.dylib
clang-19 -target x86_64-apple-macos11 -fPIC -O2 \
    -c scripts/packagekit-compat.m -o runtime/build-packagekit-compat/compat.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /System/Library/PrivateFrameworks/PackageKit.framework/Versions/A/PackageKit \
    -compatibility_version 1.0.0 -current_version 1.0.0 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -lobjc -F "$guest/System/Library/Frameworks" \
    -framework Foundation -framework CoreFoundation \
    -reexport_library "$guest/usr/lib/libPK.dylib" \
    -o runtime/build-packagekit-compat/PackageKit runtime/build-packagekit-compat/compat.o
cp runtime/build-packagekit-compat/PackageKit "$guest/$framework"
