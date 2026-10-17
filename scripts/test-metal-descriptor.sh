#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" -fobjc-arc -fblocks "$workspace/fixtures/hello/metal-descriptor.m" \
    -framework Foundation -o "$workspace/artifacts/metal-descriptor-smoke" \
    > logs/metal-descriptor-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/metal-descriptor-smoke" \
    "$workspace/runtime/native-framework-stage/Metal.framework/Metal" \
    > logs/metal-descriptor-execute.log 2>&1
rg -q '^ORIGINAL_METAL_RESIDENCY_DESCRIPTOR_DEFAULTS_LABEL_COPY_INDEPENDENT_STATE_OK$' logs/metal-descriptor-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
source=Path('runtime/rebuilt-metal/reconstruction.json')
r=json.loads(source.read_text());stage=Path('runtime/native-framework-stage/Metal.framework/Metal')
assert hashlib.sha256(stage.read_bytes()).hexdigest()==r['staged_image_sha256']
report={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
    'original_image_sha256':r['original_image_sha256'],'staged_image_sha256':r['staged_image_sha256'],
    'selected_descriptor_api_execution_verified':True,
    'scope':'Original MTLResidencySetDescriptor construction, defaults, label copy and independent instance state. No GPU, driver, device, shader or command queue execution verified.',
    'full_compatibility':False}
Path('artifacts/metal-descriptor-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original Metal software descriptor passed construction, defaults, label copy and independent state.'
