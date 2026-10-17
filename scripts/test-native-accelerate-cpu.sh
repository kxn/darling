#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 - <<'PY'
from pathlib import Path
import json,hashlib,runpy
root=Path.cwd();pins=json.loads(Path('config/cache-image-pins.json').read_text());target='vdsp'
r=json.loads(Path('runtime/rebuilt-vdsp/reconstruction.json').read_text())
assert hashlib.sha256(Path('runtime/native-library-stage/libvDSP.dylib').read_bytes()).hexdigest()==r['staged_image_sha256']
ns=runpy.run_path('scripts/dsc-image.py',init_globals={'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h','REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
base=ns['image'](pins[target]['path']).base
entry=next(e for e in r['function_resolvers'] if e['symbol']=='_vDSP_vsadd')
build=Path('runtime/native-accelerate-cpu');build.mkdir(exist_ok=True)
(build/'resolvers.h').write_text('#define ORIGINAL_VDSP_VSADD_STUB_OFFSET '+hex(int(entry['stub'],0)-base)+'UL\n#define ORIGINAL_VDSP_VSADD_RESOLVER_OFFSET '+hex(int(entry['resolver'],0)-base)+'UL\n')
PY
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout -k 5 60 bin/darling shell "$toolchain/usr/bin/clang" -target x86_64-apple-macos15.4 \
    -isysroot "$sdk" "$workspace/fixtures/hello/native-accelerate-cpu.c" -framework Foundation \
    -o "$workspace/artifacts/native-accelerate-cpu-smoke" > logs/native-accelerate-cpu-compile.log 2>&1
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH="$workspace/runtime/native-framework-stage" \
    DYLD_LIBRARY_PATH="$workspace/runtime/native-library-stage:$workspace/runtime/rebuilt-der:/usr/lib/swift" \
    "$workspace/artifacts/native-accelerate-cpu-smoke" "$workspace/runtime/native-framework-stage/Accelerate.framework/Accelerate" \
    > logs/native-accelerate-cpu-execute.log 2>&1
rg -q '^ORIGINAL_VDSP_RESOLVER_STRIDES_FLOAT_CASES_DOUBLE_OK 306$' logs/native-accelerate-cpu-execute.log
rg -q '^ORIGINAL_BNNS_GRAPH_COMPILE_OPTIONS_DEFAULTS_SET_GET_INDEPENDENCE_DESTROY_OK$' logs/native-accelerate-cpu-execute.log
rg -q '^ORIGINAL_VIMAGE_PADDED_ROWS_BYTE_FLOAT_BYTE_NUMERIC_ROUNDTRIP_OK$' logs/native-accelerate-cpu-execute.log
python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
targets=['accelerate','veclib','vimage','bnns','vdsp'];pins=json.loads(Path('config/cache-image-pins.json').read_text());images={}
for target in targets:
    r=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text());name=Path(pins[target]['path']).name
    file=Path('runtime/native-library-stage')/name if name.endswith('.dylib') else Path('runtime/native-framework-stage')/(name+'.framework')/name
    assert hashlib.sha256(file.read_bytes()).hexdigest()==r['staged_image_sha256']
    images[target]={'original_image_sha256':r['original_image_sha256'],'staged_image_sha256':r['staged_image_sha256']}
report={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,'images':images,
    'selected_cpu_api_execution_verified':True,'original_vdsp_float_cases':306,
    'scope':'Original vDSP public dispatch and original CPU resolver, float strides/lengths and double vector addition; BNNS graph option construction/get/set/isolation/destruction; vImage padded-row byte/float conversions. Foundation is loaded. No inference, graph compilation, broad numerical API, GPU or full Accelerate compatibility assertion.',
    'full_compatibility':False}
Path('artifacts/native-accelerate-cpu-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Original selected Accelerate CPU APIs passed actual resolver, numerical vector, graph option and image roundtrip checks.'
