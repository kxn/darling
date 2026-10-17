#!/usr/bin/env python3
"""Record verified logging repairs and the remaining original service failures."""

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
import hashlib, json, subprocess
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

if json.loads((root / 'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/directory-runtime-progress.json', 'artifacts/directory-services-progress.json', 'artifacts/sysdir-metadata-progress.json', 'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Preserving the later directory runtime source checkpoint')
    raise SystemExit(0)
read = lambda p: json.loads((root / p).read_text())
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
build = read('artifacts/libtrace-source-build.json')
trace = read('artifacts/libtrace-source-execution.json')
repo = root / 'vendor/darling/src/external/libtrace'
assert build['full_libtrace_source_build'] and build['complete_source_files'] == 8
assert build['original_exports_preserved'] == 142 and build['source_exports'] == 143
assert digest(build['library']) == build['library_sha256']
assert trace['build'] == build and trace['runtime_execution_verified'] and trace['actual_ASL_stderr_record_text_verified']
for path, value in build['source_files'].items():
    assert hashlib.sha256((repo / path).read_bytes()).hexdigest() == value
assert digest(trace['log']) == trace['log_sha256']
assert digest('fixtures/hello/libtrace-source.m') == trace['test_source_sha256']
assert digest('artifacts/libtrace-source') == trace['test_binary_sha256']
for marker in ['SOURCE_LIBTRACE_21_COMPILER_ENCODED_', 'SOURCE_LIBTRACE_ALL_TRUNCATIONS_GUARD_PAGE_', 'LIBTRACE_ASL_E2E -77']:
    assert marker in trace['diagnostic']
stages = {}
for label, prefix, fixture, marker in [
    ('user_directory', 'user-local-dir', 'user-local-dir-export', 'ORIGINAL_USER_DIRECTORY_NAMED_EXPORT_DIRECT_ABI_BOUNDS_AND_ERRNO_OK 4 11'),
    ('data_vault', 'rootless-datavault', 'rootless-datavault-export', 'ORIGINAL_DATAVAULT_NAMED_EXPORT_DIRECT_ERRORS_AND_FILESYSTEM_EFFECTS_OK 0 4')]:
    stage = read('artifacts/' + prefix + '-export-stage.json')
    test = read('artifacts/' + prefix + '-export-execution.json')
    assert test['stage'] == stage and test['runtime_execution_verified'] and test['exit_status'] == 0
    for key in ['library', 'helper', 'original_provider', 'source']:
        assert digest(stage[key]) == stage[key + '_sha256']
    assert stage['export_changes']['original_instructions_and_other_bytes_preserved']
    assert not stage['export_changes']['provider_entire_namespace_reexported']
    assert digest(test['log']) == test['log_sha256'] and marker in test['diagnostic']
    assert digest('fixtures/hello/' + fixture + '.c') == test['source_sha256']
    assert digest('artifacts/' + fixture) == test['binary_sha256']
    stages[label] = stage
assert stages['data_vault']['base_sha256'] == stages['user_directory']['library_sha256']
analysis = read('artifacts/rootless-datavault-native-analysis.json')
assert digest(analysis['log']) == analysis['log_sha256']
assert analysis['data_vault_flag'] == 128 and not analysis['protection_backend_implemented']
prefix = 'artifacts/uniform-type-identifiers-native-xcode-datavault-user-local-dir-source-libtrace-source-objc-support-'
probe = read(prefix + 'showsdks.json'); version = read(prefix + 'version.json')
integration = read('artifacts/datavault-source-integration.json')
lsd = read('artifacts/native-lsd-datavault-user-local-dir-source-libtrace-probe.json')
for result in [probe, version, integration, lsd]:
    assert result['source_libtrace'] == build
    assert result['user_local_dir_export'] == stages['user_directory']
    assert result['rootless_datavault_export'] == stages['data_vault']
    if 'log' in result: assert digest(result['log']) == result['log_sha256']
    for path, value in result.get('logs', {}).items(): assert digest(path) == value
assert version['exit_status'] == 0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert probe['exit_status'] == 255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in probe['diagnostic']
assert not probe['sdk_listing_succeeded'] and integration['runtime_execution_verified']
assert lsd['original_binary_sha256'] == lsd['staged_binary_sha256'] == digest('runtime/native-lsd/lsd')
assert len(lsd['selected_job']['MachServices']) == 13 and lsd['exit_status'] == 1
assert not lsd['UTI_functional_execution_verified']
for marker in ['LaunchServices database schema version: 20971545', '#LSDatabaseBuilder Seeding database',
               'Loaded LS database with sequence number 0', 'Failed to create data vault URL', 'nil argument']:
    assert marker in lsd['daemon_diagnostic']
assert 'Symbol not found:' not in lsd['daemon_diagnostic']
directory = read('artifacts/native-dirhelper-probe.json')
assert directory['original_binary_sha256'] == directory['staged_binary_sha256'] == digest('runtime/native-dirhelper/dirhelper')
assert digest(directory['log']) == directory['log_sha256']
assert digest(directory['daemon_log']) == directory['daemon_log_sha256']
assert directory['job']['MachServices'] == {'com.apple.bsd.dirhelper': True}
assert directory['exit_status'] == 1 and not directory['runtime_execution_verified']
assert 'Symbol not found: __os_log_simple' in directory['daemon_diagnostic']
assert digest('fixtures/hello/lsd-runtime-paths.c') == directory['source_sha256']
assert digest('artifacts/lsd-runtime-paths') == directory['binary_sha256']
selected = probe['source_runtime']
assert selected == version['source_runtime'] == integration['selected_runtime'] == lsd['source_runtime'] == directory['source_runtime']
for item in selected.values(): assert digest(item['path']) == item['sha256']
original = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original) == probe['original_xcodebuild_sha256'] == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
baseline_trace = 'runtime/rootfs/usr/libexec/darling/usr/lib/libTrace.dylib'
assert digest(baseline_trace) == digest('runtime/libdyld-source/darling-root/usr/lib/libTrace.dylib') == 'c73890ca6bd935d20017d03e397076ea948d6d25ee6ce1eab0310a158337a959'
patch_path = 'artifacts/darling-libtrace-parser.patch'
(root / patch_path).write_bytes(subprocess.check_output(['git', '-C', str(repo), 'diff', '--binary']))
subprocess.run(['git', '-C', str(repo), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(repo), 'apply', '--reverse', '--check', str(root / patch_path)], check=True)
paths = [
    'artifacts/libtrace-source-build.json', 'artifacts/libtrace-source-execution.json',
    'artifacts/user-local-dir-export-stage.json', 'artifacts/user-local-dir-export-execution.json',
    'artifacts/rootless-datavault-native-analysis.json', 'artifacts/rootless-datavault-export-stage.json',
    'artifacts/rootless-datavault-export-execution.json', prefix + 'showsdks.json', prefix + 'version.json',
    'artifacts/datavault-source-integration.json', 'artifacts/native-lsd-datavault-user-local-dir-source-libtrace-probe.json',
    'artifacts/native-dirhelper-probe.json', patch_path]
sources = ['scripts/build-libtrace-source.py', 'scripts/test-libtrace-source.py',
    'scripts/stage-user-local-dir-export.py', 'scripts/test-user-local-dir-export.py',
    'scripts/analyze-rootless-datavault-native.py', 'scripts/stage-rootless-datavault-export.py',
    'scripts/test-rootless-datavault-export.py', 'scripts/probe-native-lsd.py',
    'scripts/probe-native-dirhelper.py', 'scripts/probe-uniform-type-identifiers-native.py',
    'scripts/test-objc-source-integration.py', 'scripts/record-libtrace-directory-progress.py']
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), evidence={p: digest(p) for p in paths},
    scripts={p: digest(p) for p in sources}, source_libtrace=build, selected_runtime=selected,
    direct_Darling_source_parser_repair=True, actual_compiler_encoded_21_cases_and_guard_page_rejections_verified=True,
    actual_ASL_stderr_log_and_original_lsd_schema_messages_verified=True,
    original_user_directory_15_differential_cases_verified=True,
    original_data_vault_four_error_and_filesystem_differential_cases_verified=True,
    original_lsd_reaches_database_seed_and_store_load=True, original_lsd_service_start_succeeded=False,
    user_directory_daemon_start_succeeded=False, data_vault_protection_enforced=False,
    original_xcode_version_verified=True, full_UTI_URL_conformance_and_database_queries_verified=False,
    full_runtime_compatibility=False, full_xcode_build_ready=False, signing_ready=False,
    implementation_form='Full 8-source Darling libtrace with parser/scalar/NUL-boundary fixes and optional real ASL stderr diagnostics. Two typed deferred bridges expose unchanged original user-directory/data-vault code through individually named exports in private libSystem copies. Original lsd/dirhelper binaries and Mach service definitions remain unchanged; this is not a unified full Darling rebuild.',
    limits=['Other existing activity/formatting/plugin logging stubs remain unsupported; persistent unified-log delivery is unverified.',
        'Original lsd now seeds a database but fails on nil data-vault URL. Native _dirhelper initialization returned ENOENT; its original daemon cannot load because _os_log_simple is missing.',
        'Data-vault normal creation returns ENOPOLICY and leaves an unprotected directory in the isolated test. No MAC policy, protected flag enforcement or successful protected-directory creation is claimed.',
        'Original -showsdks still lacks Cocotron CALayerContext; project build, archive, signing and export are not verified.'])
destination = 'artifacts/libtrace-directory-progress.json'
(root / destination).write_text(json.dumps(record, indent=2) + '\n')
state = read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'], goal_status='active', complete=False, primary_report=destination,
    active_build=dict(task='libtrace-and-original-directory-services', running=False, report=destination),
    latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Source libtrace fixes the native lsd logging crash; real schema messages and database seeding execute. Original lsd then fails on nil data-vault URL; native directory initialization returns ENOENT and the original dirhelper daemon cannot load _os_log_simple. Native data-vault calls retain actual ENOPOLICY errors. Genuine -version passes; -showsdks still lacks CALayerContext. Full project build/archive/signing/export remain incomplete.')
next_steps = [
    'Implement the real _os_log_simple primitive logging ABI required by original Intel dirhelper; retain actual log output and error semantics. Start the original com.apple.bsd.dirhelper Mach service and pass actual native _dirhelper user-directory initialization before combining it with lsd.',
    'Complete real directory/data-vault backing required by native LaunchServices. Current protected mkdir returns ENOPOLICY; fchflags is unsupported and native cleanup uses unlinkat flags 0x880. Inspect the required modern flags and actual policy/backend semantics; do not replace protected success with ordinary mkdir or suppress failures.',
    'Once original lsd starts and replies, pass the complete original Swift UTI URL-extension, type-conformance and extension/MIME lookup fixture. Database seeding alone does not verify the Mach/XPC database service or the URL client.']
remaining = [s for s in state['next_work'] if not s.startswith(('Resolve the original Intel lsd startup crash:', 'Once original lsd starts and replies,'))]
state['next_work'] = list(dict.fromkeys(next_steps + remaining))
state['last_verification'] = list(dict.fromkeys(state['last_verification'] + [
    'Full 8-source libtrace preserves 142 exports and passes 21 real compiler-encoded cases, all buffer-prefix truncations at a guard page, and actual ASL stderr delivery. Original lsd now emits real schema messages and reaches database seeding. Native user-directory 15-case and protected-mkdir 4-case differential tests pass; these preserve actual errors, not protected-directory success. Latest loader snapshot covers 49 images and 128 concurrent policy objects pass. Genuine Xcode version passes; SDK listing, directory daemon, full UTI client and full builds remain incomplete.']))
state['latest_validation_reports'] = list(dict.fromkeys(state['latest_validation_reports'] + paths + [destination]))
state.setdefault('source_components', {})['libtrace'] = 'artifacts/libtrace-source-build.json'
state['source_components']['logging_and_directory_progress'] = destination
(root / 'artifacts/current-work-state.json').write_text(json.dumps(state, indent=2) + '\n')
print('Recorded source libtrace repairs and original directory-service failures; full goal remains active')
