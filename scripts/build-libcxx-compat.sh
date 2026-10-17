#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
guest="$project/runtime/rootfs/usr/libexec/darling"
sdk="$project/vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
mkdir -p runtime/compat-backups runtime/build-libcxx-compat
backup=runtime/compat-backups/libc++.1.dylib
if [[ ! -e $backup ]]; then
    cp "$guest/usr/lib/libc++.1.dylib" "$backup"
fi
cp "$backup" "$guest/usr/lib/libc++0.dylib"
python3 scripts/macho-set-id.py "$guest/usr/lib/libc++0.dylib" /usr/lib/libc++0.dylib
clang++-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -I "$project/vendor/darling/basic-headers" -fno-exceptions -fno-rtti -nostdinc++ \
    -O2 -fPIC -c scripts/libcxx-compat.cpp -o runtime/build-libcxx-compat/compat.o
for unit in operations directory_iterator int128_builtins; do
    clang++-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
        -I "$project/vendor/darling/basic-headers" -nostdinc++ \
        -I "$project/vendor/darling/src/external/libcxx/include" \
        -D_LIBCPP_BUILDING_LIBRARY=1 -DPLATFORM_MacOSX=1 -std=c++17 -O2 -fPIC \
        -c "$project/vendor/darling/src/external/libcxx/src/filesystem/$unit.cpp" \
        -o "runtime/build-libcxx-compat/$unit.o"
done
clang++-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -I "$project/vendor/darling/basic-headers" -nostdinc++ \
    -I "$project/vendor/darling/src/external/libcxx/include" \
    -D_LIBCPP_BUILDING_LIBRARY=1 -DPLATFORM_MacOSX=1 \
    -D_LIBCPP_ABI_BAD_FUNCTION_CALL_KEY_FUNCTION=1 -std=c++17 -O2 -fPIC \
    -c "$project/vendor/darling/src/external/libcxx/src/functional.cpp" \
    -o runtime/build-libcxx-compat/functional.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /usr/lib/libc++.1.dylib -compatibility_version 1.0.0 \
    -current_version 1.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem \
    -reexport_library "$guest/usr/lib/libc++0.dylib" \
    -o runtime/build-libcxx-compat/libc++.1.dylib runtime/build-libcxx-compat/compat.o \
    runtime/build-libcxx-compat/operations.o runtime/build-libcxx-compat/directory_iterator.o \
    runtime/build-libcxx-compat/int128_builtins.o runtime/build-libcxx-compat/functional.o
cp runtime/build-libcxx-compat/libc++.1.dylib "$guest/usr/lib/libc++.1.dylib"
