#!/usr/bin/env python3
"""Run original Intel directory helper and client in one private managed session."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess, fcntl, plistlib, shutil
root = Path(__file__).resolve().parent.parent
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-simple-log', action='store_true')
parser.add_argument('--typed-malloc', action='store_true')
parser.add_argument('--nounlink-export', action='store_true')
parser.add_argument('--sandbox-container', action='store_true')
parser.add_argument('--native-sysdir', action='store_true')
args = parser.parse_args()
if args.typed_malloc and not args.source_simple_log: parser.error('typed malloc requires source simple log')
if args.nounlink_export and not args.typed_malloc: parser.error('nounlink export requires typed malloc')
if args.sandbox_container and not args.nounlink_export: parser.error('sandbox container requires nounlink export')
if args.native_sysdir and not args.sandbox_container: parser.error('native sysdir requires sandbox container')
suffix = ('-sysdir' if args.native_sysdir else '') + ('-sandbox-container' if args.sandbox_container else '') + ('-nounlink' if args.nounlink_export else '') + ('-typed-malloc' if args.typed_malloc else '') + ('-source-simple-log' if args.source_simple_log else '')
stage = json.loads((root / 'artifacts/rootless-datavault-export-stage.json').read_text())
for name in ['library', 'helper', 'original_provider', 'source']:
    assert digest(stage[name]) == stage[name + '_sha256']
profile = json.loads((root / ('artifacts/uniform-type-identifiers-native-xcode-' + ('sysdir-' if args.native_sysdir else '') + ('sandbox-container-' if args.sandbox_container else '') + ('nounlink-' if args.nounlink_export else '') + ('typed-malloc-' if args.typed_malloc else '') + ('simple-log-' if args.source_simple_log else '') + 'datavault-user-local-dir-source-libtrace-source-objc-support-showsdks.json')).read_text())
sdk = root / 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guestroot = root / 'runtime/rootfs/usr/libexec/darling'
subprocess.run(['clang-19', '-target', 'x86_64-apple-macos11', '-isysroot', str(sdk), '-O2', '-c',
    str(root / 'fixtures/hello/lsd-runtime-paths.c'), '-o', str(root / 'artifacts/lsd-runtime-paths.o')], check=True)
subprocess.run(['ld64.lld-19', '-arch', 'x86_64', '-platform_version', 'macos', '11', '11',
    '-syslibroot', str(guestroot), '-L', str(guestroot / 'usr/lib'), '-lSystem',
    str(root / 'artifacts/lsd-runtime-paths.o'), '-o', str(root / 'artifacts/lsd-runtime-paths')], check=True)
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']; environment[name] = str(root / item['path'])
prefix = profile['command'][:-2]
guest = '/Volumes/SystemRoot/workspace/'
recovery = root / 'runtime/recovery/macOS Base System'
source = recovery / 'usr/libexec/dirhelper'
original_plist = recovery / 'System/Library/LaunchDaemons/com.apple.bsd.dirhelper.plist'
job = plistlib.loads(original_plist.read_bytes())
assert job['ProgramArguments'] == ['/usr/libexec/dirhelper']
assert job['MachServices'] == {'com.apple.bsd.dirhelper': True}
build = root / 'runtime/native-dirhelper'; build.mkdir(exist_ok=True)
settings = {key: value for key, value in (part.split('=',1) for part in prefix if part.startswith(('DYLD_', 'OBJC_DISABLE_TAGGED_POINTERS=')))}
job['EnvironmentVariables'].update(settings)
job['EnvironmentVariables']['DARLING_OS_LOG_STDERR'] = '1'
job['ProgramArguments'][0] = guest + 'runtime/native-dirhelper/dirhelper'
daemon_log = 'logs/native-dirhelper' + suffix + '-daemon.log'
job['StandardOutPath'] = job['StandardErrorPath'] = guest + daemon_log
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    pending = build / 'dirhelper.pending'; shutil.copyfile(source, pending); pending.chmod(0o755); pending.replace(build / 'dirhelper')
    plist = build / ('com.apple.bsd.dirhelper' + suffix + '.plist'); plist.write_bytes(plistlib.dumps(job)); plist.chmod(0o644)
    (root / daemon_log).write_text('')
script = build / ('session' + suffix + '.sh')
script.write_text("""#!/bin/bash
set +e
launchctl load /Volumes/SystemRoot/workspace/runtime/native-dirhelper/com.apple.bsd.dirhelper.plist
loaded=$?
echo NATIVE_DIRHELPER_LOAD_STATUS "$loaded"
if [ "$loaded" -ne 0 ]; then exit "$loaded"; fi
trap 'launchctl remove com.apple.bsd.dirhelper >/dev/null 2>&1' EXIT
sleep 2
state=$(launchctl list com.apple.bsd.dirhelper)
printf '%s\n' "$state"
case "$state" in
*'"PID"'*) ;;
*) echo NATIVE_DIRHELPER_NO_RUNNING_PID_AFTER_START; exit 1;;
esac
/Volumes/SystemRoot/workspace/artifacts/lsd-runtime-paths /Volumes/SystemRoot/workspace/runtime/foundation-native-library-stage/libDarlingNativeDirHelper.dylib --initialize
status=$?
echo NATIVE_DIRHELPER_CLIENT_STATUS "$status"
launchctl list com.apple.bsd.dirhelper
exit "$status"
""".replace('/native-dirhelper/com.apple.bsd.dirhelper.plist', '/native-dirhelper/' + plist.name))
command = prefix + ['/bin/bash', guest + str(script.relative_to(root))]
log = 'logs/native-dirhelper' + suffix + '-session.log'
with (root / log).open('w') as stream:
    result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
text = (root / log).read_text(); print(text[-4000:])
passed = result.returncode == 0 and 'ORIGINAL_DIRHELPER_THREE_REAL_USER_DIRECTORIES_CREATED_OK' in text
report = dict(source_simple_log=profile.get('source_simple_log'), typed_malloc=profile.get('typed_malloc'), nounlink_export=profile.get('nounlink_export'), sandbox_container=profile.get('sandbox_container'), native_sysdir=profile.get('native_sysdir'), checked_at=datetime.now(timezone.utc).isoformat(), stage=stage, command=command, source_runtime=profile['source_runtime'],
    exit_status=result.returncode, runtime_execution_verified=passed, log=log, log_sha256=digest(log), diagnostic=text,
    source_sha256=digest('fixtures/hello/lsd-runtime-paths.c'), binary_sha256=digest('artifacts/lsd-runtime-paths'),
    original_binary_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), staged_binary_sha256=digest('runtime/native-dirhelper/dirhelper'),
    job=job, original_plist_sha256=hashlib.sha256(original_plist.read_bytes()).hexdigest(),
    daemon_log=daemon_log, daemon_log_sha256=digest(daemon_log), daemon_diagnostic=(root / daemon_log).read_text(),
    data_vault_protection_enforced=False, full_xcode_build_ready=False, signing_ready=False)
(root / ('artifacts/native-dirhelper' + suffix + '-probe.json')).write_text(json.dumps(report, indent=2) + '\n')
print('DAEMON:', report['daemon_diagnostic'][-3500:])
raise SystemExit(0 if passed else 1)
