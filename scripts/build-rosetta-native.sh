#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
mkdir -p runtime/build-rosetta-native
guest="$project/runtime/rootfs/usr/libexec/darling"
clang-19 -target x86_64-apple-macos11 -O2 -c scripts/rosetta-native.c \
    -o runtime/build-rosetta-native/compat.o
ld64.lld-19 -dylib -arch x86_64 -platform_version macos 11.0 11.0 \
    -install_name /usr/lib/libRosetta.dylib -compatibility_version 1.0.0 \
    -current_version 1.0.0 -syslibroot "$guest" -L "$guest/usr/lib" -lSystem \
    -o runtime/build-rosetta-native/libRosetta.dylib runtime/build-rosetta-native/compat.o
cp runtime/build-rosetta-native/libRosetta.dylib "$guest/usr/lib/libRosetta.dylib"
