#!/usr/bin/env bash
# Requires the pinned full-system reference cache and extracted resources.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
for target in feature-flags core-emoji; do
    options=()
    if [[ $target == core-emoji ]]; then options+=(--lazy-functions); fi
    python3 scripts/rebuild-c-cache-image.py --target "$target" --modern-adapter "${options[@]}" \
        > "logs/rebuild-$target.log" 2>&1
done
python3 scripts/finalize-reference-resources.py > logs/finalize-reference-resources.log 2>&1
python3 - <<'PY'
from pathlib import Path
import shutil
source=Path('runtime/fullsystem/framework-resources/System/Library/PrivateFrameworks/CoreEmoji.framework/Versions/A/Resources')
target=Path('runtime/state/prefix/System/Library/PrivateFrameworks/CoreEmoji.framework')
shutil.copytree(source,target/'Versions/A/Resources',dirs_exist_ok=True)
for name,destination in [('Versions/Current','A'),('Resources','Versions/Current/Resources')]:
    link=target/name
    if not link.exists() and not link.is_symlink():link.symlink_to(destination)
shutil.copyfile('runtime/rebuilt-feature-flags/libsystem_featureflags.dylib','runtime/rebuilt-der/libsystem_featureflags.dylib')
PY
scripts/test-feature-flags.sh
scripts/test-core-emoji.sh
python3 - <<'PY'
from pathlib import Path
import shutil
prefix=Path('runtime/state/prefix')
destination=prefix/'usr/lib/system/libsystem_featureflags.dylib'
destination.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile('runtime/rebuilt-feature-flags/libsystem_featureflags.dylib',destination)
root=prefix/'System/Library/PrivateFrameworks/CoreEmoji.framework'
shutil.copyfile('runtime/rebuilt-core-emoji/CoreEmoji',root/'Versions/A/CoreEmoji')
link=root/'CoreEmoji'
if not link.exists() and not link.is_symlink():link.symlink_to('Versions/Current/CoreEmoji')
PY
FEATURE_FLAGS_LIBRARY_PATH= scripts/test-feature-flags.sh /usr/lib/system/libsystem_featureflags.dylib
cp logs/feature-flags-execute.log logs/feature-flags-installed-execute.log
CORE_EMOJI_LIBRARY_PATH= scripts/test-core-emoji.sh /System/Library/PrivateFrameworks/CoreEmoji.framework/Versions/A/CoreEmoji
cp logs/core-emoji-client-execute.log logs/core-emoji-installed-execute.log
python3 - <<'PY'
from pathlib import Path
import hashlib,json
tests={
    'feature-flags':['original plist enabled/disabled/missing queries',
        'simple query preserves caller defaults with no shared table'],
    'core-emoji':['null and ASCII negative cases','U+1F600 positive, alone and within text',
        'original resource data with payload hard links and independent plist parsing'],
}
for target in tests:
    report=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text())
    report.pop('patches');report.pop('lazy_binding_slots')
    report.update({'installed':True,'execution_verified':True,
        'tests':tests[target]+['installed-path execution without loader overrides'],
        'adapter_sha256':hashlib.sha256(Path('runtime/state/prefix/usr/lib/libDarlingDER.dylib').read_bytes()).hexdigest(),
        'scope':'Only listed APIs and inputs tested. No featureflags shared-table daemon, full emoji coverage or full Xcode build claimed.'})
    Path('artifacts/'+target+'-compat.json').write_text(json.dumps(report,indent=2)+'\n')
PY
echo 'Installed original CoreEmoji and feature-flags libraries after semantic and installed-path tests.'
