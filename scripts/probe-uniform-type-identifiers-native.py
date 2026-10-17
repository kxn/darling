#!/usr/bin/env python3
"""Run genuine Xcode with the paired UTI experiment; preserve older profiles."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess

root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', action='store_true')
parser.add_argument('--runtime-support', action='store_true')
parser.add_argument('--uti-fixture', action='store_true')
parser.add_argument('--source-objc', action='store_true')
parser.add_argument('--timeout', type=int, default=60)
parser.add_argument('--source-libtrace', action='store_true')
parser.add_argument('--user-local-dir-export', action='store_true')
parser.add_argument('--rootless-datavault-export', action='store_true')
parser.add_argument('--source-simple-log', action='store_true')
parser.add_argument('--typed-malloc', action='store_true')
parser.add_argument('--nounlink-export', action='store_true')
parser.add_argument('--sandbox-container', action='store_true')
parser.add_argument('--native-sysdir', action='store_true')
args = parser.parse_args()
if not 5 <= args.timeout <= 600:
    parser.error('--timeout must be between 5 and 600 seconds')
if args.source_objc and not args.runtime_support:
    parser.error('--source-objc requires --runtime-support')
if args.source_libtrace and not args.source_objc:
    parser.error('--source-libtrace requires --source-objc')
if args.user_local_dir_export and not args.source_libtrace:
    parser.error('--user-local-dir-export requires --source-libtrace')
if args.rootless_datavault_export and not args.user_local_dir_export:
    parser.error('--rootless-datavault-export requires --user-local-dir-export')
if args.source_simple_log and not args.rootless_datavault_export:
    parser.error('--source-simple-log requires --rootless-datavault-export')
if args.typed_malloc and not args.source_simple_log:
    parser.error('--typed-malloc requires --source-simple-log')
if args.nounlink_export and not args.typed_malloc:
    parser.error('--nounlink-export requires --typed-malloc')
if args.sandbox_container and not args.nounlink_export:
    parser.error('--sandbox-container requires --nounlink-export')
if args.native_sysdir and not args.sandbox_container:
    parser.error('--native-sysdir requires --sandbox-container')
if args.version and args.uti_fixture:
    parser.error('Choose version or UTI fixture')
base = json.loads((root / 'artifacts/pthread-yield-export-xcode-probe.json').read_text())
stage = json.loads((root / 'artifacts/uniform-type-identifiers-native-stage.json').read_text())
for image in stage['images'].values():
    assert digest(image['path']) == image['sha256']
    assert digest(image['reconstruction_report']) == image['reconstruction_report_sha256']
for path, value in stage['resources'].items():
    assert digest(path) == value
environment = os.environ.copy()
for name, item in base['source_runtime'].items():
    assert digest(item['path']) == item['sha256']
    environment[name] = str(root / item['path'])
command = list(base['command'])
assert command[:4] == ['timeout', '-k', '5', '60']
command[3] = str(args.timeout)
guest = '/Volumes/SystemRoot/workspace/runtime/uniform-type-identifiers-native/'
for variable, directory in [('DYLD_FRAMEWORK_PATH', 'frameworks'), ('DYLD_LIBRARY_PATH', 'libraries')]:
    index = next(i for i, value in enumerate(command) if value.startswith(variable + '='))
    command[index] = variable + '=' + guest + directory + ':' + command[index].split('=', 1)[1]
support = None
if args.runtime_support:
    support = json.loads((root / 'artifacts/uti-runtime-support-stage.json').read_text())
    for path, sha in support['libraries'].items():
        assert digest(path) == sha
    for path, sha in support['source_files'].items():
        assert digest(path) == sha
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/uti-runtime-support/libraries:' + command[index].split('=', 1)[1]
objc = None
if args.source_objc:
    objc = json.loads((root / 'artifacts/objc-source-build.json').read_text())
    assert not objc['missing_original_exports'] and objc['full_objc_source_build']
    assert digest(objc['library']) == objc['library_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/objc-source:' + command[index].split('=', 1)[1]
    command[command.index('OBJC_DISABLE_TAGGED_POINTERS=YES')] = 'OBJC_DISABLE_TAGGED_POINTERS=NO'
trace = None
if args.source_libtrace:
    trace = json.loads((root / 'artifacts/libtrace-source-build.json').read_text())
    tested = json.loads((root / 'artifacts/libtrace-source-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['build'] == trace
    assert digest(trace['library']) == trace['library_sha256']
    assert digest(tested['log']) == tested['log_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/libtrace-source/libraries:' + command[index].split('=', 1)[1]
user_directory = None
if args.user_local_dir_export:
    user_directory = json.loads((root / 'artifacts/user-local-dir-export-stage.json').read_text())
    tested = json.loads((root / 'artifacts/user-local-dir-export-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == user_directory
    for name in ['library', 'helper', 'original_provider', 'source']:
        assert digest(user_directory[name]) == user_directory[name + '_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/user-local-dir-export/libraries:' + command[index].split('=', 1)[1]
datavault = None
if args.rootless_datavault_export:
    datavault = json.loads((root / 'artifacts/rootless-datavault-export-stage.json').read_text())
    tested = json.loads((root / 'artifacts/rootless-datavault-export-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == datavault
    for name in ['library', 'helper', 'original_provider', 'source']:
        assert digest(datavault[name]) == datavault[name + '_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/rootless-datavault-export/libraries:' + command[index].split('=', 1)[1]
simple_log = None
if args.source_simple_log:
    simple_log = json.loads((root / 'artifacts/os-log-simple-source-stage.json').read_text())
    tested = json.loads((root / 'artifacts/os-log-simple-source-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == simple_log
    for name in ['library', 'helper']:
        assert digest(simple_log[name]) == simple_log[name + '_sha256']
    for path, value in simple_log['source_files'].items(): assert digest(path) == value
    for path, value in simple_log['compile_inputs'].items(): assert digest(path) == value
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/os-log-simple-source/libraries:' + command[index].split('=', 1)[1]
typed_malloc = None
if args.typed_malloc:
    typed_malloc = json.loads((root / 'artifacts/typed-malloc-source-stage.json').read_text())
    tested = json.loads((root / 'artifacts/typed-malloc-source-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == typed_malloc
    for name in ['library', 'helper', 'source']:
        assert digest(typed_malloc[name]) == typed_malloc[name + '_sha256']
    assert typed_malloc['base_sha256'] == simple_log['library_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/typed-malloc-source/libraries:' + command[index].split('=', 1)[1]
nounlink = None
if args.nounlink_export:
    nounlink = json.loads((root / 'artifacts/rootless-nounlink-export-stage.json').read_text())
    tested = json.loads((root / 'artifacts/rootless-nounlink-export-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == nounlink
    for name in ['library', 'helper', 'source', 'original_provider']:
        assert digest(nounlink[name]) == nounlink[name + '_sha256']
    assert nounlink['base_sha256'] == typed_malloc['library_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/rootless-nounlink-export/libraries:' + command[index].split('=', 1)[1]
container = None
if args.sandbox_container:
    container = json.loads((root / 'artifacts/sandbox-container-source-stage.json').read_text())
    tested = json.loads((root / 'artifacts/sandbox-container-source-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == container
    for name in ['library', 'helper', 'source', 'original_provider']:
        assert digest(container[name]) == container[name + '_sha256']
    assert container['base_sha256'] == nounlink['library_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/sandbox-container-source/libraries:' + command[index].split('=', 1)[1]
sysdir = None
if args.native_sysdir:
    sysdir = json.loads((root / 'artifacts/sysdir-native-export-stage.json').read_text())
    tested = json.loads((root / 'artifacts/sysdir-native-export-execution.json').read_text())
    assert tested['runtime_execution_verified'] and tested['stage'] == sysdir
    for name in ['library', 'helper', 'source', 'original_provider']:
        assert digest(sysdir[name]) == sysdir[name + '_sha256']
    assert sysdir['base_sha256'] == container['library_sha256']
    index = next(i for i, value in enumerate(command) if value.startswith('DYLD_LIBRARY_PATH='))
    command[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/sysdir-native-export/libraries:' + command[index].split('=', 1)[1]
if args.version:
    command[-1] = '-version'
if args.uti_fixture:
    fixture_build = json.loads((root / 'artifacts/uniform-type-identifiers-native-fixture-build.json').read_text())
    assert digest(fixture_build['source']) == fixture_build['source_sha256']
    assert digest(fixture_build['binary']) == fixture_build['binary_sha256']
    command[-2:] = ['/Volumes/SystemRoot/workspace/artifacts/uniform-type-identifiers-native']
suffix = ('sysdir-' if args.native_sysdir else '') + ('sandbox-container-' if args.sandbox_container else '') + ('nounlink-' if args.nounlink_export else '') + ('typed-malloc-' if args.typed_malloc else '') + ('simple-log-' if args.source_simple_log else '') + ('datavault-' if args.rootless_datavault_export else '') + ('user-local-dir-' if args.user_local_dir_export else '') + ('source-libtrace-' if args.source_libtrace else '') + ('source-objc-' if args.source_objc else '') + ('support-' if args.runtime_support else '') + ('fixture' if args.uti_fixture else 'version' if args.version else 'showsdks')
log = 'logs/uniform-type-identifiers-native-xcode-' + suffix + '.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
original = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original) == base['original_xcodebuild_sha256']
assert digest(original) == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
text = (root / log).read_text()
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), command=command,
    source_runtime=base['source_runtime'], stage=stage, exit_status=result.returncode,
    runtime_support=support,
    source_objc=objc,
    source_libtrace=trace,
    user_local_dir_export=user_directory,
    rootless_datavault_export=datavault, source_simple_log=simple_log, typed_malloc=typed_malloc, nounlink_export=nounlink, sandbox_container=container, native_sysdir=sysdir,
    original_xcodebuild_sha256=digest(original), log=log, log_sha256=digest(log), diagnostic=text,
    sdk_listing_succeeded=not args.version and not args.uti_fixture and result.returncode == 0,
    full_xcode_build_ready=False, signing_ready=False)
if args.uti_fixture:
    report['fixture_build'] = fixture_build
    report['UTI_functional_execution_verified'] = result.returncode == 0 and 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK\n' in text
(root / ('artifacts/uniform-type-identifiers-native-xcode-' + suffix + '.json')).write_text(json.dumps(report, indent=2) + '\n')
print(text[-4000:])
print('Original Xcode paired UTI profile:', result.returncode)
raise SystemExit(0 if result.returncode == 0 else 1)
