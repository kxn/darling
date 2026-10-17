#!/usr/bin/env python3
"""Record real directory initialization and the next genuine LaunchServices failure."""

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
# A historical recorder must not replace the current validated runtime state.
from pathlib import Path as _qvf_Path
import json as _qvf_json
_qvf_state = _qvf_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _qvf_state.exists() and _qvf_json.loads(_qvf_state.read_text()).get('primary_report') in {'artifacts/quarantine-vfs-progress.json','artifacts/device-identity-progress.json'}:
    print('Preserving the newer Quarantine VFS checkpoint'); raise SystemExit(0)
# A historical recorder must not replace the current dependency/source checkpoint.
from pathlib import Path as _mdns_Path
import json as _mdns_json
_mdns_state = _mdns_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _mdns_state.exists() and _mdns_json.loads(_mdns_state.read_text()).get('primary_report') in {'artifacts/mdns-source-progress.json','artifacts/security-cloud-rpc-progress.json','artifacts/security-current-item-progress.json','artifacts/sandbox-check-progress.json','artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving newer mdns/source checkpoint; historical recorder skipped')
    raise SystemExit(0)
# Preserve the newer source log-pack/FSEvents checkpoint when replaying an old recorder.
import json as _pack_json
from pathlib import Path as _PackPath
_pack_state = _PackPath(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _pack_state.exists() and _pack_json.loads(_pack_state.read_text()).get('primary_report') == 'artifacts/log-pack-progress.json':
    print('Preserving newer source log-pack/FSEvents checkpoint')
    raise SystemExit(0)
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, shutil, subprocess
root = Path(__file__).resolve().parent.parent
if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/foundation-coherent-progress.json':
    print('Preserving the newer source selector/coherent Foundation/SDK checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/fsevents-flush-progress.json':
    print('Preserving the newer source FSEvents flush checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/combine-fsevents-progress.json':
    print('Preserving the newer original Combine/source FSEvents checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/imageio-native-progress.json':
    print('Preserving the newer original ImageIO/source-ABI checkpoint')
    raise SystemExit(0)

if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') == 'artifacts/mobilegestalt-progress.json':
    print('Preserving the newer MobileGestalt/source-dyld checkpoint')
    raise SystemExit(0)


if json.loads((root/'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/layer-log-progress.json','artifacts/log-hooks-progress.json'}:
    print('Preserving the newer source layer/log checkpoint')
    raise SystemExit(0)

if json.loads((root / 'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/sysdir-metadata-progress.json', 'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Preserving the later paired sysdir/metadata checkpoint')
    raise SystemExit(0)
read = lambda p: json.loads((root / p).read_text())
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
stage = read('artifacts/sandbox-container-source-stage.json')
test = read('artifacts/sandbox-container-source-execution.json')
analysis = read('artifacts/sandbox-container-native-analysis.json')
assert test['stage'] == stage and test['runtime_execution_verified'] and test['exit_status'] == 0
for field in ['base', 'library', 'helper', 'original_provider', 'source']:
    assert digest(stage[field]) == stage[field + '_sha256']
assert stage['export_changes']['added_names'] == ['_sandbox_container_path_for_audit_token']
assert stage['export_changes']['original_instructions_and_other_bytes_preserved']
assert digest(test['log']) == test['log_sha256']
assert digest('fixtures/hello/sandbox-container-source.c') == test['source_sha256']
assert digest('artifacts/sandbox-container-source') == test['binary_sha256']
assert 'SOURCE_SANDBOX_CONTAINER_NATIVE_AND_REAL_MAC_ERRORS_UNCHANGED_BUFFER_OK 12' in test['diagnostic']
assert 'SOURCE_SANDBOX_CONTAINER_REAL_TASK_AUDIT_TOKEN_PID_AND_CREDENTIAL_FIELDS_OK' in test['diagnostic']
assert digest(analysis['log']) == analysis['log_sha256'] and analysis['compiled_helper_sha256'] == stage['helper_sha256']
assert analysis['operation'] == 4 and analysis['audit_token_size'] == 32
repair = read('artifacts/overlay-var-repair.json')
assert repair['baseline_link_matches'] and os.readlink(root / 'runtime/state/prefix/var') == 'private/var'
for item in repair['original_entries']:
    path = root / repair['original_upper_tree'] / item['path']
    if 'sha256' in item: assert digest(path) == item['sha256']
    if 'link' in item: assert os.readlink(path) == item['link']
prepared = read('artifacts/native-directory-root-prepare.json')
assert prepared['exit_status'] == 0 and prepared['private_root_layout_and_base_directory_verified']
assert digest(prepared['log']) == prepared['log_sha256']
resources = read('artifacts/coretypes-resources-stage.json')
assert resources['unchanged_resources'] and resources['exported_type_declarations'] == 761 and resources['imported_type_declarations'] == 440
for relative, item in resources['files'].items():
    source, target = root / resources['source'] / relative, root / resources['target'] / relative
    if 'sha256' in item: assert digest(source) == digest(target) == item['sha256']
    if 'link' in item: assert os.readlink(source) == os.readlink(target) == item['link']
directory = read('artifacts/native-dirhelper-sandbox-container-nounlink-typed-malloc-source-simple-log-probe.json')
assert directory['sandbox_container'] == stage and directory['runtime_execution_verified'] and directory['exit_status'] == 0
assert directory['original_binary_sha256'] == directory['staged_binary_sha256'] == digest('runtime/native-dirhelper/dirhelper')
assert directory['job']['MachServices'] == {'com.apple.bsd.dirhelper': True}
assert digest(directory['log']) == directory['log_sha256'] and digest(directory['daemon_log']) == directory['daemon_log_sha256']
assert '"PID" = ' in directory['diagnostic'] and 'ORIGINAL_DIRHELPER_THREE_REAL_USER_DIRECTORIES_CREATED_OK' in directory['diagnostic']
assert 'started normally' in directory['daemon_diagnostic'] and 'invalid ownership' not in directory['daemon_diagnostic']
for suffix in ['0', 'T', 'C']:
    assert (root / 'runtime/state/prefix/private/var/folders/zz/zyxvpxvq6csfxvn_n0000000000000' / suffix).is_dir()
lsd_path = 'artifacts/native-lsd-paired-dirhelper-sandbox-container-datavault-user-local-dir-source-libtrace-probe.json'
lsd = read(lsd_path)
assert lsd['sandbox_container'] == stage and not lsd['UTI_functional_execution_verified']
assert lsd['original_binary_sha256'] == lsd['staged_binary_sha256'] == digest('runtime/native-lsd/lsd')
assert len(lsd['selected_job']['MachServices']) == 13
assert lsd['paired_dirhelper_job']['MachServices'] == {'com.apple.bsd.dirhelper': True}
for path, sha in lsd['logs'].items(): assert digest(path) == sha
assert 'NATIVE_LSD_DIRHELPER_LOAD_STATUS 0' in lsd['diagnostic'] and 'NATIVE_LSD_LAUNCHCTL_LOAD_STATUS 0' in lsd['diagnostic']
assert 'Symbol not found: _sysdir_start_search_path_enumeration_private' in lsd['daemon_diagnostic']
assert '#LSDatabaseBuilder register apps' in lsd['daemon_diagnostic'] and "nil argument" not in lsd['daemon_diagnostic']
assert 'Error -50 registering path /System/Library/CoreServices/CoreTypes.bundle' in lsd['daemon_diagnostic']
prefix = 'artifacts/uniform-type-identifiers-native-xcode-sandbox-container-nounlink-typed-malloc-simple-log-datavault-user-local-dir-source-libtrace-source-objc-support-'
probe, version = read(prefix + 'showsdks.json'), read(prefix + 'version.json')
integration = read('artifacts/sandbox-container-source-integration.json')
for item in [probe, version, integration]:
    assert item['sandbox_container'] == stage
    if 'log' in item: assert digest(item['log']) == item['log_sha256']
    for path, sha in item.get('logs', {}).items(): assert digest(path) == sha
assert version['exit_status'] == 0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert probe['exit_status'] == 255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in probe['diagnostic']
assert integration['runtime_execution_verified']
selected = probe['source_runtime']
assert selected == version['source_runtime'] == integration['selected_runtime'] == directory['source_runtime'] == lsd['source_runtime'] == test['source_runtime'] == prepared['source_runtime']
assert selected == read('artifacts/directory-runtime-progress.json')['selected_runtime']
for item in selected.values(): assert digest(item['path']) == item['sha256']
original = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original) == probe['original_xcodebuild_sha256'] == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
store = root / 'runtime/state/prefix/private/var/folders/zz/zyxvpxvq6csfxvn_n0000000000000/0/com.apple.LaunchServices.dv/SystemDataOnly-com.apple.LaunchServices-20971545-v2.csstore'
assert store.stat().st_size > 0
snapshot = root / 'runtime/native-lsd/system-data-only-observed.csstore'
shutil.copyfile(store, snapshot)
store_observation = dict(snapshot=str(snapshot.relative_to(root)), size=snapshot.stat().st_size,
    sha256=digest(snapshot), native_store_deserialization_or_catalog_correctness_verified=False)
patch = 'artifacts/darling-sandbox-container-query.patch'
result = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', 'src/sandbox/container.c'], cwd=root / 'vendor/darling', capture_output=True)
assert result.returncode == 1, result.stderr
(root / patch).write_bytes(result.stdout)
subprocess.run(['git', '-C', str(root / 'vendor/darling'), 'apply', '--reverse', '--check', str(root / patch)], check=True)
assert not (root / 'logs/host-smoke.diff').read_bytes()
for path in ['logs/smoke-guest.log', 'logs/smoke-persistence.log', 'logs/smoke-isolation.log', 'logs/smoke-exit-code.log']: assert (root / path).exists()
paths = ['artifacts/sandbox-container-source-stage.json', 'artifacts/sandbox-container-source-execution.json',
    'artifacts/sandbox-container-native-analysis.json', 'artifacts/overlay-var-repair.json',
    'artifacts/native-directory-root-prepare.json', 'artifacts/coretypes-resources-stage.json',
    'artifacts/native-dirhelper-sandbox-container-nounlink-typed-malloc-source-simple-log-probe.json', lsd_path,
    prefix + 'showsdks.json', prefix + 'version.json', 'artifacts/sandbox-container-source-integration.json', patch,
    'logs/host-smoke.diff', 'logs/smoke-guest.log', 'logs/smoke-persistence.log', 'logs/smoke-isolation.log', 'logs/smoke-exit-code.log']
scripts = ['build-sandbox-container-source.py', 'test-sandbox-container-source.py', 'analyze-sandbox-container-native.py',
    'repair-overlay-var.py', 'prepare-native-directory-root.py', 'stage-coretypes-resources.py',
    'probe-uniform-type-identifiers-native.py', 'probe-native-dirhelper.py', 'probe-native-lsd.py',
    'test-objc-source-integration.py', 'record-directory-services-progress.py']
destination = 'artifacts/directory-services-progress.json'
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), evidence={p: digest(p) for p in paths},
    scripts={'scripts/' + p: digest('scripts/' + p) for p in scripts}, selected_runtime=selected,
    source_sandbox_container_native_ABI_and_12_missing_policy_comparisons_verified=True,
    root_self_task_audit_token_PID_and_credential_fields_verified=True,
    PID_version_and_foreign_identity_authorization_verified=False,
    guest_var_symlink_restored_with_full_old_upper_backup=True, original_three_user_directories_created=True,
    original_dirhelper_daemon_started=True, positive_cross_process_directory_MIG_requests_verified=False,
    original_lsd_reaches_application_scan=True, original_lsd_start_succeeded=False,
    native_system_data_store_file_written=store_observation, coretypes_resources_staged_unchanged=True,
    coretypes_catalog_registration_verified=False, full_UTI_client_verified=False,
    original_xcode_version_verified=True, sdk_listing_verified=False,
    full_xcode_build_ready=False, signing_ready=False,
    implementation_form='A direct Darling source Sandbox query wrapper uses the original Intel audit-token/five-slot MAC ABI. It preserves actual ENOPOLICY; no container path is fabricated. The private guest /var symlink is restored with a complete backup, and original recovery CoreTypes resources are staged unchanged. Original dirhelper and directory library now execute successfully in the selected experiment; Xcode and the seven earlier source runtime binaries are unchanged.',
    limits=['The current kernel has no Sandbox container policy. Self root task token fields match, but PID version is zero; foreign identity, PID reuse and path authority are not verified.',
        'Original _dirhelper may create the current root user directories locally; daemon startup plus those directories do not prove positive cross-process directory MIG execution.',
        'Existing stat conversion substitutes caller UID/GID and clears flags. Protected directories and multi-user ownership are not implemented by this change.',
        'Original lsd no longer throws on a nil data-vault URL, but still cannot load the private sysdir starter. CoreTypes registration reports EINVAL despite genuine resources being present. The data-only store file is not proof of a valid catalog.',
        'SDK listing still lacks CALayerContext. Full Unity/CocoaPods project build, archive, signing and export remain incomplete.'])
(root / destination).write_text(json.dumps(record, indent=2) + '\n')
state = read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'], goal_status='active', complete=False, primary_report=destination,
    active_build=dict(task='source-container-query-and-original-directory-services', running=False, report=destination),
    latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Original dirhelper starts and native library creates three real user directories after restoring the private /var layout. Paired original lsd advances to application scan and writes a data-only store, then fails to load sysdir_start_search_path_enumeration_private. CoreTypes is genuine/present but registration still fails EINVAL. Version, 53-image loader/policy regression and host-isolated smoke pass; SDK listing still lacks CALayerContext and full builds/signing remain incomplete.')
state['next_work'] = list(dict.fromkeys([
    'Restore the real private sysdir enumeration required by lsd. The original DirHelper already exports the private starter plus public starter/get-next; preserve matching enumeration state ABI and lifetime. Inspect all three entries rather than mixing a native starter with the old Darling decoder. Then retry original paired services and the complete UTI client.',
    'Resolve actual file-metadata errors while original LaunchServices registers CoreTypes.bundle: genuine 761 exported/440 imported declarations are installed byte-for-byte, but registration fails NSPOSIXErrorDomain EINVAL. Inspect the actual getattrlist/URL resource-key request and backend before claiming a populated type catalog.',
] + [s for s in state['next_work'] if not s.startswith('Expose/implement the real sandbox_container_path_for_audit_token ABI')]))
state['last_verification'] = list(dict.fromkeys(state['last_verification'] + [
    'Source Sandbox container query matches original by-value Intel ABI and 12 actual missing-policy errors. Restored guest /var -> private/var with full old upper backup; original dirhelper stays alive and its native library creates 0/T/C directories. Paired original lsd reaches application scan and writes a 219420-byte data-only store; private sysdir entry and CoreTypes metadata registration remain unresolved. Genuine version, 53-image snapshot/128 policies and host-isolated smoke pass. Full Xcode build/signing are not complete.']))
state['latest_validation_reports'] = list(dict.fromkeys(state['latest_validation_reports'] + paths + [destination]))
state.setdefault('source_components', {}).update(sandbox_container_query='artifacts/sandbox-container-source-stage.json', directory_services_progress=destination)
(root / 'artifacts/current-work-state.json').write_text(json.dumps(state, indent=2) + '\n')
print('Recorded original directory startup/creation and next LaunchServices failures; full Xcode goal remains active')
