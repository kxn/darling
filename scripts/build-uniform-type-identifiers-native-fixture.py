#!/usr/bin/env python3
"""Compile the UTI behavioral fixture with the genuine installed Apple tools."""
from pathlib import Path
import hashlib, json, subprocess

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
guest = '/Volumes/SystemRoot/workspace/'
tc = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain'
sdk = '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
prefix = ['timeout', '-k', '5', '60', 'bin/darling', 'shell']
commands = [prefix + [tc + '/usr/bin/swift-frontend', '-c', guest + 'fixtures/hello/uniform-type-identifiers-native.swift',
    '-target', 'x86_64-apple-macos15.4', '-sdk', sdk, '-module-name', 'NativeUTIProbe', '-o', guest + 'artifacts/uniform-type-identifiers-native.o'],
    prefix + [tc + '/usr/bin/clang', '-target', 'x86_64-apple-macos15.4', '-isysroot', sdk,
    guest + 'artifacts/uniform-type-identifiers-native.o', '-L/usr/lib/swift', '-L' + tc + '/usr/lib/swift/macosx',
    '-lswiftCore', '-lswiftSwiftOnoneSupport', '-lobjc', '-framework', 'Foundation', '-framework', 'UniformTypeIdentifiers',
    '-Wl,-rpath,/usr/lib/swift', '-o', guest + 'artifacts/uniform-type-identifiers-native']]
logs = {}
for mode, command in zip(['compile', 'link'], commands):
    log = 'logs/uniform-type-identifiers-native-' + mode + '.log'
    with (root / log).open('w') as stream:
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    assert result.returncode == 0, log
    logs[log] = digest(log)
report = dict(compiled=True, runtime_execution_verified=False, commands=commands, logs=logs,
    source='fixtures/hello/uniform-type-identifiers-native.swift', source_sha256=digest('fixtures/hello/uniform-type-identifiers-native.swift'),
    binary='artifacts/uniform-type-identifiers-native', binary_sha256=digest('artifacts/uniform-type-identifiers-native'))
(root / 'artifacts/uniform-type-identifiers-native-fixture-build.json').write_text(json.dumps(report, indent=2) + '\n')
print('Compiled and linked original SDK UTI fixture; functional execution remains unverified')
