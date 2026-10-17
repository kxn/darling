#!/usr/bin/env python3
"""Exercise compiler-produced os_log records with native Foundation/source objc4."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, runpy, subprocess
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--enablement',action='store_true');parser.add_argument('--hooks',action='store_true');args=parser.parse_args()
stem='libtrace-hooks' if args.hooks else 'libtrace-enablement' if args.enablement else 'libtrace-source'
folder='libtrace-hooks-source' if args.hooks else 'libtrace-enablement-source' if args.enablement else 'libtrace-source'
build = json.loads((root / ('artifacts/'+folder+'-build.json')).read_text())
assert digest(build['library']) == build['library_sha256']
profile = json.loads((root / 'artifacts/uniform-type-identifiers-native-xcode-source-objc-support-showsdks.json').read_text())
if args.hooks:profile.update(runpy.run_path(str(root/'scripts/log-hooks-profile.py'))['profile']())
elif args.enablement:profile.update(runpy.run_path(str(root/'scripts/log-enablement-profile.py'))['profile']())
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-fblocks', '-c',
    *(['-DEXPECTED_TRACE_PROVIDER="/runtime/'+folder+'/"'] if args.enablement or args.hooks else []),
    str(root / 'fixtures/hello/libtrace-source.m'), '-o', str(root / ('artifacts/'+stem+'.o'))], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11', '-syslibroot', str(guestroot),
    '-F', str(guestroot / 'System/Library/Frameworks'), '-framework', 'Foundation', '-lobjc', '-lSystem',
    str(root / ('artifacts/'+stem+'.o')), '-o', str(root / ('artifacts/'+stem))], check=True)
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']; environment[name] = str(root / item['path'])
prefix = profile['command'][:-2]
prefix.insert(prefix.index('/usr/bin/env') + 1, 'DARLING_OS_LOG_STDERR=1')
index = next(i for i, value in enumerate(prefix) if value.startswith('DYLD_LIBRARY_PATH='))
if not(args.enablement or args.hooks):prefix[index] = 'DYLD_LIBRARY_PATH=/Volumes/SystemRoot/workspace/runtime/libtrace-source/libraries:' + prefix[index].split('=', 1)[1]
command = prefix + ['/Volumes/SystemRoot/workspace/artifacts/'+stem, '/Volumes/SystemRoot/workspace/' + build['library']]
log = 'logs/'+stem+'-execute.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text(); print(text[-4500:])
passed = result.returncode == 0 and 'SOURCE_LIBTRACE_ACTUAL_LOG_OBJECT_ENCODED_DECODER_AND_ASL_CALL_RETURNED_OK\n' in text and 'LIBTRACE_ASL_E2E -77' in text
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), build=build, source_runtime=profile['source_runtime'],
    source_objc=profile['source_objc'], command=command, exit_status=result.returncode,
    log=log, log_sha256=digest(log), diagnostic=text, runtime_execution_verified=passed,
    test_source_sha256=digest('fixtures/hello/libtrace-source.m'), test_binary_sha256=digest('artifacts/'+stem),
    persistent_unified_log_delivery_verified=False, full_xcode_build_ready=False, signing_ready=False)
report['actual_ASL_stderr_record_text_verified'] = 'LIBTRACE_ASL_E2E -77' in text
(root / ('artifacts/'+stem+'-execution.json')).write_text(json.dumps(report, indent=2) + '\n')
assert passed
