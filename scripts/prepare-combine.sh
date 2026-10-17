#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
revision=1c6f02c7ed8140c0ba7a783aaddb6e0685a0037b
if [[ ! -d vendor/OpenCombine/.git ]]; then
    git init -q vendor/OpenCombine
    git -C vendor/OpenCombine remote add origin https://github.com/OpenCombine/OpenCombine.git
    git -C vendor/OpenCombine fetch --depth 1 origin "$revision"
    git -C vendor/OpenCombine checkout --detach FETCH_HEAD
fi
test "$(git -C vendor/OpenCombine rev-parse HEAD)" = "$revision"
python3 scripts/build-combine-core.py > logs/build-combine-core.log 2>&1
scripts/link-combine.sh > logs/link-combine.log 2>&1
scripts/test-combine.sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, plistlib, re, shutil, subprocess
source=Path('runtime/build-combine/Combine')
exports={x.split()[-1] for x in subprocess.check_output(
    ['llvm-nm-19','--defined-only','--extern-only',str(source)],text=True).splitlines() if x.split()}
consumer=Path('runtime/state/prefix/Applications/Xcode.app/Contents/SharedFrameworks/DVTFoundation.framework/Versions/A/DVTFoundation')
bindings=subprocess.check_output(['llvm-objdump-19','--macho','--chained-fixups',str(consumer)],text=True)
required=sorted({re.search(r'name_offset = \d+ \(([^\n]+)\)',group).group(1)
    for group in bindings.split('dyld chained import[')[1:]
    if re.search(r'lib_ordinal = \d+ \(Combine\)',group)})
if not required: raise SystemExit('No Combine imports found in original DVTFoundation')
Path('artifacts/dvtfoundation-combine-imports.txt').write_text('\n'.join(required)+'\n')
missing=set(required)-exports
if missing: raise SystemExit('Missing DVTFoundation Combine exports: '+repr(missing))
root=Path('runtime/state/prefix/System/Library/Frameworks/Combine.framework')
(root/'Versions/A/Resources').mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,root/'Versions/A/Combine')
(root/'Versions/A/Combine').chmod(0o755)
for name,target in [('Versions/Current','A'),('Combine','Versions/Current/Combine'),('Resources','Versions/Current/Resources')]:
    link=root/name
    if not link.exists() and not link.is_symlink():link.symlink_to(target)
(root/'Versions/A/Resources/Info.plist').write_bytes(plistlib.dumps({
    'CFBundleExecutable':'Combine','CFBundleIdentifier':'com.apple.Combine',
    'CFBundleName':'Combine','CFBundlePackageType':'FMWK',
    'LinuxcodeImplementation':'OpenCombine core, ABI adapted for Darling'}))
Path('artifacts/combine-compat.json').write_text(json.dumps({
    'source_revision':'1c6f02c7ed8140c0ba7a783aaddb6e0685a0037b',
    'framework_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'dvtfoundation_required_exports':len(required),'missing_required_exports':[],
    'original_sdk_client_test':'passed',
    'semantic_tests':['map','catch','deferred Future','backpressure','cancellation','type erasure'],
    'scope':'OpenCombine core. Foundation/Dispatch scheduler adapters and KVO publishers are not implemented.'
},indent=2)+'\n')
PY
echo 'Installed tested OpenCombine core framework into the isolated Darling prefix.'
