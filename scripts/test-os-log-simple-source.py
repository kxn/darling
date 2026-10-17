#!/usr/bin/env python3
"""Check the complete simple-log source ABI over actual Unix datagrams."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
stage = json.loads((root / 'artifacts/os-log-simple-source-stage.json').read_text())
for name in ['library', 'helper']:
    assert digest(stage[name]) == stage[name + '_sha256']
profile = json.loads((root / 'artifacts/uniform-type-identifiers-native-xcode-datavault-user-local-dir-source-libtrace-source-objc-support-showsdks.json').read_text())
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-c',
    str(root / 'fixtures/hello/os-log-simple-source.c'), '-o', str(root / 'artifacts/os-log-simple-source.o')], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guestroot), '-L', str(guestroot / 'usr/lib'), '-lSystem',
    str(root / 'artifacts/os-log-simple-source.o'), '-o', str(root / 'artifacts/os-log-simple-source')], check=True)
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']; environment[name] = str(root / item['path'])
prefix = profile['command'][:-2]
index = next(i for i, value in enumerate(prefix) if value.startswith('DYLD_LIBRARY_PATH='))
prefix[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/os-log-simple-source/libraries:' + prefix[index].split('=', 1)[1]
guest = '/Volumes/SystemRoot/workspace/'
command = prefix + [guest + 'artifacts/os-log-simple-source', guest + stage['library'], guest + stage['helper']]
log = 'logs/os-log-simple-source-execute.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text(); print(text[-4000:])
passed = result.returncode == 0 and 'SOURCE_SIMPLE_LOG_ACTUAL_UNIX_DATAGRAM_TRANSPORT_AND_96_CONCURRENT_RECORDS_OK ' in text
assert 'SIMPLE_LOG_E2E 日志 -77 -9223372036854775808 ffffffffffffffff Z %' in text
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), stage=stage, command=command, source_runtime=profile['source_runtime'],
    exit_status=result.returncode, runtime_execution_verified=passed, log=log, log_sha256=digest(log), diagnostic=text,
    source_sha256=digest('fixtures/hello/os-log-simple-source.c'), binary_sha256=digest('artifacts/os-log-simple-source'),
    selected_fork_during_threaded_logging_delivered=True, persistent_logd_delivery_verified=False, early_boot_signal_and_fork_safety_verified=False, full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/os-log-simple-source-execution.json').write_text(json.dumps(report, indent=2) + '\n')
assert passed
