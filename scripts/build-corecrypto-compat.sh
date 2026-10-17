#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
mkdir -p runtime/build-corecrypto-compat runtime/compat-backups
backup=runtime/compat-backups/libcorecrypto.dylib
if [[ ! -e $backup ]]; then cp "$guest/usr/lib/system/libcorecrypto.dylib" "$backup"; fi
cp "$backup" "$guest/usr/lib/libCCry.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/libCCry.dylib" /usr/lib/libCCry.dylib
clang-19 -target x86_64-apple-macos11 -O2 -fPIC -DPLATFORM_MacOSX=1 \
    -isysroot "$project/vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk" \
    -I "$project/vendor/darling/basic-headers" \
    -I "$project/vendor/darling/src/external/corecrypto/include" \
    -c scripts/corecrypto-compat.c -o runtime/build-corecrypto-compat/compat.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /usr/lib/system/libcorecrypto.dylib -compatibility_version 1.0.0 \
    -current_version 0.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem \
    -reexport_library "$guest/usr/lib/libCCry.dylib" \
    -o runtime/build-corecrypto-compat/libcorecrypto.dylib runtime/build-corecrypto-compat/compat.o
cp runtime/build-corecrypto-compat/libcorecrypto.dylib "$guest/usr/lib/system/libcorecrypto.dylib"
