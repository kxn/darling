#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/remote-service-discovery.m" \
    -framework Foundation -o "$workspace/artifacts/remote-service-discovery-abi-smoke" \
    > logs/remote-service-discovery-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-fdr:$workspace/runtime/rebuilt-amsupport:$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/remote-service-discovery-abi-smoke" \
    "$workspace/runtime/rebuilt-remote-service-discovery/RemoteServiceDiscovery" \
    > logs/remote-service-discovery-client-execute.log 2>&1
for marker in ORIGINAL_RSD_CLASSES_PROTOCOL_REGISTERED_OK ORIGINAL_RSD_QUERY_INIT_COPY_MUTATE_DEALLOC_OK \
    ORIGINAL_RSD_NSDATA_CATEGORY_SHA256_VECTOR_OK; do
    rg -q "^$marker\$" logs/remote-service-discovery-client-execute.log
done
offset=$(python3 - <<'PY'
import json
report=json.load(open('runtime/rebuilt-remote-service-discovery/reconstruction.json'))
print(next(slot['offset'] for slot in report['lazy_binding_slots']
    if slot['symbol']=='_SecTrustCopyCertificateChain'))
PY
)
if timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_LIBRARY_PATH="$workspace/runtime/rebuilt-fdr:$workspace/runtime/rebuilt-amsupport:$workspace/runtime/rebuilt-der" \
    "$workspace/artifacts/remote-service-discovery-abi-smoke" \
    "$workspace/runtime/rebuilt-remote-service-discovery/RemoteServiceDiscovery" "$offset" \
    > logs/remote-service-discovery-missing-security.log 2>&1; then
    echo 'Missing Security function unexpectedly executed.' >&2; exit 1
fi
rg -q '^CALLING_ORIGINAL_MISSING_SECURITY_IMPORT$' logs/remote-service-discovery-missing-security.log
rg -q 'Symbol not found: _SecTrustCopyCertificateChain' logs/remote-service-discovery-missing-security.log
echo 'Original RSD classes/protocol, real query object lifecycle and NSData SHA256 passed; device discovery is unverified.'
