#!/usr/bin/env python3
"""Exercise original CoreFoundation signatures and NSInvocation with source objc4."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
build = json.loads((root / 'artifacts/objc-source-build.json').read_text())
assert digest(build['library']) == build['library_sha256']
profile = json.loads((root / 'artifacts/uniform-type-identifiers-native-xcode-source-objc-support-fixture.json').read_text())
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-fblocks', '-c',
    str(root / 'fixtures/hello/objc-source-signatures.m'), '-o', str(root / 'artifacts/objc-source-signatures.o')], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guestroot), '-F', str(guestroot / 'System/Library/Frameworks'),
    '-framework', 'Foundation', '-framework', 'CoreFoundation', '-lobjc', '-lSystem',
    str(root / 'artifacts/objc-source-signatures.o'), '-o', str(root / 'artifacts/objc-source-signatures')], check=True)
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']
    environment[name] = str(root / item['path'])
command = profile['command'][:-1] + ['/Volumes/SystemRoot/workspace/artifacts/objc-source-signatures']
log = 'logs/objc-source-native-signatures.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text()
print(text[-5000:])
passed = result.returncode == 0 and 'SOURCE_OBJC_NATIVE_INVOCATION_INTEGER_DOUBLE_AND_STRUCT_RETURN_OK\n' in text
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command, build=build,
    selected_runtime=profile['source_runtime'], runtime_execution_verified=passed,
    exit_status=result.returncode, log=log, log_sha256=digest(log), diagnostic=text,
    test_source_sha256=digest('fixtures/hello/objc-source-signatures.m'), test_binary_sha256=digest('artifacts/objc-source-signatures'),
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/objc-source-signatures-execution.json').write_text(json.dumps(report, indent=2) + '\n')
assert passed
