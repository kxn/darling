#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
source_runtime="$project/runtime/swift633-extract/usr/lib/swift/macosx"
guest="$project/runtime/rootfs/usr/libexec/darling"
destination="$project/runtime/state/prefix/usr/lib/swift"
mkdir -p "$destination" runtime/build-swift633
for library in "$source_runtime"/libswift*.dylib; do
    if [[ ${library##*/} != libswiftCore.dylib ]]; then
        cp -a "$library" "$destination/"
    fi
done
cp "$source_runtime/libswiftCore.dylib" "$destination/libswiftC6.dylib"
python3 scripts/macho-set-id.py "$destination/libswiftC6.dylib" /usr/lib/swift/libswiftC6.dylib
clang-19 -target x86_64-apple-macos13.0 -O2 -fPIC \
    -isysroot "$project/vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk" \
    -I "$project/vendor/darling/basic-headers" \
    -c scripts/swift633-compat.c -o runtime/build-swift633/compat.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 13.0 13.0 \
    -install_name /usr/lib/swift/libswiftCore.dylib -compatibility_version 1.0.0 \
    -current_version 0.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem -lobjc \
    -reexport_library "$destination/libswiftC6.dylib" \
    -o runtime/build-swift633/libswiftCore.dylib runtime/build-swift633/compat.o
cp runtime/build-swift633/libswiftCore.dylib "$destination/libswiftCore.dylib"
# Xcode also links the system demangler directly. Its toolchain contains the
# genuine implementation; relocate a copy, keeping Xcode.app untouched.
cp "$project/runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/libswiftDemangle.dylib" \
    "$destination/libswiftDemangle.dylib"
llvm-install-name-tool-19 -id /usr/lib/swift/libswiftDemangle.dylib "$destination/libswiftDemangle.dylib"
