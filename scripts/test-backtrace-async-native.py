#!/usr/bin/env python3
"""Check the libSystem entry against real ordinary and Swift async frames."""
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
guest = '/Volumes/SystemRoot/workspace/'
tc = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain'
sdkguest = '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
sdk = root / 'runtime/state/prefix' / sdkguest.lstrip('/')
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
source = root / 'fixtures/hello/backtrace-async-native.c'
logs = {}
def run(command, name, env=None):
    log = 'logs/backtrace-async-native-' + name + '.log'
    with (root / log).open('w') as stream:
        result = subprocess.run(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
    text = (root / log).read_text()
    logs[log] = digest(log)
    print(name, result.returncode, text[-1500:])
    assert result.returncode == 0, log
    return text
for mode in ['ordinary', 'bridge']:
    command = ['clang-19', '-target', 'x86_64-apple-macos15.4', '-isysroot', str(sdk),
        '-O0', '-fno-omit-frame-pointer', '-c', str(source), '-o', str(root / ('artifacts/backtrace-async-' + mode + '.o'))]
    if mode == 'bridge': command.insert(1, '-DLINUXCODE_SWIFT_STACK_CLIENT')
    subprocess.run(command, check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guestroot), '-L', str(guestroot / 'usr/lib'), '-lSystem',
    str(root / 'artifacts/backtrace-async-ordinary.o'), '-o', str(root / 'artifacts/backtrace-async-ordinary')], check=True)
prefix = profile['command'][:-2]
system = guest + 'runtime/uti-runtime-support/libraries/libSystem.B.dylib'
ordinary = run(prefix + [guest + 'artifacts/backtrace-async-ordinary', system], 'ordinary', environment)
assert 'BACKTRACE_ASYNC_ORDINARY_REAL_PC_CAPACITIES_NULL_OUTPUT_AND_FOUR_THREADS_OK\n' in ordinary
run(['timeout', '-k', '5', '60', 'bin/darling', 'shell', tc + '/usr/bin/swift-frontend', '-c',
    guest + 'fixtures/hello/thread-stack-async.swift', '-parse-as-library',
    '-import-objc-header', guest + 'fixtures/hello/thread-stack-async.h',
    '-target', 'x86_64-apple-macos15.4', '-sdk', sdkguest, '-module-name', 'NativeBacktraceAsyncProbe',
    '-o', guest + 'artifacts/backtrace-async-swift.o'], 'compile')
run(['timeout', '-k', '5', '60', 'bin/darling', 'shell', tc + '/usr/bin/clang', '-target', 'x86_64-apple-macos15.4',
    '-isysroot', sdkguest, guest + 'artifacts/backtrace-async-swift.o', guest + 'artifacts/backtrace-async-bridge.o',
    '-L/usr/lib/swift', '-L' + tc + '/usr/lib/swift/macosx', '-lswiftCore', '-lswiftSwiftOnoneSupport', '-lswift_Concurrency',
    '-Wl,-rpath,/usr/lib/swift', '-o', guest + 'artifacts/backtrace-async-swift'], 'link')
asynchronous = run(prefix + [guest + 'artifacts/backtrace-async-swift', system], 'swift', environment)
assert 'APPLE_THREAD_STACK_64_REAL_SWIFT_ASYNC_TASK_IDS_AND_BOUNDED_FRAMES_OK\n' in asynchronous
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), runtime_execution_verified=True,
    selected_runtime=profile['source_runtime'], stage=stage, command_prefix=prefix,
    ordinary_capacity_0_through_64_exact_caller_PC_null_outputs_four_threads_verified=True,
    actual_64_swift_tasks_task_ids_and_bounded_frames_verified=True,
    actual_named_libSystem_export_resolves_source_helper=True,
    logs=logs, test_files={p: digest(p) for p in ['fixtures/hello/backtrace-async-native.c',
        'fixtures/hello/thread-stack-async.swift', 'fixtures/hello/thread-stack-async.h', 'scripts/test-backtrace-async-native.py']},
    binaries={p: digest(p) for p in ['artifacts/backtrace-async-ordinary', 'artifacts/backtrace-async-swift']},
    full_xcode_build_ready=False, signing_ready=False)
(root / 'artifacts/backtrace-async-native-execution.json').write_text(json.dumps(report, indent=2) + '\n')
