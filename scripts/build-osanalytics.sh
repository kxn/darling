#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
stage=runtime/build-osanalytics/Frameworks/OSAnalytics.framework
mkdir -p "$stage/Versions/A"
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/scripts/osanalytics-compat.m" \
    -framework Foundation -Wl,-install_name,/System/Library/PrivateFrameworks/OSAnalytics.framework/Versions/A/OSAnalytics \
    -Wl,-compatibility_version,1.0 -Wl,-current_version,1.0 \
    -o "$workspace/$stage/Versions/A/OSAnalytics" > logs/build-osanalytics.log 2>&1
ln -sfn A "$stage/Versions/Current"
ln -sfn Versions/Current/OSAnalytics "$stage/OSAnalytics"
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/osanalytics.m" \
    "$workspace/$stage/Versions/A/OSAnalytics" -framework Foundation \
    -o "$workspace/artifacts/osanalytics-error-probe" > logs/osanalytics-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_FRAMEWORK_PATH="$workspace/runtime/build-osanalytics/Frameworks" \
    "$workspace/artifacts/osanalytics-error-probe" > logs/osanalytics-client-execute.log 2>&1
rg -q '^OSANALYTICS_CONSTANTS_OK_UNSUPPORTED_TRANSFORMATION_REJECTED$' logs/osanalytics-client-execute.log
python3 - <<'PY'
from pathlib import Path
import hashlib, json, plistlib, shutil
source=Path('runtime/build-osanalytics/Frameworks/OSAnalytics.framework/Versions/A/OSAnalytics')
root=Path('runtime/state/prefix/System/Library/PrivateFrameworks/OSAnalytics.framework')
(root/'Versions/A/Resources').mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,root/'Versions/A/OSAnalytics')
for name,target in [('Versions/Current','A'),('OSAnalytics','Versions/Current/OSAnalytics'),('Resources','Versions/Current/Resources')]:
    link=root/name
    if not link.exists() and not link.is_symlink():link.symlink_to(target)
(root/'Versions/A/Resources/Info.plist').write_bytes(plistlib.dumps({
    'CFBundleExecutable':'OSAnalytics','CFBundleIdentifier':'com.apple.OSAnalytics',
    'CFBundlePackageType':'FMWK','LinuxcodeImplementation':'Constants and explicit unsupported-operation error boundary only'}))
Path('artifacts/osanalytics-compat.json').write_text(json.dumps({
    'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'constant_provenance':'Apple recovery cache, inspected via scripts/inspect-dsc-constants.py',
    'implemented':'Three constant values and NSError failure contract only',
    'unsupported':['legacy crash-report transformation','crash symbolication'],
    'failure_probe':'passed; ENOTSUP NSError returned, no report manufactured',
    'full_osanalytics_compatibility':False
},indent=2)+'\n')
PY
echo 'Installed OSAnalytics constants and explicit NSError rejection boundary; report conversion remains unsupported.'
