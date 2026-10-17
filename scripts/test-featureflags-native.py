#!/usr/bin/env python3
"""Validate the lazy bridge against the actual original flag backend."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
profile = json.loads((root / 'artifacts/uniform-type-identifiers-native-xcode-support-showsdks.json').read_text())
stage = json.loads((root / 'artifacts/uti-runtime-support-stage.json').read_text())
for path, sha in stage['libraries'].items(): assert digest(path) == sha
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']
    environment[name] = str(root / item['path'])
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-c',
    str(root / 'fixtures/hello/featureflags-native.c'), '-o', str(root / 'artifacts/featureflags-native.o')], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guestroot), '-L', str(guestroot / 'usr/lib'), '-lSystem',
    str(root / 'artifacts/featureflags-native.o'), '-o', str(root / 'artifacts/featureflags-native')], check=True)
guest = '/Volumes/SystemRoot/workspace/'
command = profile['command'][:-2] + [guest + 'artifacts/featureflags-native',
    guest + 'runtime/uti-runtime-support/libraries/libSystem.B.dylib',
    guest + 'runtime/uti-runtime-support/libraries/libsystem_featureflags.dylib']
log = 'logs/featureflags-native-execute.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, env=environment, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text()
print(text[-3000:])
assert result.returncode == 0
assert 'NATIVE_FEATUREFLAGS_REAL_OWNER_MISSING_DOMAIN_BOTH_DEFAULTS_AND_FOUR_THREADS_OK\n' in text
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
    selected_runtime=profile['source_runtime'], stage=stage, exit_status=0,
    runtime_execution_verified=True, original_backend_and_bridge_owner_verified=True,
    missing_domain_two_defaults_four_threads_verified=True,
    configured_feature_decisions_verified=False, log=log, log_sha256=digest(log),
    test_files={p: digest(p) for p in ['fixtures/hello/featureflags-native.c', 'scripts/test-featureflags-native.py']},
    binary='artifacts/featureflags-native', binary_sha256=digest('artifacts/featureflags-native'),
    scope='Original backend executes actual missing-domain lookups and explicit false/true defaults. The bridge does not decide flag values. Configured features and full daemon transport remain unverified.',
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/featureflags-native-execution.json').write_text(json.dumps(report, indent=2) + '\n')
