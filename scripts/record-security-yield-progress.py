#!/usr/bin/env python3
"""Validate real policy, Linux yield and combined original-Xcode evidence."""

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
from datetime import datetime,timezone
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
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
read=lambda p:json.loads((root/p).read_text());digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
build_path='artifacts/security-policy-source.json';build=read(build_path)
execution_path='artifacts/security-policy-source-execution.json';execution=read(execution_path)
analysis_path='artifacts/security-policy-native-analysis.json';analysis=read(analysis_path)
yield_stage_path='artifacts/pthread-yield-export-stage.json';stage=read(yield_stage_path)
yield_execution_path='artifacts/pthread-yield-export-execution.json';yield_execution=read(yield_execution_path)
integration_path='artifacts/security-yield-integration.json';integration=read(integration_path)
probe_path='artifacts/pthread-yield-export-xcode-probe.json';probe=read(probe_path)
version_path='artifacts/pthread-yield-export-xcode-version.json';version=read(version_path)
assert not build['full_security_source_build'] and build['upstream_function_bodies_unchanged']
assert build['original_security_instructions_unchanged'] and build['original_bytes_outside_header_updates_unchanged']
assert build['original_exports_preserved']==4147 and build['source_exports']==4149
assert build['private_policy_layout_access_added'] is False
assert digest(build['staged_framework'])==build['staged_framework_sha256']==execution['staged_framework_sha256']
assert digest(build['library'])==build['library_sha256']==execution['library_sha256']
for path,value in build['source_files'].items():assert digest(path)==value
assert build['source_files']==execution['source_files']
assert execution['runtime_execution_verified'] and execution['full_typed_option_schema_true_false_verified']
assert execution['real_legacy_policy_differential_verified'] and execution['actual_policy_factory_and_trust_container_integration_verified']
assert execution['owned_lifetime_isolation_and_128_concurrent_objects_per_profile_verified']
assert not execution['certificate_chain_trust_evaluation_verified'] and not execution['full_security_source_rebuild']
assert digest('fixtures/hello/security-external-developer-policy.m')==execution['test_source_sha256']
assert digest('artifacts/security-external-developer-policy')==execution['test_binary_sha256']
assert digest('scripts/test-security-policy-source.py')==execution['test_driver_sha256']
assert digest(execution['certificate_fixture'])==execution['certificate_fixture_sha256']
for path,value in execution['logs'].items():assert digest(path)==value
assert digest(analysis['log'])==analysis['log_sha256']
assert analysis['upstream_commit']==build['source_configuration']['modern_source_commit']
assert analysis['upstream_source_function_body_sha256']==build['source_configuration']['selected_upstream_functions']['SecPolicyCreateAppleExternalDeveloperOptionalExpiry']
assert digest('runtime/fullsystem-libraries/'+analysis['native_provider'].lstrip('/'))==analysis['native_provider_sha256']
assert stage==yield_execution['stage'] and stage['export_changes']['added_names']==['_pthread_yield_np']
assert stage['export_changes']['original_instructions_and_other_bytes_preserved'] and not stage['export_changes']['provider_entire_namespace_reexported']
assert digest(stage['staged_library'])==stage['staged_library_sha256']
assert digest(stage['base'])==stage['base_sha256']==read('artifacts/dyld-cache-introspection.json')['libsystem_stage_sha256']
assert digest(stage['provider'])==stage['provider_sha256']==read('artifacts/foundation-libc-compat.json')['library_sha256']
assert digest(stage['provider_source'])==stage['provider_source_sha256']
assert stage['provider_has_no_initializers'] and stage['provider_dependencies']==['/usr/lib/libSystem.B.dylib']
assert yield_execution['baseline_export_absence_verified'] and yield_execution['real_existing_helper_resolved']
assert yield_execution['exact_main_thread_Linux_sched_yield_syscalls_between_markers']==256
assert yield_execution['minimum_total_Linux_sched_yield_syscalls']>=1280 and yield_execution['all_main_thread_yields_succeeded']
assert digest('fixtures/hello/pthread-yield-export.c')==yield_execution['test_source_sha256']
assert digest('artifacts/pthread-yield-export')==yield_execution['test_binary_sha256']
assert digest('scripts/test-pthread-yield-export.py')==yield_execution['test_driver_sha256']
for path,value in yield_execution['backend_source_files'].items():assert digest(path)==value
for path,value in yield_execution['logs'].items():assert digest(path)==value
selected=execution['selected_runtime']
assert len(selected)==7 and selected==yield_execution['selected_runtime']==integration['selected_runtime']==probe['source_runtime']==version['selected_runtime']
for item in selected.values():assert digest(item['path'])==item['sha256']
assert integration['existing_snapshot_images_UUID_segments_load_unload_and_rights_verified']
assert integration['complete_source_policy_schema_and_128_concurrent_objects_verified']
assert integration['original_xcode_version_verified'] and version['original_xcode_version_verified'] and version['exit_status']==0
for path,value in integration['logs'].items():assert digest(path)==value
assert integration['input_probe_sha256']==version['probe_sha256']==digest(probe_path)
assert probe['source_security_policy']==build and probe['pthread_yield_export']==stage
missing='_$s10Foundation3URLV22UniformTypeIdentifiersE22appendingPathExtension3forAcD6UTTypeV_tF'
assert probe['exit_status']==255 and not probe['sdk_listing_succeeded'] and 'Symbol not found: '+missing in probe['diagnostic']
assert '_SecPolicyCreateAppleExternalDeveloperOptionalExpiry' not in probe['diagnostic'] and '_pthread_yield_np' not in probe['diagnostic']
for record in [probe,version]:assert digest(record['log'])==record['log_sha256']
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
assert digest(build['source_configuration']['base'])==build['source_configuration']['base_sha256']
assert digest('runtime/rootfs/usr/libexec/darling/usr/lib/libSystem.B.dylib')==read('config/dyld-cache-introspection.json')['libsystem_sha256']
repo=root/'vendor/darling/src/external/security'
paths=['OSX/sec/Security/SecPolicyExternalDeveloper.c','OSX/sec/Security/CMakeLists.txt','trust/headers/SecPolicyPriv.h']
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary','--',*paths])
for path in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','--',*paths],text=True).splitlines():
    result=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',path],cwd=repo,stdout=subprocess.PIPE)
    assert result.returncode==1;patch+=result.stdout
patch_path='artifacts/darling-security-external-developer-policy.patch';(root/patch_path).write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(root/patch_path)],check=True)
reports=[build_path,execution_path,analysis_path,yield_stage_path,yield_execution_path,integration_path,probe_path,version_path,patch_path,
    'artifacts/security-policy-source-xcode-probe.json','artifacts/apple-system-info-native-progress.json']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),evidence={p:digest(p) for p in reports},source_runtime=selected,
    full_security_source_rebuild=False,unmodified_upstream_constructor_and_helper_bodies=12,
    original_security_exports_preserved=4147,existing_security_instructions_unchanged=True,
    policy_schema_option_counts=[18,15],real_policy_and_trust_container_integration_verified=True,
    policy_concurrent_objects_per_profile=128,policy_profiles_verified=['legacy','native','combined_yield_profile'],
    certificate_chain_trust_evaluation_verified=False,modern_trust_check_enforcement_verified=False,
    real_Linux_main_thread_yield_syscalls=256,total_observed_completed_Linux_yield_syscalls=yield_execution['minimum_total_Linux_sched_yield_syscalls'],
    source_kernel_yield_backend_verified=True,original_Xcode_and_default_Security_libSystem_unchanged=True,
    original_xcode_version_verified=True,original_sdk_listing_exit_status=255,current_missing_symbol=missing,
    next_provider='/usr/lib/swift/libswiftUniformTypeIdentifiers.dylib',
    implementation_form='Selected upstream policy constructor/helper source is integrated into Darling and built as a separate component, reexported by an isolated original Security image. Existing Security code and all old exports remain. One named libSystem export points at the existing real yield helper. This is not a full Security/framework or pthread rebuild; existing external adapters remain.',
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/security-yield-progress.json').write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json')
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/uti-native-progress.json':
    print('Preserving the later UTI/runtime-support checkpoint')
    raise SystemExit(0)
state.update(updated_at=record['checked_at'],goal_status='active',complete=False,primary_report='artifacts/security-yield-progress.json',
    latest_implementation_form=record['implementation_form'],
    active_build=dict(task='security-policy-and-yield-integration-finished',running=False,report='artifacts/security-yield-progress.json'),
    runtime_changes_this_phase='Added the upstream constructor/helper component to Darling Security source and selected isolated Security/libSystem export additions. Packaged defaults, original Xcode and all seven existing source runtime binaries remain unchanged. No host package installation, service or kernel-module changes.',
    latest_staged_coreml_and_metal_blocker='The source optional-expiry developer-policy constructor and named pthread yield export are verified in the combined seven-source/native-framework profile. Original -showsdks now exits 255 at the Swift UniformTypeIdentifiers overlay Foundation.URL.appendingPathExtension(for: UTType) symbol; -version and real snapshot/policy regressions pass. Full SDK listing/project build/archive/signing remain incomplete.')
state['next_work']=[
    'Restore the original Swift UniformTypeIdentifiers overlay URL.appendingPathExtension(for: UTType), matching the actual native Foundation.URL and UniformTypeIdentifiers.UTType ABI. Native overlay SHA256 is 7b0dafab8b75bf8179a0c938b4ade797548cf42a5cfec5912c63f4b1cf6e9b2c and it depends on the UniformTypeIdentifiers framework plus existing Swift/Foundation modules. Neither UTI framework nor overlay is staged in the current 30-library profile. Preserve genuine preferred-filename-extension/type behavior; do not return the input URL or invent an extension/layout.',
    'Verify actual certificate-chain trust evaluation and modern check enforcement in the existing Security/trustd backend, particularly duplicate/unparseable extensions and signature/key/expiry failures. Current tests prove the exact policy option schema, real object factory and SecTrust container integration, not certificate authentication. The full Security source framework has not been rebuilt.'
]+[s for s in state['next_work'] if not s.startswith(('Continue genuine xcodebuild from SecPolicy','Restore the original Swift UniformTypeIdentifiers','Verify actual certificate-chain trust'))]
state['last_verification'].append('Ported unchanged Apple optional-expiry policy constructor plus 11 helper bodies into Darling source and selected a separate component. True/false typed option schemas (18/15 entries), real old-policy differential, real certificate parsing/SecTrust container, lifetimes and 128 concurrent objects per legacy/native/combined profile passed. Original Security 4147 export payloads and code preserved; only new constructor reexport/existing hidden getter visibility added. Named pthread yield export has 256 exact successful main-thread Linux sched_yield calls and eight-worker execution via source kernel. Combined snapshot and original version passed; -showsdks now reaches Swift UTI URL extension. Certificate trust evaluation and full CI are incomplete.')
state['last_verification']=list(dict.fromkeys(state['last_verification']))
state['source_components'].update(security_policy=build_path,security_policy_execution=execution_path,security_policy_native_analysis=analysis_path,
    security_policy_xcode_probe='artifacts/security-policy-source-xcode-probe.json',pthread_yield_export=yield_stage_path,
    pthread_yield_execution=yield_execution_path,security_yield_integration=integration_path,security_yield_xcode_probe=probe_path,
    security_yield_progress='artifacts/security-yield-progress.json')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+reports+['artifacts/security-yield-progress.json']))
state['known_scope_limits']=list(dict.fromkeys(state['known_scope_limits']+[
    'Only the selected Security policy constructor component is compiled from source; original Security code is reused with export metadata additions. Exact policy construction/trust-container tests do not establish actual certificate-chain evaluation or enforcement of all modern flags by the old trust backend.',
    'The current original SDK listing fails on the Swift UTI URL extension; complete preserved Xcode/Unity/CocoaPods build, archive, signing and export are unverified.']))
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Verified policy construction, actual Linux yielding and combined Xcode progression; full goal remains active/incomplete.')
