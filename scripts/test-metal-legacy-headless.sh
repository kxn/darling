#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
scripts/build-metal-legacy-headless.sh > logs/build-metal-legacy-headless.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
guest=runtime/rootfs/usr/libexec/darling
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" -c fixtures/hello/metal-legacy-headless.m -o runtime/metal-legacy-headless/test.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 -syslibroot "$guest" \
    -L "$guest/usr/lib" -lSystem -lobjc -framework Foundation runtime/metal-legacy-headless/test.o \
    -o artifacts/metal-legacy-headless
workspace=/Volumes/SystemRoot/workspace
run_texture_test() {
    timeout -k 5 30 bin/darling shell /usr/bin/env \
        DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
        DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
        "$workspace/artifacts/metal-legacy-headless" "$workspace/runtime/native-framework-stage/Metal.framework/Metal" "$@"
}
run_texture_test > logs/metal-legacy-headless-execute.log 2>&1
rg -q '^DARLING_LEGACY_TEXTURE_CLASS_NATIVE_METAL_REEXPORT_IDENTITY_OWNER_OK$' logs/metal-legacy-headless-execute.log
status=0
run_texture_test --unsupported > logs/metal-legacy-headless-unsupported.log 2>&1 || status=$?
if [[ $status == 0 || $status == 99 || $status == 124 || $status == 137 ]]; then
    echo 'Unsupported original texture operation did not reject explicitly.' >&2;exit 1
fi
rg -q 'Method invocation in unsupported class width in MTLTextureInternal' logs/metal-legacy-headless-unsupported.log
python3 - "$status" <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sys
r={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
 'source':json.loads(Path('config/metal-legacy-headless.json').read_text()),
 'library_sha256':hashlib.sha256(Path('runtime/native-library-stage/libDarlingMetalLegacyHeadless.dylib').read_bytes()).hexdigest(),
 'metal_image_sha256':hashlib.sha256(Path('runtime/native-framework-stage/Metal.framework/Metal').read_bytes()).hexdigest(),
 'reexport_class_identity_and_owner_verified':True,'unsupported_texture_operation_rejected':True,
 'unsupported_operation_exit_status':int(sys.argv[1]),'gpu_execution_supported':False,'full_compatibility':False}
Path('artifacts/metal-legacy-headless-compat.json').write_text(json.dumps(r,indent=2)+'\n')
PY
