#!/usr/bin/env python3
"""Validate source-runtime execution and retain the real unresolved Xcode/service failures."""

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
import hashlib, json, plistlib, subprocess

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

# A historical recorder must not replace the newer directory-service checkpoint.
if json.loads((root / 'artifacts/current-work-state.json').read_text()).get('primary_report') in {'artifacts/libtrace-directory-progress.json', 'artifacts/directory-runtime-progress.json', 'artifacts/directory-services-progress.json', 'artifacts/sysdir-metadata-progress.json', 'artifacts/metadata-kernel-progress.json', 'artifacts/mount-container-progress.json'}:
    print('Preserving the later source logging and directory-service checkpoint')
    raise SystemExit(0)
read = lambda p: json.loads((root / p).read_text())
digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
build = read('artifacts/objc-source-build.json')
assert build['full_objc_source_build'] and build['complete_source_files'] == 43
assert build['original_export_count'] == build['source_export_count'] == 770 and not build['missing_original_exports']
assert digest(build['library']) == build['library_sha256']
repo = root / 'vendor/darling/src/external/objc4'
for relative, sha in build['source_files'].items(): assert digest(str((repo / 'runtime' / relative).relative_to(root))) == sha
for path, sha in build['build_inputs'].items(): assert digest(path) == sha
for path, sha in build['compile_input_reports'].items():
    assert digest(path) == sha
    item = read(path)
    for absolute, value in item['inputs'].items(): assert hashlib.sha256(Path(absolute).read_bytes()).hexdigest() == value
assert build['initializer_sections'] == [dict(name='__objc_init_func', size=80, flags=9)]
baseline = read('config/objc-class-enumeration.json')
assert digest(baseline['backend_binary']) == baseline['backend_sha256'] == build['original_runtime_sha256']
layout = read('artifacts/objc-source-layout-analysis.json')
assert layout['object_word_and_class_ABI_preserved'] and layout['upstream_storage_and_accessor_lines_unchanged']
assert layout['layouts']['original'] == [8, 8, 8, 8, 40, 8, 8, 16, 32]
assert layout['layouts']['source'] == [8, 1, 8, 8, 40, 8, 8, 16, 32]
for key in ['source_files', 'compiler_outputs']:
    for path, sha in layout[key].items(): assert digest(path) == sha
tagged = read('artifacts/objc-source-tagged-execution.json')
assert tagged['build'] == build and tagged['runtime_execution_verified']
assert tagged['results']['packaged']['exit_status'] != 0 and tagged['results']['source']['exit_status'] == 0
for result in tagged['results'].values(): assert digest(result['log']) == result['log_sha256']
assert digest('fixtures/hello/objc-source-tagged.m') == tagged['test_source_sha256']
assert digest('artifacts/objc-source-tagged') == tagged['test_binary_sha256']
signatures = read('artifacts/objc-source-signatures-execution.json')
assert signatures['build'] == build and signatures['runtime_execution_verified'] and signatures['exit_status'] == 0
assert digest('fixtures/hello/objc-source-signatures.m') == signatures['test_source_sha256']
assert digest('artifacts/objc-source-signatures') == signatures['test_binary_sha256']
assert digest(signatures['log']) == signatures['log_sha256']
integration = read('artifacts/objc-source-integration.json')
assert integration['source_objc'] == build and integration['runtime_execution_verified']
for path, sha in integration['logs'].items(): assert digest(path) == sha
base = 'artifacts/uniform-type-identifiers-native-xcode-source-objc-support-'
probe, version, fixture = [read(base + suffix + '.json') for suffix in ['showsdks', 'version', 'fixture']]
for result in [probe, version, fixture]:
    assert result['source_objc'] == build and digest(result['log']) == result['log_sha256']
assert version['exit_status'] == 0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert probe['exit_status'] == 255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in probe['diagnostic']
assert not probe['sdk_listing_succeeded'] and not fixture['UTI_functional_execution_verified']
assert fixture['exit_status'] != 0 and 'NATIVE_UTI_PREFERRED_EXTENSION_OK public.plain-text txt\n' in fixture['diagnostic']
assert 'NATIVE_UTI_URL_EXTENSION_OK' not in fixture['diagnostic']
fixture_build = read('artifacts/uniform-type-identifiers-native-fixture-build.json')
assert fixture_build == fixture['fixture_build']
assert digest(fixture_build['source']) == fixture_build['source_sha256']
assert digest(fixture_build['binary']) == fixture_build['binary_sha256']
wait = read('artifacts/uti-source-objc-current-live-stack.json')
assert digest(wait['log']) == wait['log_sha256']
names = [item.get('nearest_symbol', '') for item in wait['frames']]
assert any('appendingPathExtension3for' in name for name in names)
assert '___NSXPCCONNECTION_IS_WAITING_FOR_A_SYNCHRONOUS_REPLY__' in names
assert '__LSCopyServerStore' in names
lsd = read('artifacts/native-lsd-probe.json')
assert lsd['source_objc'] == build and lsd['exit_status'] == 1 and not lsd['UTI_functional_execution_verified']
assert 'NATIVE_LSD_LAUNCHCTL_LOAD_STATUS 0\n' in lsd['diagnostic']
assert '"LastExitStatus" = 139;' in lsd['diagnostic'] and 'NATIVE_LSD_NO_RUNNING_PID_AFTER_START\n' in lsd['diagnostic']
assert lsd['original_binary_sha256'] == lsd['staged_binary_sha256'] == digest('runtime/native-lsd/lsd')
original_job = plistlib.loads((root / 'runtime/recovery/macOS Base System/System/Library/LaunchDaemons/com.apple.lsd.plist').read_bytes())
assert lsd['selected_job']['MachServices'] == original_job['MachServices']
for path, sha in lsd['logs'].items(): assert digest(path) == sha
crash = read('artifacts/native-lsd-crash-stack.json')
assert digest(crash['log']) == crash['log_sha256']
assert crash['frames'][0]['nearest_symbol'] == '_objc_msgSend'
assert crash['frames'][0]['image_sha256'] == build['library_sha256']
assert crash['frames'][1]['nearest_symbol'] == '__os_log_impl'
assert any('currentSchemaVersion' in item.get('nearest_symbol', '') for item in crash['frames'])
archive = read('artifacts/native-lsd-core-archive.json')
assert digest(archive['core']) == archive['core_sha256']
for path, sha in archive['runtime_snapshot'].items(): assert digest(path) == sha
selected = probe['source_runtime']
assert selected == version['source_runtime'] == tagged['source_runtime'] == signatures['selected_runtime'] == integration['selected_runtime'] == lsd['source_runtime']
for item in selected.values(): assert digest(item['path']) == item['sha256']
original = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original) == probe['original_xcodebuild_sha256'] == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
patch = subprocess.check_output(['git', '-C', str(repo), 'diff', '--binary'])
patch_path = root / 'artifacts/darling-objc-source-tagged.patch'
patch_path.write_bytes(patch)
subprocess.run(['git', '-C', str(repo), 'diff', '--check'], check=True)
subprocess.run(['git', '-C', str(repo), 'apply', '--reverse', '--check', str(patch_path)], check=True)
paths = ['artifacts/objc-source-build.json', 'artifacts/objc-source-layout-analysis.json',
    'artifacts/objc-source-tagged-execution.json', 'artifacts/objc-source-signatures-execution.json',
    'artifacts/objc-source-integration.json', base + 'showsdks.json', base + 'version.json', base + 'fixture.json',
    'artifacts/uti-source-objc-current-live-stack.json', 'artifacts/native-lsd-probe.json',
    'artifacts/native-lsd-crash-stack.json', 'artifacts/native-lsd-core-archive.json',
    'artifacts/darling-objc-source-tagged.patch']
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), evidence={p: digest(p) for p in paths},
    selected_runtime=selected, source_objc=build, full_objc_source_build=True,
    upstream_ISA_storage_port=True, object_word_and_class_ABI_preserved=True,
    tagged_basic_extended_19_cases_and_actual_native_tagged_signature_verified=True,
    original_NSInvocation_integer_double_and_struct_return_verified=True,
    combined_loader_snapshot_and_128_policy_objects_verified=True,
    original_xcode_version_verified=True, UTI_identifier_and_preferred_txt_extension_verified=True,
    UTI_URL_extension_conformance_and_database_queries_verified=False,
    original_lsd_managed_job_loaded=True, original_lsd_service_start_succeeded=False,
    original_lsd_startup_crash='Actual core: objc_msgSend from libTrace _os_log_impl, while LaunchServices currentSchemaVersion runs. Formatter/ASL ABI or object lifetime needs investigation; root cause not yet established.',
    implementation_form='Direct Darling objc4 source port of upstream ISA byte storage/accessors; full 43-source Intel build with all 770 old exports. Independently selected through the library path, with tagged dispatch enabled. Packaged defaults, seven earlier source components, and Xcode are unchanged. Original lsd binary and Mach service definitions are used in a temporary managed-job experiment.',
    full_runtime_compatibility=False, full_xcode_build_ready=False, signing_ready=False)
destination = 'artifacts/objc-source-progress.json'
(root / destination).write_text(json.dumps(record, indent=2) + '\n')
state = read('artifacts/current-work-state.json')
state.update(updated_at=record['checked_at'], goal_status='active', complete=False, primary_report=destination,
    active_build=dict(task='objc-source-and-native-lsd-checkpoint', running=False, report=destination),
    latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Full source objc4 repairs the tagged-pointer alignment bug and passes real native method signatures, int/double/struct invocations, loader snapshots, and 128 policy objects. Genuine -version passes; -showsdks remains blocked by Cocotron CALayerContext. Native UTI reaches its real URL implementation but waits for the LaunchServices database; original managed lsd crashes in the libTrace logging path during currentSchemaVersion startup. Full project build/archive/signing remain incomplete.')
state['next_work'] = [
    'Resolve the original Intel lsd startup crash: captured core is in objc_msgSend from libTrace _os_log_impl during LaunchServices currentSchemaVersion logging. Investigate the real formatter callback, ASL/CF object ABI and ownership; retain actual logging, do not disable logs or fake database responses. Original daemon and 13 MachServices are staged in runtime/native-lsd, and actual launchctl load succeeds but the daemon exits 139.',
    'Once original lsd starts and replies, pass the complete original Swift UTI URL-extension, type-conformance and extension/MIME lookup fixture. The actual URL overlay currently enters NSURL URLByAppendingPathExtensionForType -> UTType conformsToType -> LaunchServices database -> synchronous NSXPC wait. The previous pre-main tagged NSMethodSignature crash is repaired by the full source objc4 runtime; identifier and preferred plain-text extension already execute.',
] + [item for item in state['next_work'] if not item.startswith('Repair the Objective-C tagged-pointer runtime boundary')]
state['last_verification'].append('Direct objc4 source port preserves 8-byte object word and 40-byte class layout while removing C++ pointer-alignment assumptions. Full 43-source/770-export runtime passes 19 basic/extended tag cases, actual native tagged signatures, NSInvocation int/double/struct returns, 47-image loader snapshot and 128 concurrent policy objects. Genuine -version passes. UTI URL code now executes and waits on NSXPC; original managed lsd crashes in logging. SDK listing/project build/archive/signing are incomplete.')
state['latest_validation_reports'] = list(dict.fromkeys(state['latest_validation_reports'] + paths + [destination]))
state['known_limits'].append('Full source objc4 has only the selected runtime and native-Foundation execution coverage recorded here. Existing external ObjC enumeration/selector adapters still have packaged-runtime ABI/UUID guards; source-aware migration and wider runtime compatibility are not established.') if 'known_limits' in state else None
(root / 'artifacts/current-work-state.json').write_text(json.dumps(state, indent=2) + '\n')
print('Recorded verified source objc4 progress; full xcodebuild goal remains active')
