#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 45 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos14.0 \
    -isysroot "$sdk" "$workspace/fixtures/hello/core-emoji.c" -framework CoreFoundation \
    -o "$workspace/artifacts/core-emoji-smoke" > logs/core-emoji-client-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="${CORE_EMOJI_LIBRARY_PATH-$workspace/runtime/rebuilt-der}" \
    "$workspace/artifacts/core-emoji-smoke" "${1-$workspace/runtime/rebuilt-core-emoji/CoreEmoji}" \
    > logs/core-emoji-client-execute.log 2>&1
rg -q '^ORIGINAL_CORE_EMOJI_ASCII_NEGATIVE_EMOJI_POSITIVE_OK$' logs/core-emoji-client-execute.log
echo 'Original CoreEmoji rejects ASCII/null and identifies actual Unicode emoji.'
