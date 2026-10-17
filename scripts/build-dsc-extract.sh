#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p runtime/tools
clang-19 -target x86_64-apple-macos11 -fblocks -O2 \
    -isysroot runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
    -c scripts/dsc-extract.c -o runtime/tools/dsc-extract.o
ld64.lld-19 -arch x86_64 -platform_version macos 11.0 11.0 \
    -syslibroot runtime/rootfs/usr/libexec/darling \
    -L runtime/rootfs/usr/libexec/darling/usr/lib -lSystem \
    -o runtime/tools/dsc-extract runtime/tools/dsc-extract.o
