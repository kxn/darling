#!/usr/bin/env python3
"""Verify original ASI execution and the next genuine Xcode/Security binding gap."""

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
read=lambda p:json.loads((root/p).read_text())
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
stage_path='artifacts/apple-system-info-native-stage.json';stage=read(stage_path)
execution_path='artifacts/apple-system-info-native-execution.json';execution=read(execution_path)
analysis_path='artifacts/apple-system-info-native-analysis.json';analysis=read(analysis_path)
probe_path='artifacts/apple-system-info-native-xcode-probe.json';probe=read(probe_path)
version_path='artifacts/apple-system-info-native-xcode-version.json';version=read(version_path)
assert digest(stage['framework'])==stage['framework_sha256']==execution['stage']['framework_sha256']
assert digest(stage['reconstruction_report'])==stage['reconstruction_report_sha256']
reconstruction=read(stage['reconstruction_report'])
assert reconstruction['exports']==stage['original_exports_preserved']==29
assert reconstruction['code_analysis']['function_entries']==stage['original_functions_analyzed']==43
assert not reconstruction['redirected_imports'] and not reconstruction['backend_call_overrides']
assert digest('runtime/fullsystem-libraries/'+stage['original']['path'].lstrip('/'))==stage['original']['sha256']
for p,value in stage['staged_resources'].items():assert digest(p)==value
for p,value in stage['original_resources'].items():assert digest(stage['resource_source']+'/'+p)==value
assert stage==probe['native_systeminfo'] and stage['original']==analysis['original']
assert len(analysis['DVT_imports'])==7
assert execution['native_execution_verified'] and execution['exit_status']==0
assert execution['native_scalar_format_cases']==25 and execution['native_current_format_flag_cases']==10
assert execution['original_bundle_and_string_lifetime_verified']
assert not execution['complete_frequency_formatting_verified'] and not execution['hardware_registry_platform_identity_verified']
assert digest('fixtures/hello/apple-system-info-native.m')==execution['test_source_sha256']
assert digest('artifacts/apple-system-info-native')==execution['test_binary_sha256']
assert digest('scripts/test-apple-system-info-native.py')==execution['test_driver_sha256']
assert execution['input_probe_sha256']==digest('artifacts/mobileasset-source-xcode-probe.json')
selected=execution['selected_runtime'];assert len(selected)==7 and selected==probe['source_runtime']==version['selected_runtime']
for item in selected.values():assert digest(item['path'])==item['sha256']
mobile=read('artifacts/mobileasset-source-progress.json')
assert mobile['all_five_client_operation_protocols_verified'] and mobile['actual_protocol_fixture_requests']==348
assert not mobile['remaining_DVT_MobileAsset_API_semantics']
assert probe['source_mobileasset']==read('artifacts/mobileasset-source.json')
assert digest(mobile['source_framework']['path'])==mobile['source_framework']['sha256']
assert probe['exit_status']==255 and not probe['sdk_listing_succeeded']
missing='_SecPolicyCreateAppleExternalDeveloperOptionalExpiry'
assert 'Symbol not found: '+missing in probe['diagnostic']
assert 'Symbol not found: _ASI_' not in probe['diagnostic']
assert version['original_xcode_version_verified'] and version['exit_status']==0
assert version['probe_sha256']==digest(probe_path)
for report in [probe,execution,version,analysis]:assert digest(report['log'])==report['log_sha256']
default='runtime/rootfs/usr/libexec/darling/System/Library/PrivateFrameworks/AppleSystemInfo.framework/Versions/A/AppleSystemInfo'
original_default_hash=read('artifacts/xcode-chained-import-audit.json')['image_sha256'][default]
assert digest(default)==original_default_hash=='2a0614e3bd3b61f5aad6dabe2245465a1f931158ca1a9d99122e2347fa259486'
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
reports=[stage_path,execution_path,analysis_path,probe_path,version_path,'artifacts/mobileasset-source-progress.json']
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=selected,
    evidence={p:digest(p) for p in reports},original_native_ASI_code_and_resources_staged=True,
    preserved_native_exports=29,analyzed_native_functions=43,native_scalar_input_execution_cases=25,
    native_current_format_execution_cases=10,exact_MHz_output_verified=True,
    complete_GHz_number_formatting_verified=False,hardware_platform_identity_verified=False,
    observed_native_CPU_package_count=execution['observed_native_CPU_package_count'],
    observed_native_frequency_scalar=execution['observed_native_frequency_scalar'],
    known_backend_limits=execution['observed_backend_limits'],
    default_ASI_unchanged_sha256=original_default_hash,original_xcodebuild_sha256=digest(original),
    original_xcode_version_verified=True,original_sdk_listing_exit_status=255,current_missing_symbol=missing,
    implementation_form='Complete original Intel AppleSystemInfo reconstructed from the pinned cache, with original bundle resources; no source ASI function or fixed-result CPU-description hook added. Seven source runtime components and source MobileAsset remain selected. Other existing compatibility adapters remain.',
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/apple-system-info-native-progress.json').write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json')
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/uti-native-progress.json':
    print('Preserving the later UTI/runtime-support checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/security-yield-progress.json':
    print('Verified ASI checkpoint; preserved the newer Security/yield work state.')
    raise SystemExit(0)
state.update(updated_at=record['checked_at'],goal_status='active',complete=False,
    primary_report='artifacts/apple-system-info-native-progress.json',latest_implementation_form=record['implementation_form'],
    latest_staged_coreml_and_metal_blocker='All five DVT Pallas clients have source implementations and 348 real protocol-fixture requests. Original AppleSystemInfo is staged with 29 exports and original resources; selected formatter/bundle/lifetime operations execute. Original -showsdks now exits 255 at SecPolicyCreateAppleExternalDeveloperOptionalExpiry in Security; -version passes. ASI GHz formatting and hardware registry/frequency semantics remain incomplete. SDK listing/project build/archive/signing remain incomplete.')
state['next_work']=[
    'Continue genuine xcodebuild from SecPolicyCreateAppleExternalDeveloperOptionalExpiry. Inspect the native signature, option meaning, real policy object ABI and existing Darling Security implementation before writing source code. Existing older SecPolicyCreateAppleExternalDeveloper source has Apple-root pinning, chain/OID/EKU/revocation/key-strength checks; preserve actual certificate-validation semantics. Do not add a policy success stub, fake trusted certificate, broad expiry bypass or guess the boolean meaning from its name.',
    'Resolve existing ASI backend gaps: GHz numeric formatting currently drops frequency; CPU-kind hardware registry returns no identity and native current descriptions use Unknown. Observed guest frequency/package scalars are recorded, but real hardware identity/frequency-unit accuracy and other ASI operations remain unverified.'
]+[s for s in state['next_work'] if not s.startswith(('Continue original xcodebuild at ASI_','Continue genuine xcodebuild from SecPolicy','Resolve existing ASI backend'))]
state['last_verification'].append('Original Intel ASI 29-export/43-function reconstruction with original bundle resources selected privately. Actual formatter executes 25 scalar inputs (including exact 100/500 MHz assertions), ten current-format flags, owned/borrowed lifetime and CopyCurrent composition checks. Native Intel 2 x fallback differs from older Dual resource; GHz numeric rendering remains incomplete and actual CPU kind is Unknown. Genuine -showsdks now reaches SecPolicyCreateAppleExternalDeveloperOptionalExpiry; -version passes; default ASI/original Xcode unchanged.')
state['last_verification']=list(dict.fromkeys(state['last_verification']))
state['source_components'].update(apple_system_info_native=stage_path,apple_system_info_execution=execution_path,
    apple_system_info_native_analysis=analysis_path,apple_system_info_xcode_probe=probe_path,
    apple_system_info_progress='artifacts/apple-system-info-native-progress.json')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+reports+['artifacts/apple-system-info-native-progress.json']))
state['known_scope_limits']=list(dict.fromkeys(state['known_scope_limits']+execution['observed_backend_limits']))
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Verified source Pallas completion and original ASI execution/probe progression; full Xcode goal remains active/incomplete.')
