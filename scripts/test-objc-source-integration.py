#!/usr/bin/env python3
"""Check actual loader snapshots and Security policy objects with the source runtime."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, subprocess
root = Path(__file__).resolve().parent.parent
read = lambda p: json.loads((root / p).read_text())
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-libtrace', action='store_true')
parser.add_argument('--user-local-dir-export', action='store_true')
parser.add_argument('--rootless-datavault-export', action='store_true')
parser.add_argument('--source-simple-log', action='store_true')
parser.add_argument('--typed-malloc', action='store_true')
parser.add_argument('--nounlink-export', action='store_true')
parser.add_argument('--sandbox-container', action='store_true')
parser.add_argument('--native-sysdir', action='store_true')
args = parser.parse_args()
if args.user_local_dir_export and not args.source_libtrace: parser.error('user directory export requires source libtrace')
if args.rootless_datavault_export and not args.user_local_dir_export: parser.error('data vault export requires user directory export')
if args.source_simple_log and not args.rootless_datavault_export: parser.error('simple log requires data vault profile')
if args.typed_malloc and not args.source_simple_log: parser.error('typed malloc requires simple log')
if args.nounlink_export and not args.typed_malloc: parser.error('nounlink export requires typed malloc')
if args.sandbox_container and not args.nounlink_export: parser.error('sandbox container requires nounlink export')
if args.native_sysdir and not args.sandbox_container: parser.error('native sysdir requires sandbox container')
profile = read('artifacts/uniform-type-identifiers-native-xcode-' + ('sysdir-' if args.native_sysdir else '') + ('sandbox-container-' if args.sandbox_container else '') + ('nounlink-' if args.nounlink_export else '') + ('typed-malloc-' if args.typed_malloc else '') + ('simple-log-' if args.source_simple_log else '') + ('datavault-' if args.rootless_datavault_export else '') + ('user-local-dir-' if args.user_local_dir_export else '') + ('source-libtrace-' if args.source_libtrace else '') + 'source-objc-support-showsdks.json')
label = 'sysdir-native' if args.native_sysdir else 'sandbox-container-source' if args.sandbox_container else 'nounlink-source' if args.nounlink_export else 'typed-malloc-source' if args.typed_malloc else 'simple-log-source' if args.source_simple_log else 'datavault-source' if args.rootless_datavault_export else 'libtrace-source' if args.source_libtrace else 'objc-source'
build = read('artifacts/objc-source-build.json')
assert digest(build['library']) == build['library_sha256'] == profile['source_objc']['library_sha256']
previous = read('artifacts/security-yield-integration.json')
policy = read('artifacts/security-policy-source-execution.json')
assert digest('fixtures/hello/security-external-developer-policy.m') == policy['test_source_sha256']
assert digest('artifacts/security-external-developer-policy') == policy['test_binary_sha256']
environment = os.environ.copy()
for name, item in profile['source_runtime'].items():
    assert digest(item['path']) == item['sha256']
    environment[name] = str(root / item['path'])
prefix = profile['command'][:-2]
markers = dict(snapshot='REAL_DYLD_PROCESS_SNAPSHOT_MACH_IMAGES_UUID_SEGMENTS_CONTENT_LOAD_UNLOAD_FROZEN_STATE_RIGHTS_OK',
    policy='SOURCE_SECURITY_POLICY_OWNED_LIFETIME_MUTATION_ISOLATION_AND_EIGHT_THREADS_128_REAL_OBJECTS_OK')
commands = {}
logs = {}
for name in ['snapshot', 'policy']:
    old = previous['commands'][name]
    index = next(i for i, value in enumerate(old) if value.startswith('/Volumes/SystemRoot/workspace/artifacts/'))
    command = prefix + old[index:]
    log = 'logs/' + label + '-integration-' + name + '.log'
    with (root / log).open('w') as stream:
        result = subprocess.run(command, cwd=root, env=environment, stdout=stream, stderr=subprocess.STDOUT)
    text = (root / log).read_text()
    print(name, result.returncode, text[-3000:], flush=True)
    assert result.returncode == 0, log
    assert re.search(r'(?m)^' + re.escape(markers[name]) + r'(?: \d+)?$', text)
    commands[name] = command
    logs[log] = digest(log)
report = dict(checked_at=datetime.now(timezone.utc).isoformat(), runtime_execution_verified=True,
    source_objc=build, selected_runtime=profile['source_runtime'], commands=commands, logs=logs,
    source_libtrace=profile.get('source_libtrace'), user_local_dir_export=profile.get('user_local_dir_export'),
    rootless_datavault_export=profile.get('rootless_datavault_export'),
    source_simple_log=profile.get('source_simple_log'), typed_malloc=profile.get('typed_malloc'), nounlink_export=profile.get('nounlink_export'), sandbox_container=profile.get('sandbox_container'), native_sysdir=profile.get('native_sysdir'),
    real_loader_snapshots_load_unload_UUID_segments_and_Mach_rights_verified=True,
    Security_policy_full_schema_lifetime_and_128_concurrent_objects_verified=True,
    certificate_chain_trust_evaluation_verified=False, full_xcode_build_ready=False, signing_ready=False)
(root / ('artifacts/' + label + '-integration.json')).write_text(json.dumps(report, indent=2) + '\n')
