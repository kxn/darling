#!/usr/bin/env bash
# Requires the base environment and the already extracted, pinned Intel cache.
# Rebuilds/stages only; never installs these experimental system frameworks.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --probe-only ) ]]; then
    echo "Usage: $0 [--probe-only]" >&2
    exit 2
fi
python3 scripts/prepare-capstone.py
python3 scripts/configure-host-cpu.py > logs/configure-host-cpu.log 2>&1
scripts/test-host-cpu.sh > logs/host-cpu-test.log 2>&1
python3 scripts/build-dyld-cache-introspection.py > logs/build-dyld-cache-introspection.log 2>&1
python3 scripts/build-libcxx-to-chars.py > logs/build-libcxx-to-chars.log 2>&1
scripts/test-foundation-xpc-exports.sh > logs/foundation-xpc-test.log 2>&1
scripts/test-xpc-send-once.sh > logs/xpc-send-once-test.log 2>&1
scripts/build-dispatch-executor-compat.sh > logs/build-dispatch-executor-compat.log 2>&1
scripts/build-metal-legacy-headless.sh > logs/build-metal-legacy-headless.log 2>&1
scripts/test-native-string-constants.sh > logs/native-string-constants-test.log 2>&1
scripts/test-constant-float-number.sh > logs/constant-float-number-test.log 2>&1
python3 scripts/build-directory-hint-native.py > logs/build-directory-hint-native.log 2>&1
scripts/build-url-appending-compat.sh > logs/build-url-appending-compat.log 2>&1
python3 scripts/build-foundation-file-errors.py > logs/build-foundation-file-errors.log 2>&1
python3 scripts/stage-foundation-additions.py > logs/stage-foundation-additions.log 2>&1
scripts/test-person-name-compat.sh > logs/person-name-compat-test.log 2>&1
scripts/test-person-name-formatter.sh > logs/person-name-formatter-test.log 2>&1
scripts/test-mach-port-compat.sh > logs/mach-port-compat-test.log 2>&1
if [[ ${1-} != --probe-only ]]; then
    target_list=$(python3 - <<'PY'
from pathlib import Path
import json,re
for entry in json.loads(Path('config/coreml-experiment.json').read_text())['targets']:
    if not re.fullmatch('[a-z0-9-]+',entry['target']):raise ValueError('Invalid experiment target')
    print(entry['target'],'swift' if entry.get('swift_relative') else
        ('analyze' if entry.get('analyze_code') else 'objc'))
PY
    )
    while read -r target mode; do
        extra=()
        if [[ $mode == swift ]]; then extra=(--experimental-swift --repair-swift-relative); fi
        if [[ $mode == analyze ]]; then extra=(--analyze-code); fi
        python3 scripts/rebuild-c-cache-image.py --target "$target" --modern-adapter --lazy-functions \
            "${extra[@]}" > "logs/rebuild-$target-experimental.log" 2>&1
    done <<< "$target_list"
fi
python3 - <<'PY'
from pathlib import Path
import hashlib,json,shutil,subprocess
def publish(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_name(destination.name+'.pending')
    shutil.copyfile(source,temporary);shutil.copymode(source,temporary);temporary.replace(destination)
pins=json.loads(Path('config/cache-image-pins.json').read_text())
for entry in json.loads(Path('config/coreml-experiment.json').read_text())['targets']:
    target=entry['target'];name=Path(pins[target]['path']).name
    source=Path('runtime/rebuilt-'+target)/name
    report=json.loads((source.parent/'reconstruction.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=report['staged_image_sha256']:
        raise ValueError('Staged file differs from reconstruction report: '+target)
    with Path('logs/'+target+'-rebuilt-symbols.log').open('w') as log:
        subprocess.run(['llvm-nm-19','--defined-only',str(source)],stdout=log,check=True)
    if name.endswith('.dylib'):
        destination=Path('runtime/native-library-stage')/name
        publish(source,destination)
        continue
    bundle=Path('runtime/native-framework-stage')/(name+'.framework')
    destination=bundle/'Versions/A'/name
    publish(source,destination)
    for link,value in [(bundle/'Versions/Current','A'),(bundle/name,'Versions/Current/'+name)]:
        if link.is_symlink() and link.readlink()==Path(value):continue
        if link.exists() and not link.is_symlink():raise ValueError('Refusing to replace a non-symlink: '+str(link))
        temporary=link.with_name(link.name+'.pending')
        if temporary.is_symlink():temporary.unlink()
        if temporary.exists():raise ValueError('Unexpected pending link path: '+str(temporary))
        temporary.symlink_to(value);temporary.replace(link)
PY
python3 scripts/test-cache-code-analysis.py > logs/cache-code-analysis-test.log 2>&1
scripts/test-collections-metadata.sh > logs/collections-metadata-test.log 2>&1
scripts/test-apfs-fletcher.sh > logs/apfs-fletcher-test.log 2>&1
scripts/test-dispatch-executor-compat.sh > logs/dispatch-executor-test.log 2>&1
scripts/test-swift-dispatch.sh > logs/swift-dispatch-test.log 2>&1
scripts/test-applekeystore-strings.sh > logs/applekeystore-strings-test.log 2>&1
scripts/test-metal-descriptor.sh > logs/metal-descriptor-test.log 2>&1
scripts/test-metal-legacy-headless.sh > logs/metal-legacy-headless-test.log 2>&1
scripts/test-metadata-thread-local.sh > logs/metadata-thread-local-test.log 2>&1
scripts/test-directory-hint-native.sh > logs/directory-hint-native-test.log 2>&1
scripts/test-url-appending-compat.sh > logs/url-appending-compat-test.log 2>&1
scripts/test-libcxx-to-chars.sh > logs/libcxx-to-chars-test.log 2>&1
scripts/test-dyld-cache-introspection.sh > logs/dyld-cache-introspection-test.log 2>&1
scripts/test-dyld-process-snapshot.sh > logs/dyld-process-snapshot-test.log 2>&1
scripts/test-macho-architecture.sh > logs/macho-architecture-test.log 2>&1
scripts/test-system-xpc-empty.sh > logs/system-xpc-empty-test.log 2>&1
scripts/test-foundation-file-errors.sh > logs/foundation-file-errors-test.log 2>&1
scripts/test-native-accelerate-cpu.sh > logs/native-accelerate-cpu-test.log 2>&1
scripts/test-native-swift-metadata.sh > logs/native-swift-metadata-test.log 2>&1
python3 scripts/inventory-runtime-dependencies.py --native-stage --library-path /usr/lib/swift \
    --seed /System/Library/Frameworks/CoreML.framework/Versions/A/CoreML \
    > logs/coreml-dependency-inventory.log 2>&1
python3 scripts/audit-runtime-symbols.py > logs/native-symbol-audit.log 2>&1
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c scripts/library-probe.c -o runtime/tools/library-probe.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem runtime/tools/library-probe.o -o runtime/tools/library-probe
probe_status=0
timeout -k 5 30 bin/darling shell /usr/bin/env \
    DYLD_FRAMEWORK_PATH=/Volumes/SystemRoot/workspace/runtime/native-framework-stage \
    DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/native-library-stage:/Volumes/SystemRoot/workspace/runtime/rebuilt-der:/usr/lib/swift \
    /Volumes/SystemRoot/workspace/runtime/tools/library-probe --lazy \
    /Volumes/SystemRoot/workspace/runtime/native-framework-stage/CoreML.framework/CoreML \
    > logs/coreml-library-load.log 2>&1 || probe_status=$?
api_status=-1
if [[ $probe_status == 0 ]]; then
    api_status=0
    scripts/test-coreml-feature-values.sh > logs/coreml-feature-values-test.log 2>&1 || api_status=$?
fi
python3 - "$probe_status" "$api_status" <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import json,sys
reports={}
for entry in json.loads(Path('config/coreml-experiment.json').read_text())['targets']:
    target=entry['target']
    r=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text())
    reports[target]={key:r[key] for key in ('original_image_sha256','staged_image_sha256','target','reference_set','exports','bindings')}
    reports[target].update({'installed':False,'execution_verified':False,
        'llvm_symbol_parser_verified':True,'objc_classes':len(r.get('objc_metadata',{}).get('classes',[]))})
    if 'swift_metadata' in r:
        reports[target]['swift_relative_references_restored']=len(r['swift_metadata']['patches'])
        reports[target]['verified_tail_tables']=len(r['code_analysis']['tail_tables'])
    for image,proof_file,field in [
        ('apfs','artifacts/apfs-fletcher-compat.json','checksum_execution_verified'),
        ('applekeystore','artifacts/applekeystore-string-compat.json','literal_values_verified'),
        ('metal','artifacts/metal-descriptor-compat.json','selected_descriptor_api_execution_verified'),
        ('swift-dispatch','artifacts/swift-dispatch-compat.json','selected_api_execution_verified')]:
        if target!=image:continue
        proof=json.loads(Path(proof_file).read_text())
        if proof['staged_image_sha256']!=r['staged_image_sha256']:
            raise ValueError('Selected API validation belongs to another image build: '+target)
        reports[target][field]=proof[field]
        reports[target]['selected_api_report']=proof_file
    if target=='collectionsinternal':
        proof=json.loads(Path('artifacts/collections-metadata-compat.json').read_text())
        if proof['staged_image_sha256']!=r['staged_image_sha256']:
            raise ValueError('Collections metadata validation belongs to another build')
        reports[target]['selected_metadata_api_execution_verified']=proof['selected_metadata_api_execution_verified']
        reports[target]['selected_api_report']='artifacts/collections-metadata-compat.json'
    if target in ('accelerate','veclib','vimage','bnns','vdsp'):
        proof=json.loads(Path('artifacts/native-accelerate-cpu-compat.json').read_text())
        if proof['images'][target]['staged_image_sha256']!=r['staged_image_sha256']:
            raise ValueError('Accelerate CPU validation belongs to another image build: '+target)
        reports[target]['selected_cpu_api_execution_verified']=proof['selected_cpu_api_execution_verified']
        reports[target]['selected_api_report']='artifacts/native-accelerate-cpu-compat.json'
    if target in ('swift-metal','ml-model-asset','odie'):
        proof=json.loads(Path('artifacts/native-swift-metadata-compat.json').read_text())['images'][target]
        if proof['staged_image_sha256']!=r['staged_image_sha256']:
            raise ValueError('Swift metadata validation belongs to another build: '+target)
        reports[target]['selected_metadata_api_execution_verified']=proof['selected_metadata_api_execution_verified']
        reports[target]['selected_api_report']='artifacts/native-swift-metadata-compat.json'
log=Path('logs/coreml-library-load.log').read_text(errors='replace')
status=int(sys.argv[1]);loaded=status==0 and 'Library loaded (RTLD_LAZY)' in log
api_status=int(sys.argv[2]);api_verified=loaded and api_status==0 and \
    'ORIGINAL_COREML_INT64_LIMITS_DOUBLE_STRING_UNDEFINED_EQUALITY_COPY_OK' in \
    Path('logs/coreml-feature-values-execute.log').read_text(errors='replace')
report={'checked_at':datetime.now(timezone.utc).isoformat(),'images':reports,
    'load_probe_exit_code':status,'coreml_load_verified':loaded,'load_diagnostic':log,
    'api_probe_exit_code':api_status,'api_execution_verified':api_verified,'full_compatibility':False,
    'static_dependencies_report':'artifacts/native-dependency-inventory.json',
    'static_symbols_report':'artifacts/native-symbol-audit.json',
    'selected_compatibility_helper_reports':['artifacts/native-string-constants-compat.json',
        'artifacts/constant-float-compat.json','artifacts/person-name-compat.json',
        'artifacts/person-name-formatter-compat.json','artifacts/mach-port-compat.json',
        'artifacts/foundation-xpc-exports.json','artifacts/xpc-send-once-compat.json',
        'artifacts/host-cpu-compat.json','artifacts/native-accelerate-cpu-compat.json',
        'artifacts/native-swift-metadata-compat.json','artifacts/metal-legacy-headless-compat.json',
        'artifacts/metadata-thread-local-compat.json','artifacts/foundation-staged-additions.json',
        'artifacts/directory-hint-native.json','artifacts/url-appending-compat.json',
        'artifacts/libcxx-to-chars.json','artifacts/dyld-cache-introspection.json',
        'artifacts/foundation-file-errors.json'],
    'scope':'Project-local experiment only. Static reconstruction and table checks do not establish framework API or Xcode build compatibility.'}
Path('artifacts/coreml-experiment.json').write_text(json.dumps(report,indent=2)+'\n')
print('CoreML experiment recorded; load verified: '+str(loaded))
PY
if [[ $probe_status == 0 && $api_status != 0 ]]; then exit "$api_status"; fi
exit "$probe_status"
