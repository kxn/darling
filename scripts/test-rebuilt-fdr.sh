#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/fdr.c" \
    -framework CoreFoundation -o "$workspace/artifacts/fdr-abi-smoke" \
    > logs/fdr-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-amsupport:$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/fdr-abi-smoke" "$workspace/runtime/rebuilt-fdr/libFDR.dylib" \
    > logs/fdr-client-execute.log 2>&1
rg -q '^ORIGINAL_FDR_CFTYPE_REGISTRATION_OK$' logs/fdr-client-execute.log
rg -q '^ORIGINAL_FDR_TAG_CONVERSION_OK$' logs/fdr-client-execute.log
rg -q '^ORIGINAL_FDR_MD5_KNOWN_VECTOR_OK$' logs/fdr-client-execute.log
echo 'Original FDR: CF type registration, tag conversion and MD5 known vector passed.'
