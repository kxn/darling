#!/usr/bin/env python3
"""Validate real process/file enforcement and original Xcode service execution."""

# Preserve the newer native cryptography and FileCoordination checkpoint.
from pathlib import Path as _nc_Path
import json as _nc_json
_nc_state = _nc_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _nc_state.exists() and _nc_json.loads(_nc_state.read_text()).get('primary_report') == 'artifacts/native-crypto-progress.json':
    print('Preserving the newer native cryptography checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer archive/crypto checkpoint.
from pathlib import Path as _ac_Path
import json as _ac_json
_ac_state = _ac_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _ac_state.exists() and _ac_json.loads(_ac_state.read_text()).get('primary_report') == 'artifacts/archive-crypto-progress.json':
    print('Preserving the newer archive/crypto checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer dispatch/XPC checkpoint.
from pathlib import Path as _dx_Path
import json as _dx_json
_dx_state = _dx_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _dx_state.exists() and _dx_json.loads(_dx_state.read_text()).get('primary_report') == 'artifacts/dispatch-xpc-progress.json':
    print('Preserving the newer dispatch/XPC checkpoint'); raise SystemExit(0)

# A historical recorder must not replace the newer active checkpoint.
from pathlib import Path as _cw_Path
import json as _cw_json
_cw_state = _cw_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _cw_state.exists() and _cw_json.loads(_cw_state.read_text()).get('primary_report') == 'artifacts/cryptex-workqueue-progress.json':
    print('Preserving the newer Cryptex/workqueue checkpoint'); raise SystemExit(0)
from pathlib import Path as _device_Path
import json as _device_json
_device_state = _device_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _device_state.exists() and _device_json.loads(_device_state.read_text()).get('primary_report') == 'artifacts/device-identity-progress.json':
    print('Preserving the newer DeviceIdentity checkpoint'); raise SystemExit(0)
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, runpy, subprocess

root = Path(__file__).resolve().parent.parent
read = lambda n: json.loads((root / n).read_text())
digest = lambda n: hashlib.sha256((root / n).read_bytes()).hexdigest()
p = runpy.run_path(str(root / 'scripts/quarantine-vfs-runtime-profile.py'))['profile']()
runtime = p['source_runtime']
evidence = {}

def add(name):
    evidence[name] = digest(name)

def pair(data, key):
    assert digest(data[key]) == data[key + '_sha256'], data[key]
    add(data[key])

for item in runtime.values():
    assert digest(item['path']) == item['sha256']
stage = read('artifacts/quarantine-vfs-runtime-stage.json')
kernel = read(stage['kernel_build'])
server = read(stage['server_build'])
assert kernel['full_libsystem_kernel_source_build'] and kernel['complete_source_files'] == 877
assert server['baseline_build_output_restored']
assert digest(server['compilation_output_path']) == server['baseline_build_output_sha256']
assert stage['supported_self_policy_flags'] == [6]
for name in [stage['kernel_build'], stage['server_build'], 'artifacts/quarantine-vfs-runtime-stage.json']:
    add(name)
for n, sha in server['source_files'].items():
    assert digest(n) == sha
    add(n)
for entry in kernel['sources']:
    assert digest(entry['source']) == entry['sha256']
for n, sha in {**kernel['metadata_source_headers'], **stage['source_files']}.items():
    assert digest(n) == sha
    add(n)
for suffix in ['misc/quarantine.h', 'stat/quotactl.h']:
    folder = 'helper/' if suffix.startswith('misc/') else 'impl/'
    add('vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/' + folder + suffix)
add('vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/CMakeLists.txt')

test = read('artifacts/quarantine-vfs-source-test.json')
assert test['source_runtime'] == runtime and test['real_policy_and_VFS_execution_verified']
assert [r['label'] for r in test['checks']] == ['old-kernel-control', 'source']
assert all(r['exit_status'] == 0 for r in test['checks'])
for n, sha in {**test['sources'], **test['binaries']}.items():
    assert digest(n) == sha
    add(n)
for row in test['checks']:
    pair(row, 'log')
assert 'QUARANTINE_OLD_KERNEL_CANNOT_ACKNOWLEDGE_UNENFORCED_POLICY_OK' in (root / test['checks'][0]['log']).read_text()
assert 'QUARANTINE_VFS_REAL_PERSISTED_LABELS_KERNEL_PAIRING_FORK_EXEC_AND_UNCONFINED_CONTROL_OK' in (root / test['checks'][1]['log']).read_text()
output = root / 'runtime/quarantine-vfs-test/output'
for n, value in test['physical_Linux_xattrs'].items():
    assert os.getxattr(output / n, 'user.com.apple.quarantine').decode() == value
assert os.getxattr(output / 'new', 'user.user.com.apple.quarantine') == b'shadow'
assert 'user.com.apple.quarantine' not in os.listxattr(output / 'parent-unconfined-exec')
add('artifacts/quarantine-vfs-source-test.json')

quota = read('artifacts/quotactl-source-test.json')
assert quota['unsupported_filesystem_and_error_paths_verified'] and quota['exit_status'] == 0
pair(quota, 'runtime_stage')
for key in ['source', 'binary', 'log']:
    pair(quota, key)
assert not quota['quota_enabled_filesystem_verified'] and not quota['quota_mutations_implemented']
add('artifacts/quotactl-source-test.json')

regression = read('artifacts/quarantine-vfs-regression.json')
assert regression['source_runtime'] == runtime and len(regression['checks']) == 6
for row in regression['checks']:
    assert row['exit_status'] == 0
    for key in ['binary', 'log']:
        pair(row, key)
assert 'cases=852 hash=48 hmac=480 hkdf=324 checks=13385084' in (root / regression['checks'][-1]['log']).read_text()
add('artifacts/quarantine-vfs-regression.json')

probes = {}
for mode in ['version', 'showsdks', 'build']:
    stem = 'xcode-service-runtime-vfs-crypto-' + ('extended-' if mode != 'build' else '')
    stem += 'mobile-generation-policy-expected-sandbox-typed-cloud' + ('-base' if mode == 'version' else '') + '-prefs-daemon-' + mode
    name = 'artifacts/' + stem + '.json'
    data = read(name)
    assert data['source_runtime'] == runtime and data['UTI_preflight_verified']
    assert not data['diagnostic_without_UTI_preflight']
    assert data['xcode_process_started'] and data['xcode_invocation_attempted'] and data['xcode_process_returned']
    assert data['exit_status'] == (70 if mode == 'build' else 0)
    for key in ['log', 'script']:
        pair(data, key)
    for n, sha in data['service_logs'].items():
        assert digest(n) == sha
        add(n)
    for job in data['jobs']:
        assert digest(job['path']) == job['sha256']
        add(job['path'])
    daemon = next(n for n in data['service_logs'] if n.endswith('-cfprefsd-daemon.log'))
    daemon_text = (root / daemon).read_text()
    assert 'sent a request related to' in daemon_text and 'successfully sent' in daemon_text
    assert 'Failure to configure quarantine' not in daemon_text
    service = data['original_preference_service']
    assert digest(service['original']) == service['sha256'] == digest(service['selected'])
    text = (root / data['log']).read_text()
    if mode == 'version':
        assert 'Xcode 26.6' in text and 'Build version 17F113' in text
    elif mode == 'showsdks':
        assert 'iOS SDKs:' in text and 'macOS SDKs:' in text and '-sdk iphoneos26.5' in text
    else:
        assert 'Library not loaded: /System/Library/PrivateFrameworks/DeviceIdentity.framework' in text
        assert 'SERVICE_RUNTIME_XCODE_STATUS 70' in text
        assert 'Unimplemented syscall (165)' not in text
    assert digest('scripts/runtime-ns.sh') == data['runtime_namespace_script_sha256']
    probes[mode] = dict(report=name, exit_status=data['exit_status'], strict_UTI=True, original_process_returned=True)
    add(name)

semantics = read('artifacts/quarantine-vfs-native-semantics.json')
assert semantics['setprocinfo_flags_byte_offset'] == 64
for n, sha in semantics['reference_files'].items():
    assert digest(n) == sha
    add(n)
add('artifacts/quarantine-vfs-native-semantics.json')
for history in ['artifacts/coreutils-quarantine-history/manifest.json', 'artifacts/quarantine-vfs-initial-pass/manifest.json']:
    for row in read(history).values():
        assert digest(row.get('archived', row.get('object'))) == row['sha256']
    add(history)

device = read('artifacts/device-identity-native-load.json')
assert not device['native_dlopen_verified'] and device['exit_status'] == 1
assert 'Library not loaded: /System/Library/PrivateFrameworks/MultiverseSupport.framework' in (root / device['log']).read_text()
for key in ['stage', 'runtime', 'source', 'binary', 'log']:
    pair(device, key)
device_stage = read(device['stage'])
for n, sha in device_stage['files'].items():
    assert digest(n) == sha
for n, sha in device_stage['dependencies'].items():
    assert digest(n) == sha
    add(n)
pair(device_stage, 'reconstruction')
assert not device_stage['backend_overrides'] and not device_stage['device_attestation_verified']
add('artifacts/device-identity-native-load.json')

for repo, label in [('vendor/darlingserver', 'darlingserver-quarantine-vfs-source'), ('vendor/darling/src/external/xnu', 'xnu-quarantine-vfs-quota-source'), ('vendor/darling', 'darling-quarantine-vfs-companions-source')]:
    name = 'artifacts/' + label + '.patch'
    subprocess.run(['git', 'apply', '--reverse', '--check', str(root / name)], cwd=root / repo, check=True)
    subprocess.run(['git', 'diff', '--check'], cwd=root / repo, check=True)
    add(name)

original = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
original_sha = digest(original)
assert original_sha == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild') == 'd6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
scripts = ['scripts/' + n for n in [
    'build-quarantine-vfs-server.py', 'stage-quarantine-vfs-runtime.py', 'quarantine-vfs-runtime-profile.py',
    'build-libsystem-kernel-source.py', 'test-quarantine-vfs-source.py', 'test-quotactl-source.py',
    'test-quarantine-vfs-regression.py', 'probe-xcode-service-runtime.py', 'record-quarantine-vfs-progress.py',
    'mount-path-kernel-profile.py', 'sandbox-policy-source-profile.py', 'pid-generation-source-profile.py',
    'rebuild-c-cache-image.py', 'stage-device-identity-native.py', 'device-identity-native-profile.py', 'probe-device-identity-native.py']]
scripts += read('artifacts/quarantine-vfs-recorder-guards.json')
add('artifacts/quarantine-vfs-recorder-guards.json')
add('README.md')
add('config/cache-image-pins.json')
next_work = [
    'Complete original DeviceIdentity dependencies, beginning with MultiverseSupport and its actual dependency closure. Current staged original DeviceIdentity/libbootpolicy do not yet load. Then rerun original project build with strict UTI, without suppressing required simulator plugins.',
    'Investigate lsd LastExitStatus 139 after the successful preflight during plugin discovery; keep it recorded as an unresolved service-lifecycle failure.',
    'Continue real Xcode compiler/build-service execution, then Unity/CocoaPods compilation, archive, signing and export. Version and SDK listing do not prove any compilation or signing.',
    'Expand Quarantine/Sandbox behavior when actually required. Only self flags 6, tested regular files/directories, fork/exec state and the documented file events are supported. Native NULL exclusion-pattern clone, Linux symlink labels, full xattr namespace/list conversion, other flags and actual Seatbelt profiles remain unresolved.',
    'Retain previous unresolved strong C++ chained-fixup replacement coalescing and production Security NSXPC failures. Do not promote the default launcher before full execution is proven.'
]
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), previous_report='artifacts/coreutils-quarantine-progress.json', previous_evidence_archive='artifacts/coreutils-quarantine-history/manifest.json',
    previous_goal_turn_classification='no progress', previous_goal_turn_note='The immediately preceding turn answered the hook/source question using read-only status checks. This turn revalidated stopped processes and the failed VFS test, changed source, and verified original runtime execution.', current_goal_turn_classification='progress', source_runtime=runtime,
    full_source_kernel_files=877, self_quarantine_flags_6_real_file_enforcement_verified=True,
    old_kernel_cannot_acknowledge_policy_verified=True, cfprefsd_original_protocol_responses_verified=True,
    strict_UTI_verified=True, original_xcode_version_verified=True, original_xcode_SDK_listing_verified=True,
    original_project_build_exit_status=70, current_build_failure='Required CoreSimulator/IDESimulatorFoundation dependency DeviceIdentity is missing from the selected runtime; experimental original DeviceIdentity still lacks MultiverseSupport.',
    quota_query_backend='Actual Linux quotactl_fd; quota-unsupported filesystem and 8 error checks verified; quota-enabled filesystem not verified; quota mutations unsupported.',
    original_xcodebuild_sha256=original_sha, probe_results=probes, default_launcher_changed=False,
    default_launcher_sha256=digest('bin/xcodebuild'), full_xcode_build_ready=False, archive_verified=False,
    signing_ready=False, export_verified=False, complete=False, goal_status='active', next_work=next_work,
    evidence=evidence, scripts={n:digest(n) for n in scripts})
destination = 'artifacts/quarantine-vfs-progress.json'
(root / destination).write_text(json.dumps(record, indent=2) + '\n')
state = read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'], primary_report=destination, goal_status='active', complete=False,
    latest_selected_runtime=runtime, latest_xcode_loader_blocker='DeviceIdentity.framework required by CoreSimulator',
    latest_staged_coreml_and_metal_blocker='Required IDE plugin dependency closure',
    latest_xcode_runtime_failure=record['current_build_failure'], latest_xcode_failure_kind='required_simulator_plugin_dependency',
    latest_implementation_form='Darling server and complete source libsystem_kernel implement real Quarantine flags-6 process/file state, file tagging, xattr protections and exec checks. Native cfprefsd responds; original Xcode version and SDK listing pass strict UTI. No full compilation/archive/sign/export success.',
    active_build=dict(task='quarantine-vfs-and-original-Xcode-services', running=False, report=destination), next_work=next_work)
state.setdefault('source_components', {}).update(Quarantine_VFS_progress=destination, Quarantine_kernel=stage['kernel_build'], Quarantine_server=stage['server_build'])
state['latest_validation_reports'] = list(dict.fromkeys(state.get('latest_validation_reports', []) + list(evidence) + [destination]))
(root / 'artifacts/current-work-state.json').write_text(json.dumps(state, indent=2) + '\n')
print('Validated real Quarantine VFS, native cfprefsd and strict original Xcode version/SDK listing; required project plugin still fails, full goal active')
