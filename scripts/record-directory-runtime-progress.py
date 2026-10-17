#!/usr/bin/env python3
"""Validate real simple-log/allocator execution and retain original service failures."""

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

if json.loads((root / 'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/directory-services-progress.json', 'artifacts/sysdir-metadata-progress.json', 'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Preserving the later original directory-services checkpoint')
    raise SystemExit(0)
read = lambda p: json.loads((root / p).read_text())
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
simple = read('artifacts/os-log-simple-source-stage.json')
log_test = read('artifacts/os-log-simple-source-execution.json')
typed = read('artifacts/typed-malloc-source-stage.json')
typed_test = read('artifacts/typed-malloc-source-execution.json')
nounlink = read('artifacts/rootless-nounlink-export-stage.json')
nounlink_test = read('artifacts/rootless-nounlink-export-execution.json')
for stage, test, fixture, fields in [
    (simple, log_test, 'os-log-simple-source', ['library', 'helper']),
    (typed, typed_test, 'typed-malloc-source', ['library', 'helper', 'source']),
    (nounlink, nounlink_test, 'rootless-nounlink-export', ['library', 'helper', 'source', 'original_provider'])]:
    assert test['stage'] == stage and test['runtime_execution_verified'] and test['exit_status'] == 0
    for field in fields: assert digest(stage[field]) == stage[field + '_sha256']
    assert digest(stage['base']) == stage['base_sha256']
    assert digest(test['log']) == test['log_sha256']
    assert digest('fixtures/hello/' + fixture + '.c') == test['source_sha256']
    assert digest('artifacts/' + fixture) == test['binary_sha256']
    assert stage['export_changes']['original_instructions_and_other_bytes_preserved']
    assert not stage['export_changes']['provider_entire_namespace_reexported']
for group in ['compile_inputs', 'source_files']:
    for path, sha in simple[group].items(): assert digest(path) == sha
assert simple['full_simple_log_source_port'] and not simple['full_libplatform_source_build']
assert simple['source_function_bodies_preserved_except_optional_diagnostic_call']
assert typed['upstream_source_bytes_unchanged'] and not typed['typed_allocation_isolation_implemented']
assert (root / typed['source']).read_bytes() == (root / 'vendor/apple-libmalloc/src/malloc_type_stubs.c').read_bytes()
assert len(simple['export_changes']['added_names']) == 8 and len(typed['export_changes']['added_names']) == 13
assert nounlink['export_changes']['added_names'] == ['_rootless_mkdir_nounlink']
assert typed['base_sha256'] == simple['library_sha256'] and nounlink['base_sha256'] == typed['library_sha256']
for marker in ['SOURCE_SIMPLE_LOG_REAL_ABSENT_SOCKET_ERROR_AND_LAUNCHD_RECONNECT_OK',
    'SIMPLE_LOG_E2E 日志 -77 -9223372036854775808 ffffffffffffffff Z %',
    'SOURCE_SIMPLE_LOG_REAL_FORK_DURING_THREADED_LOGGING_CHILD_PID_AND_DELIVERY_OK',
    'SOURCE_SIMPLE_LOG_ACTUAL_UNIX_DATAGRAM_TRANSPORT_AND_96_CONCURRENT_RECORDS_OK 104']:
    assert marker in log_test['diagnostic']
assert 'SOURCE_TYPED_MALLOC_ALL_13_UPSTREAM_FALLBACK_APIS_AND_256_THREADED_LIFETIMES_OK' in typed_test['diagnostic']
assert 'ORIGINAL_NOUNLINK_NAMED_EXPORT_DIRECT_ERRORS_AND_FILESYSTEM_EFFECTS_OK 0 4' in nounlink_test['diagnostic']
analysis = read('artifacts/rootless-nounlink-native-analysis.json')
assert analysis['flag'] == 0x100000 and not analysis['protection_implemented']
assert digest(analysis['log']) == analysis['log_sha256']
assert digest(analysis['prototype_reference']) == analysis['prototype_reference_sha256']
prefix = 'artifacts/uniform-type-identifiers-native-xcode-nounlink-typed-malloc-simple-log-datavault-user-local-dir-source-libtrace-source-objc-support-'
probe, version = read(prefix + 'showsdks.json'), read(prefix + 'version.json')
integration = read('artifacts/nounlink-source-integration.json')
directory = read('artifacts/native-dirhelper-nounlink-typed-malloc-source-simple-log-probe.json')
for result in [probe, version, integration, directory]:
    assert result['source_simple_log'] == simple and result['typed_malloc'] == typed and result['nounlink_export'] == nounlink
    if 'log' in result: assert digest(result['log']) == result['log_sha256']
    for path, sha in result.get('logs', {}).items(): assert digest(path) == sha
assert version['exit_status'] == 0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert probe['exit_status'] == 255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in probe['diagnostic']
assert not probe['sdk_listing_succeeded'] and integration['runtime_execution_verified']
selected = probe['source_runtime']
assert selected == version['source_runtime'] == integration['selected_runtime'] == directory['source_runtime']
assert selected == read('artifacts/libtrace-directory-progress.json')['selected_runtime']
for item in selected.values(): assert digest(item['path']) == item['sha256']
original_xcode = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original_xcode) == probe['original_xcodebuild_sha256'] == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
assert directory['original_binary_sha256'] == directory['staged_binary_sha256'] == digest('runtime/native-dirhelper/dirhelper')
assert digest(directory['daemon_log']) == directory['daemon_log_sha256']
assert directory['job']['MachServices'] == {'com.apple.bsd.dirhelper': True}
assert directory['exit_status'] == 1 and not directory['runtime_execution_verified']
assert 'NATIVE_DIRHELPER_LOAD_STATUS 0' in directory['diagnostic']
assert 'Symbol not found: _sandbox_container_path_for_audit_token' in directory['daemon_diagnostic']
assert digest('fixtures/hello/lsd-runtime-paths.c') == directory['source_sha256']
assert digest('artifacts/lsd-runtime-paths') == directory['binary_sha256']
patches = []
for folder, files, output in [
    ('libplatform', ['private/os/log_simple_private.h', 'private/os/log_simple_private_impl.h',
     'src/simple/log_simple.c', 'src/simple/log_simple_darling.h', 'src/simple/log_simple_transport.c'], 'darling-platform-simple-log.patch'),
    ('libmalloc', ['src/malloc_type_stubs.c'], 'darling-malloc-type-fallback.patch')]:
    repo = root / 'vendor/darling/src/external' / folder
    parts = [subprocess.check_output(['git', '-C', str(repo), 'diff', '--binary'])]
    for file in files:
        result = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', file], cwd=repo, capture_output=True)
        assert result.returncode == 1, result.stderr
        parts.append(result.stdout)
    path = 'artifacts/' + output; (root / path).write_bytes(b''.join(parts)); patches.append(path)
    subprocess.run(['git', '-C', str(repo), 'apply', '--reverse', '--check', str(root / path)], check=True)
paths = ['artifacts/os-log-simple-source-stage.json', 'artifacts/os-log-simple-source-execution.json',
    'artifacts/typed-malloc-source-stage.json', 'artifacts/typed-malloc-source-execution.json',
    'artifacts/rootless-nounlink-native-analysis.json', 'artifacts/rootless-nounlink-export-stage.json',
    'artifacts/rootless-nounlink-export-execution.json', prefix + 'showsdks.json', prefix + 'version.json',
    'artifacts/nounlink-source-integration.json', 'artifacts/native-dirhelper-nounlink-typed-malloc-source-simple-log-probe.json'] + patches
scripts = ['build-os-log-simple-source.py', 'test-os-log-simple-source.py', 'build-typed-malloc-source.py',
    'test-typed-malloc-source.py', 'analyze-rootless-nounlink-native.py', 'stage-rootless-nounlink-export.py',
    'test-rootless-nounlink-export.py', 'rootless-nounlink-native-loader.c', 'probe-native-dirhelper.py',
    'probe-uniform-type-identifiers-native.py', 'test-objc-source-integration.py', 'record-directory-runtime-progress.py']
destination = 'artifacts/directory-runtime-progress.json'
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), evidence={p: digest(p) for p in paths},
    scripts={'scripts/' + p: digest('scripts/' + p) for p in scripts}, selected_runtime=selected,
    simple_log_source_port=True, actual_104_Unix_datagrams_including_96_threaded_and_one_fork_child_verified=True,
    simple_log_missing_receiver_error_and_explicit_reconnect_verified=True,
    original_13_legacy_allocator_fallback_APIs_and_256_threaded_lifetimes_verified=True,
    native_nounlink_three_argument_ABI_and_four_error_filesystem_differentials_verified=True,
    protected_directory_creation_verified=False, typed_zone_isolation_implemented=False,
    original_directory_service_started=False, original_user_directory_initialization_verified=False,
    original_xcode_version_verified=True, sdk_listing_verified=False,
    UTI_URL_and_database_service_verified=False, full_xcode_build_ready=False, signing_ready=False,
    implementation_form='Apple simple-log source port with actual Unix datagram transport and optional stderr diagnostic; unchanged Apple malloc_type_stubs.c implements 13 real legacy-allocator fallbacks. Both are separately compiled source components, selected through named exports in private libSystem copies. A typed deferred nounlink entry executes unchanged native Sandbox code. Default platform/malloc libraries, original Xcode and service binaries are not replaced.',
    limits=['No logd daemon/persistent unified-log storage claim. The selected fork/thread test does not prove all early-boot, asynchronous-signal or exec/fork contexts.',
        'The real allocator fallback deliberately has no typed xzone isolation; the full platform/malloc libraries were not rebuilt or integrated into their CMake targets.',
        'Native protected mkdir still returns ENOPOLICY. Four nounlink comparisons prove matching errors and side effects, not protected directory creation.',
        'Original dirhelper cannot load sandbox_container_path_for_audit_token. Original lsd database service/full UTI client remain incomplete; original -showsdks lacks CALayerContext.'])
(root / destination).write_text(json.dumps(record, indent=2) + '\n')
state = read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'], goal_status='active', complete=False, primary_report=destination,
    active_build=dict(task='source-simple-log-typed-allocation-and-nounlink', running=False, report=destination),
    latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Source simple-log and 13 upstream allocator fallbacks pass real logging/allocation execution. Original nounlink entry retains ENOPOLICY. Native dirhelper now fails to load sandbox_container_path_for_audit_token; directory initialization and original lsd/UTI database operations remain incomplete. Latest combined 52-image snapshot/policy regression and genuine Xcode version pass; SDK listing still lacks CALayerContext. Full build/archive/signing/export are unverified.')
state['next_work'] = list(dict.fromkeys([
    'Expose/implement the real sandbox_container_path_for_audit_token ABI needed by original Intel dirhelper. Verify the by-value audit-token calling convention, real process identity and native return/error contract; do not synthesize a successful container path. Keep starting the unchanged managed daemon and test actual user-directory creation before combining with lsd.',
] + [s for s in state['next_work'] if not s.startswith('Implement the real _os_log_simple primitive')]))
state['last_verification'] = list(dict.fromkeys(state['last_verification'] + [
    'Apple simple-log source port delivered 104 actual Unix datagrams, including 96 concurrent records and a real fork child; missing receiver fails and explicit launchd reconnect succeeds. All 13 unchanged Apple legacy typed-allocation fallback APIs pass real zones, alignment, zeroing, failure lifetime and 256 threaded lifetimes. Native nounlink has four matching error/side-effect cases. Original dirhelper advances to missing sandbox_container_path_for_audit_token. Version and combined loader/policy execution pass; full xcodebuild remains incomplete.']))
state['latest_validation_reports'] = list(dict.fromkeys(state['latest_validation_reports'] + paths + [destination]))
state.setdefault('source_components', {}).update(simple_log='artifacts/os-log-simple-source-stage.json',
    typed_allocator_fallback='artifacts/typed-malloc-source-stage.json', directory_runtime_progress=destination)
(root / 'artifacts/current-work-state.json').write_text(json.dumps(state, indent=2) + '\n')
print('Recorded source logging/allocator/nounlink execution; original directory service and full Xcode goal remain incomplete')
