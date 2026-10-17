#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/feature-flags.c -o artifacts/feature-flags-smoke.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem artifacts/feature-flags-smoke.o -o artifacts/feature-flags-smoke
python3 - "${1-/Volumes/SystemRoot/workspace/runtime/rebuilt-feature-flags/libsystem_featureflags.dylib}" <<'PY'
from pathlib import Path
import os, plistlib, subprocess, sys
p=Path('runtime/state/prefix/Library/Preferences/FeatureFlags/Domain/LinuxcodeCompatibilityTest.plist')
prior=p.read_bytes() if p.exists() else None
p.parent.mkdir(parents=True,exist_ok=True)
try:
    p.write_bytes(plistlib.dumps({'Enabled':{'Enabled':True},'Disabled':{'Enabled':False}}))
    with Path('logs/feature-flags-execute.log').open('wb') as log:
        subprocess.run(['timeout','-k','5','30','bin/darling','shell','/usr/bin/env',
            'DYLD_LIBRARY_PATH='+os.environ.get('FEATURE_FLAGS_LIBRARY_PATH','/Volumes/SystemRoot/workspace/runtime/rebuilt-der'),
            '/Volumes/SystemRoot/workspace/artifacts/feature-flags-smoke',sys.argv[1]],
            stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
    if prior is None:p.unlink(missing_ok=True)
    else:p.write_bytes(prior)
PY
rg -q '^ORIGINAL_FEATURE_FLAGS_PLIST_AND_DEFAULTS_OK$' logs/feature-flags-execute.log
echo 'Original feature flags read enabled/disabled/missing plist settings; simple API preserves defaults without a shared table.'
