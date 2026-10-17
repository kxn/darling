#!/usr/bin/env bash
# Requires the existing base setup and pinned full Intel reference cache.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/prepare-capstone.py
for target in symptoms native-trace; do
    python3 scripts/rebuild-c-cache-image.py --target "$target" --modern-adapter --lazy-functions \
        > "logs/rebuild-$target-experimental.log" 2>&1
done
mkdir -p runtime/metrics-native-stage
cp runtime/rebuilt-native-trace/libsystem_trace.dylib runtime/metrics-native-stage/libDarlingMetrics.dylib
cp runtime/rebuilt-symptoms/libsystem_symptoms.dylib runtime/metrics-native-stage/libsystem_symptoms.dylib
python3 scripts/rebuild-c-cache-image.py --target swift-os --modern-adapter --lazy-functions \
    --experimental-swift --repair-swift-relative > logs/rebuild-swift-os-experimental.log 2>&1
llvm-nm-19 --extern-only --defined-only runtime/rebuilt-swift-os/libswiftos.dylib > logs/rebuilt-swift-os-exports.log
llvm-nm-19 --extern-only --defined-only runtime/metrics-native-stage/libDarlingMetrics.dylib > logs/native-metrics-exports.log
scripts/test-metric-dimensions.sh
scripts/test-swift-os.sh
python3 - <<'PY'
from pathlib import Path
import shutil,subprocess
old=Path('runtime/rootfs/usr/libexec/darling/usr/lib/swift/libswiftos.dylib')
new=Path('runtime/rebuilt-swift-os/libswiftos.dylib')
def exports(path):return {line.split()[-1] for line in subprocess.check_output([
    'llvm-nm-19','--extern-only','--defined-only',str(path)],text=True).splitlines() if line.split()}
missing={name for name in exports(old)-exports(new) if not name.startswith('$ld$')}
if missing:raise ValueError('New Swift os omits old runtime exports: '+str(sorted(missing)))
prefix=Path('runtime/state/prefix')
for source,destination in [(new,prefix/'usr/lib/swift/libswiftos.dylib'),
    (Path('runtime/metrics-native-stage/libDarlingMetrics.dylib'),prefix/'usr/lib/libDarlingMetrics.dylib'),
    (Path('runtime/metrics-native-stage/libsystem_symptoms.dylib'),prefix/'usr/lib/system/libsystem_symptoms.dylib')]:
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
PY
METRICS_LIBRARY_PATH= scripts/test-metric-dimensions.sh /usr/lib/libDarlingMetrics.dylib
cp logs/metric-dimensions-execute.log logs/metric-dimensions-installed-execute.log
SWIFT_OS_LIBRARY_PATH= scripts/test-swift-os.sh
cp logs/swift-os-client-execute.log logs/swift-os-installed-execute.log
python3 - <<'PY'
from pathlib import Path
import json
scopes={
    'swift-os':('swift-os',True,['original SDK client','Logger construction and enabled query',
        'integer/string interpolation arguments really evaluated','type reflection',
        'OSLogType Hashable/Equatable through Set','generic unfair-lock state mutation',
        'array state and ARC destruction of two objects','installed path without loader overrides'],
        'Only listed Swift os APIs tested. Unified-log delivery, metrics reporting and full Swift metadata compatibility remain unverified.'),
    'native-trace':('native-metrics',True,['four original metric object classes registered',
        'two independent dimensions objects','add dimensions and reject capacity overflow',
        'release objects and original labels','installed path without loader overrides'],
        'Original metrics code in a separate library. Legacy logging/activity classes and their +load routines are excluded to preserve Darling logging. Counter operations and telemetry delivery unverified.'),
    'symptoms':('symptoms',False,['loaded as a real dependency of the tested metrics library'],
        'Load verified only. Symptom construction, daemon communication and delivery unverified.'),
}
for target,(report_name,executed,tests,scope) in scopes.items():
    report=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text())
    for key in ('patches','lazy_binding_slots'):report.pop(key,None)
    if 'code_analysis' in report:
        report['code_analysis']['tail_tables']=len(report['code_analysis']['tail_tables'])
    if 'swift_metadata' in report:
        report['swift_metadata']['relative_references_restored']=len(report['swift_metadata'].pop('patches'))
        report['swift_metadata']['selected_api_execution_verified']=True
    report.update({'installed':True,'load_verified':True,'execution_verified':executed,
        'tests':tests,'scope':scope,'full_compatibility':False})
    Path('artifacts/'+report_name+'-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Installed tested original Swift os and isolated metrics object support; full logging/metrics service compatibility is not claimed.'
