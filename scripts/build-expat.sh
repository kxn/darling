#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
command -v clang-19 >/dev/null
command -v ld64.lld-19 >/dev/null
checkout() {
    local path=$1 url=$2 revision=$3
    if [[ ! -d $path/.git ]]; then
        git init "$path"
        git -C "$path" remote add origin "$url"
        git -C "$path" fetch --depth 1 origin "$revision"
        git -C "$path" checkout --detach FETCH_HEAD
    fi
    if [[ $(git -C "$path" rev-parse HEAD) != "$revision" ]]; then
        echo "Unexpected source revision in $path; refusing to replace local work." >&2
        exit 1
    fi
}
checkout vendor/darling https://github.com/darlinghq/darling.git \
    60ba801decee7a00782f74f6be4c8ffb013f79ff
checkout vendor/darling-expat https://github.com/darlinghq/darling-expat.git \
    70006a0c32d7c8653c11e53fc0c905f1bb498218
git -C vendor/darling submodule update --init --depth 1 \
    src/external/libc src/external/libplatform src/external/libpthread \
    src/external/libmalloc src/external/xnu src/external/AvailabilityVersions \
    src/external/architecture src/external/libcxx src/external/libcxxabi \
    src/external/copyfile src/external/libtrace src/external/corecrypto
mkdir -p runtime/build-expat
sdk="$project/vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
for unit in xmlparse xmlrole xmltok; do
    clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
        -I "$project/vendor/darling/basic-headers" -I "$project/vendor/darling-expat" \
        -DHAVE_EXPAT_CONFIG_H -DXML_ENABLE_VISIBILITY=1 -D__DARWIN_UNIX03 -fPIC -O2 \
        -c "$project/vendor/darling-expat/expat/lib/$unit.c" \
        -o "$project/runtime/build-expat/$unit.o"
done
guest="$project/runtime/rootfs/usr/libexec/darling"
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /usr/lib/libexpat.1.dylib -compatibility_version 7.0.0 \
    -current_version 8.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem \
    -o runtime/build-expat/libexpat.1.dylib \
    runtime/build-expat/xmlparse.o runtime/build-expat/xmlrole.o runtime/build-expat/xmltok.o
cp runtime/build-expat/libexpat.1.dylib "$guest/usr/lib/libexpat.1.dylib"
ln -sfn libexpat.1.dylib "$guest/usr/lib/libexpat.dylib"
