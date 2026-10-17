#!/usr/bin/env python3
"""Record verified support APIs separately from unverified UTI semantics."""

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
import hashlib, json

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
stage = read('artifacts/uniform-type-identifiers-native-stage.json')
support = read('artifacts/uti-runtime-support-stage.json')
backtrace = read('artifacts/backtrace-async-native-execution.json')
flags = read('artifacts/featureflags-native-execution.json')
probe = read('artifacts/uniform-type-identifiers-native-xcode-support-showsdks.json')
version = read('artifacts/uniform-type-identifiers-native-xcode-support-version.json')
fixture = read('artifacts/uniform-type-identifiers-native-xcode-support-fixture.json')
for image in stage['images'].values():
    assert digest(image['path']) == image['sha256']
    assert digest(image['reconstruction_report']) == image['reconstruction_report_sha256']
for path, sha in stage['resources'].items(): assert digest(path) == sha
for path, sha in support['source_files'].items(): assert digest(path) == sha
for path, sha in support['libraries'].items(): assert digest(path) == sha
assert support['source_helpers_have_no_initializers_and_only_libSystem_dependency']
assert support['upstream_backtrace_body_unchanged']
for change in support['export_changes']:
    assert change['original_instructions_and_other_bytes_preserved']
    assert not change['provider_entire_namespace_reexported']
for test in [backtrace, flags]:
    assert test['runtime_execution_verified'] and test['stage'] == support
    for path, sha in test['test_files'].items(): assert digest(path) == sha
for path, sha in backtrace['logs'].items(): assert digest(path) == sha
for path, sha in backtrace['binaries'].items(): assert digest(path) == sha
assert digest(flags['log']) == flags['log_sha256']
assert digest(flags['binary']) == flags['binary_sha256']
assert flags['missing_domain_two_defaults_four_threads_verified']
assert not flags['configured_feature_decisions_verified']
assert backtrace['actual_64_swift_tasks_task_ids_and_bounded_frames_verified']
assert backtrace['ordinary_capacity_0_through_64_exact_caller_PC_null_outputs_four_threads_verified']
for result in [probe, version, fixture]:
    assert digest(result['log']) == result['log_sha256']
    assert result['runtime_support'] == support and result['stage'] == stage
assert version['exit_status'] == 0 and 'Xcode 26.6\nBuild version 17F113' in version['diagnostic']
assert probe['exit_status'] == 255 and 'Symbol not found: _OBJC_CLASS_$_CALayerContext' in probe['diagnostic']
assert not probe['sdk_listing_succeeded']
assert fixture['exit_status'] != 0
assert fixture['UTI_functional_execution_verified'] is False
fixture_build = read('artifacts/uniform-type-identifiers-native-fixture-build.json')
assert fixture['fixture_build'] == fixture_build
assert digest(fixture_build['source']) == fixture_build['source_sha256']
assert digest(fixture_build['binary']) == fixture_build['binary_sha256']
for path, sha in fixture_build['logs'].items(): assert digest(path) == sha
assert 'NATIVE_UTI_TYPED_TAG_CONFORMANCE_AND_URL_EXTENSION_OK' not in fixture['diagnostic']
analysis = read('artifacts/uti-native-blocker-analysis.json')
for path, sha in analysis['evidence_logs'].items(): assert digest(path) == sha
tagged = read('artifacts/uniform-type-identifiers-native-tagged-enabled.json')
assert tagged['timed_out_and_killed'] and not tagged['UTI_functional_execution_verified']
assert digest(tagged['log']) == tagged['log_sha256']
selected = probe['source_runtime']
assert selected == version['source_runtime'] == backtrace['selected_runtime'] == flags['selected_runtime']
for item in selected.values(): assert digest(item['path']) == item['sha256']
original = 'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original) == probe['original_xcodebuild_sha256'] == digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
assert digest(support['base']) == support['base_sha256']
assert digest('runtime/rootfs/usr/libexec/darling/usr/lib/libSystem.B.dylib') == read('config/dyld-cache-introspection.json')['libsystem_sha256']
evidence = ['artifacts/uniform-type-identifiers-native-stage.json', 'artifacts/uti-runtime-support-stage.json',
    'artifacts/backtrace-async-native-execution.json', 'artifacts/featureflags-native-execution.json',
    'artifacts/uniform-type-identifiers-native-xcode-support-showsdks.json',
    'artifacts/uniform-type-identifiers-native-xcode-support-version.json',
    'artifacts/uniform-type-identifiers-native-xcode-support-fixture.json',
    'artifacts/uti-native-blocker-analysis.json', 'artifacts/uti-cache-import-analysis.json',
    'artifacts/uniform-type-identifiers-native-fixture-build.json',
    'artifacts/uniform-type-identifiers-native-tagged-enabled.json']
record = dict(checked_at=datetime.now(timezone.utc).isoformat(), evidence={p: digest(p) for p in evidence},
    source_runtime=selected, restored_UTI_exports=267, restored_Swift_overlay_exports=627,
    original_xcode_version_verified=True, source_async_backtrace_execution_verified=True,
    original_featureflags_missing_domain_defaults_and_bridge_verified=True,
    configured_feature_decisions_verified=False, UTI_functional_execution_verified=False,
    current_original_xcode_blocker='_OBJC_CLASS_$_CALayerContext in Darling AppKit versus native QuartzCore',
    independent_UTI_blocker='Native compact tagged NSMethodSignature returned while this profile disables tagged dispatch; captured objc_msgSend crash before main.',
    implementation_form='Paired original Intel UTI images and native feature-flag code are staged separately. The upstream backtrace_async entry plus original frame walker are compiled as a source component. Two small source helpers and libSystem named exports provide lazy backend loading and the async entry; default runtime and Xcode binaries are unchanged. No full objc4/CoreFoundation/AppKit source rebuild.',
    full_xcode_build_ready=False, signing_ready=False)
path = 'artifacts/uti-native-progress.json'
(root / path).write_text(json.dumps(record, indent=2) + '\n')
state = read('artifacts/current-work-state.json')
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
state.update(updated_at=record['checked_at'], goal_status='active', complete=False, primary_report=path,
    latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='Paired original UTI framework/Swift overlay and verified source backtrace_async advance original -showsdks to CALayerContext, a Cocotron AppKit dependency absent in native QuartzCore. Native feature-flag missing-domain/default behavior passes direct/bridge tests. UTI functional fixture crashes before main in compact tagged NSMethodSignature dispatch; UTI semantics, SDK listing, full project build/archive/signing remain unverified.',
    active_build=dict(task='uti-restoration-and-runtime-support-checkpoint', running=False, report=path),
    runtime_changes_this_phase='Independent native UTI pair and feature-flag image; new upstream async-backtrace and lazy flag-loader source components; named exports only in an isolated libSystem copy. No default binary, host package/service or kernel changes.')
state['next_work'] = [
    'Resolve the real CALayerContext dependency between Cocotron AppKit and native QuartzCore. Inspect existing source rendering/layer-context contracts; CAContext is a different class and must not be aliased. Keep headless execution and actual failure semantics; do not invent a successful GUI backend.',
    'Repair the Objective-C tagged-pointer runtime boundary needed by original CoreFoundation NSMethodSignature and UTI. The compact signature factory unconditionally creates an obfuscated tagged object for supported short encodings, while this profile disables tagged dispatch. Trace evidence places the pre-main crash in objc_msgSend at _argInfo: from Foundation protocol metadata. Support the real ABI in Darling source rather than guessing object layout; then pass actual UTType identifier/tag/conformance and URL extension fixture.',
] + [s for s in state['next_work'] if not s.startswith('Restore the original Swift UniformTypeIdentifiers overlay')]
state['last_verification'].append('Native UTI framework 267 exports/5 classes and Swift overlay 627 exports restored; original Xcode advances past URL overlay and async backtrace symbols to Cocotron CALayerContext. Source async backtrace passes caller-PC/capacity/null-output/four-thread tests and 64 real Swift task IDs; original feature flags and lazy bridge pass actual missing-domain/both-default/four-thread checks. UTI functional execution still fails before main in tagged NSMethodSignature dispatch.')
state['latest_validation_reports'] = list(dict.fromkeys(state['latest_validation_reports'] + evidence + [path]))
(root / 'artifacts/current-work-state.json').write_text(json.dumps(state, indent=2) + '\n')
print('Recorded UTI checkpoint; full goal remains active and incomplete')
