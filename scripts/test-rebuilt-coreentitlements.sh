#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/coreentitlements.m" \
    -framework Foundation -o "$workspace/artifacts/coreentitlements-abi-smoke" \
    > logs/coreentitlements-client-compile.log 2>&1
timeout 45 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/coreentitlements-abi-smoke" \
    "$workspace/runtime/rebuilt-coreentitlements/libCoreEntitlements.dylib" \
    > logs/coreentitlements-client-execute.log 2>&1
rg -q '^ORIGINAL_APPLE_COREENTITLEMENTS_SEMANTICS_OK$' logs/coreentitlements-client-execute.log
cp runtime/rebuilt-coreentitlements/libCoreEntitlements.dylib runtime/rebuilt-coreentitlements/libCEBlocker.dylib
python3 scripts/macho-set-id.py runtime/rebuilt-coreentitlements/libCEBlocker.dylib /usr/lib/libCEBlocker.dylib
timeout 45 bin/darling shell /usr/bin/env DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/coreentitlements-abi-smoke" \
    "$workspace/runtime/rebuilt-coreentitlements/libCoreEntitlements.dylib" --slide \
    > logs/coreentitlements-client-slide.log 2>&1
rg -q '^CE_SLIDE_APPLIED$' logs/coreentitlements-client-slide.log
rg -q '^CE_TWO_DISTINCT_COPIES_EXECUTED_OK$' logs/coreentitlements-client-slide.log
rg -q '^ORIGINAL_APPLE_COREENTITLEMENTS_SEMANTICS_OK$' logs/coreentitlements-client-slide.log
rg -q '^CE_MALFORMED_LENGTH_TRUNCATION_DUPLICATE_KEYS_REJECTED$' logs/coreentitlements-client-slide.log
python3 scripts/verify-entitlements-der.py > logs/coreentitlements-independent-der.log
openssl asn1parse -inform DER -in artifacts/coreentitlements-nested.der > logs/coreentitlements-openssl-asn1.log
echo 'Original Apple CoreEntitlements serialized/parsed actual DER, enforced positive/negative subsets and rejected malformed input.'
