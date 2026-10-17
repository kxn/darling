#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
framework=System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation
mkdir -p runtime/compat-backups runtime/build-corefoundation-compat
backup=runtime/compat-backups/CoreFoundation
if [[ ! -e $backup ]]; then
    cp "$guest/$framework" "$backup"
fi
cp "$backup" "$guest/usr/lib/libCF.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/libCF.dylib" /usr/lib/libCF.dylib
clang-19 -target x86_64-apple-macos11 \
    -isysroot "$project/vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk" \
    -I "$project/vendor/darling/basic-headers" -O2 -fPIC \
    -c scripts/corefoundation-compat.c -o runtime/build-corefoundation-compat/compat.o
sdk="$project/runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -fPIC -O2 \
    -c scripts/constant-collections.m -o runtime/build-corefoundation-compat/collections.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation \
    -compatibility_version 150.0.0 -current_version 1153.18.0 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -lobjc -reexport_library "$guest/usr/lib/libCF.dylib" \
    -o runtime/build-corefoundation-compat/CoreFoundation runtime/build-corefoundation-compat/compat.o \
    runtime/build-corefoundation-compat/collections.o
cp runtime/build-corefoundation-compat/CoreFoundation "$guest/$framework"
