#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
stage=runtime/build-softlinking/Frameworks/SoftLinking.framework
mkdir -p "$stage/Versions/A" runtime/build-softlinking/lib
workspace=/Volumes/SystemRoot/workspace
toolchain=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain
sdk=/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib -O2 \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/scripts/softlinking-compat.c" \
    -Wl,-install_name,/System/Library/PrivateFrameworks/SoftLinking.framework/Versions/A/SoftLinking \
    -Wl,-compatibility_version,1.0 -Wl,-current_version,1.0 \
    -o "$workspace/$stage/Versions/A/SoftLinking" > logs/build-softlinking.log 2>&1
ln -sfn A "$stage/Versions/Current"
ln -sfn Versions/Current/SoftLinking "$stage/SoftLinking"
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" -dynamiclib \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/softlinking-probe-library.c" \
    -Wl,-install_name,@rpath/Probe.dylib -o "$workspace/runtime/build-softlinking/lib/Probe.dylib" \
    > logs/softlinking-probe-library-build.log 2>&1
timeout 45 bin/darling shell "$toolchain/usr/bin/clang" \
    -target x86_64-apple-macos14.0 -isysroot "$sdk" "$workspace/fixtures/hello/softlinking.c" \
    "$workspace/$stage/Versions/A/SoftLinking" -Wl,-rpath,"$workspace/runtime/build-softlinking/lib" \
    -o "$workspace/artifacts/softlinking-abi-smoke" > logs/softlinking-client-compile.log 2>&1
timeout 30 bin/darling shell /usr/bin/env DYLD_FRAMEWORK_PATH="$workspace/runtime/build-softlinking/Frameworks" \
    "$workspace/artifacts/softlinking-abi-smoke" > logs/softlinking-client-execute.log 2>&1
rg -q '^SOFTLINKING_FALLBACK_ERRORS_CALLER_RPATH_OK$' logs/softlinking-client-execute.log
python3 - <<'PY'
from pathlib import Path
import hashlib, json, plistlib, shutil
source=Path('runtime/build-softlinking/Frameworks/SoftLinking.framework/Versions/A/SoftLinking')
root=Path('runtime/state/prefix/System/Library/PrivateFrameworks/SoftLinking.framework')
(root/'Versions/A/Resources').mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,root/'Versions/A/SoftLinking')
for name,target in [('Versions/Current','A'),('SoftLinking','Versions/Current/SoftLinking'),('Resources','Versions/Current/Resources')]:
    link=root/name
    if not link.exists() and not link.is_symlink():link.symlink_to(target)
(root/'Versions/A/Resources/Info.plist').write_bytes(plistlib.dumps({
    'CFBundleExecutable':'SoftLinking','CFBundleIdentifier':'com.apple.SoftLinking',
    'CFBundlePackageType':'FMWK','LinuxcodeImplementation':'Path-list loader implemented using Darling dlopen_from'}))
Path('artifacts/softlinking-compat.json').write_text(json.dumps({
    'library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'implemented':['_sl_dlopen','_sl_dlopen_audited'],
    'tests':['fallback path loads real library','combined dlerror messages','caller rpath preserved'],
    'provenance':'Original x86_64 SoftLinking disassembly, logs/softlinking-disassembly.log'
},indent=2)+'\n')
PY
echo 'Installed tested SoftLinking path-list loader with actual dlopen, errors and caller rpath support.'
