#!/usr/bin/env python3
"""Run the same real tagged-object operations against packaged and source objc4."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
build = json.loads((root / 'artifacts/objc-source-build.json').read_text())
assert not build['missing_original_exports'] and digest(build['library']) == build['library_sha256']
profile = json.loads((root / 'artifacts/uniform-type-identifiers-native-xcode-support-showsdks.json').read_text())
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk),
    '-I' + str(root / 'runtime/objc-source/include'), '-O2', '-c',
    str(root / 'fixtures/hello/objc-source-tagged.m'), '-o', str(root / 'artifacts/objc-source-tagged.o')], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guestroot), '-L', str(guestroot / 'usr/lib'), '-lobjc', '-lSystem',
    str(root / 'artifacts/objc-source-tagged.o'), '-o', str(root / 'artifacts/objc-source-tagged')], check=True)
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']
    environment[name] = str(root / item['path'])
prefix = profile['command'][:-2]
prefix[prefix.index('OBJC_DISABLE_TAGGED_POINTERS=YES')] = 'OBJC_DISABLE_TAGGED_POINTERS=NO'
results = {}
for mode in ['packaged', 'source']:
    command = list(prefix)
    if mode == 'source':
        at = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
        command[at] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/objc-source:' + command[at].split('=', 1)[1]
    command.append('/Volumes/SystemRoot/workspace/artifacts/objc-source-tagged')
    log = 'logs/objc-tagged-' + mode + '.log'
    with (root / log).open('w') as stream:
        result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
    text = (root / log).read_text()
    results[mode] = dict(command=command, exit_status=result.returncode, log=log, log_sha256=digest(log), diagnostic=text)
    print(mode, result.returncode, text[-3000:], flush=True)
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), build=build, results=results,
    source_runtime=profile['source_runtime'], test_source_sha256=digest('fixtures/hello/objc-source-tagged.m'),
    test_binary_sha256=digest('artifacts/objc-source-tagged'), runtime_execution_verified=False,
    full_xcode_build_ready=False, signing_ready=False)
passed = results['source']['exit_status'] == 0 and 'SOURCE_OBJC_TAGGED_19_BASIC_EXTENDED_BOUNDARIES_CLASS_DISPATCH_RR_WEAK_AND_HEAP_OK\n' in results['source']['diagnostic']
assert '/runtime/objc-source/libobjc.A.dylib\n' in results['source']['diagnostic'] or not passed
report['runtime_execution_verified'] = passed
(root / 'artifacts/objc-source-tagged-execution.json').write_text(json.dumps(report, indent=2) + '\n')
assert passed, 'Source objc4 tagged behavior still failed'
