#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
sdk="$project/vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
mkdir -p runtime/compat-backups runtime/build-trace-compat
backup=runtime/compat-backups/libsystem_trace.dylib
if [[ ! -e $backup ]]; then
    cp "$guest/usr/lib/system/libsystem_trace.dylib" "$backup"
fi
cp "$backup" "$guest/usr/lib/libTrace.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/libTrace.dylib" /usr/lib/libTrace.dylib
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -I "$project/vendor/darling/basic-headers" -O2 -fPIC \
    -c scripts/trace-compat.c -o runtime/build-trace-compat/compat.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /usr/lib/system/libsystem_trace.dylib -compatibility_version 1.0.0 \
    -current_version 1.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem \
    -reexport_library "$guest/usr/lib/libTrace.dylib" \
    -o runtime/build-trace-compat/libsystem_trace.dylib runtime/build-trace-compat/compat.o
cp runtime/build-trace-compat/libsystem_trace.dylib "$guest/usr/lib/system/libsystem_trace.dylib"
