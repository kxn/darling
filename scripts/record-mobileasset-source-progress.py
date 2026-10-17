#!/usr/bin/env python3
"""Check source/runtime/wire evidence and record the next genuine Xcode blocker."""

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
build_path='artifacts/mobileasset-source.json';build=read(build_path)
execution_path='artifacts/mobileasset-pallas-source.json';execution=read(execution_path)
probe_path='artifacts/mobileasset-source-xcode-probe.json';probe=read(probe_path)
version_path='artifacts/mobileasset-source-xcode-version.json';version=read(version_path)
analysis_path='artifacts/mobileasset-pallas-native-analysis.json';analysis=read(analysis_path)
callers_path='artifacts/mobileasset-dvt-callers.json';callers=read(callers_path)
assert build['full_framework_source_build'] and build['complete_source_files']==14
assert build['runtime_execution_verified'] and execution['runtime_execution_verified']
assert build['framework']==execution['framework']
assert digest(build['framework'])==build['framework_sha256']==execution['framework_sha256']
assert digest(build['baseline'])==build['baseline_sha256']
assert build['original_exports_preserved']==75 and build['source_exports']==82
for p,value in build['source_files'].items():assert digest(p)==value
assert execution['source_files']==build['source_files']
assert execution['test_source_sha256']==digest('fixtures/hello/mobileasset-pallas.m')
assert execution['test_binary_sha256']==digest('artifacts/mobileasset-pallas')
assert execution['test_driver_sha256']==digest('scripts/test-mobileasset-source.py')
assert execution['native_analysis_sha256']==digest(analysis_path)
for path,value in execution['logs'].items():assert digest(path)==value
for field in ['actual_named_xpc_transport_verified','absent_service_is_failure_verified',
    'boolean_and_signed_64bit_status_independent_verified','legacy_and_original_foundation_verified']:assert execution[field]
assert execution['requests_per_mode']==174 and execution['concurrent_threads_per_mode']==8
for path,value in execution['tested_files'].items():assert digest(path)==value
for field in ['all_five_DVT_operations_and_legacy_aliases_verified','string_return_utf8_autorelease_lifetime_verified',
    'url_class_validation_and_nil_clear_verified','connection_interruption_retry_execution_verified',
    'retry_limit_execution_verified']:assert execution[field]
assert not execution['real_Apple_daemon_interoperation_verified'] and not execution['MobileAsset_download_daemon_implemented']
selected=execution['selected_runtime'];assert len(selected)==7
assert selected==probe['source_runtime']==version['selected_runtime']
for item in selected.values():assert digest(item['path'])==item['sha256']
assert probe['source_mobileasset']==build
assert probe['exit_status']==255 and not probe['sdk_listing_succeeded']
assert 'Symbol not found: _ASI_GetCurrentCPUDescriptionWithFormat' in probe['diagnostic']
assert not any('Symbol not found: '+symbol in probe['diagnostic'] for symbol in callers['required_functions'])
assert version['original_xcode_version_verified'] and version['exit_status']==0
assert version['probe_sha256']==digest(probe_path)
for record in [probe,version,analysis,callers]:assert digest(record['log'])==record['log_sha256']
assert digest('runtime/fullsystem-libraries/'+analysis['provider'].lstrip('/'))==analysis['provider_sha256']
assert digest(callers['original_DVTFoundation'])==callers['original_DVTFoundation_sha256']
assert digest(callers['intel_slice'])==callers['intel_slice_sha256'] and callers['intel_slice_matches_original']
assert len(callers['required_functions'])==5
assert set(analysis['operations'].values())=={9,10,20,32,33}
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==probe['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
repo=root/'vendor/darling';relative='src/private-frameworks/MobileAsset'
patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary','--',relative])
for p in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard','--',relative],text=True).splitlines():
    result=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',p],cwd=repo,stdout=subprocess.PIPE)
    assert result.returncode==1;patch+=result.stdout
patch_path='artifacts/darling-mobileasset-pallas.patch';(root/patch_path).write_bytes(patch)
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(root/patch_path)],check=True)
reports=[build_path,execution_path,probe_path,version_path,analysis_path,callers_path,
    'artifacts/mobileasset-xpc-native-analysis.json',patch_path,'artifacts/libdyld-source-progress.json']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),evidence={p:digest(p) for p in reports},
    source_runtime=selected,complete_source_framework_build=True,
    source_framework=dict(path=build['framework'],sha256=build['framework_sha256']),
    actual_protocol_fixture_requests=348,actual_concurrent_protocol_fixture_requests=256,
    real_Apple_service_daemon_implemented=False,original_xcode_version_verified=True,
    original_sdk_listing_exit_status=255,current_missing_symbol='_ASI_GetCurrentCPUDescriptionWithFormat',
    remaining_DVT_MobileAsset_API_semantics=[],all_five_client_operation_protocols_verified=True,
    implementation_form='Complete Darling source framework plus existing seven source runtime components, selected by per-invocation framework path. All five DVT Pallas clients use real named XPC transport, not hooks or fixed-result stubs. Audience string ownership and true connection-interruption retry/limit are tested. Other external compatibility adapters remain.',
    limitations=build['known_limits']+[
        'Positive replies came from a separate test protocol server over real Mach/XPC, not the original Apple daemon.',
        'Tests exercise a controlled protocol server, not daemon authorization, catalog or download semantics.'],
    full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/mobileasset-source-progress.json').write_text(json.dumps(report,indent=2)+'\n')
state=read('artifacts/current-work-state.json')
if state.get('primary_report') == 'artifacts/objc-source-progress.json':
    print('Preserving the later source objc4 checkpoint')
    raise SystemExit(0)
if state.get('primary_report')=='artifacts/uti-native-progress.json':
    print('Preserving the later UTI/runtime-support checkpoint')
    raise SystemExit(0)
if state.get('primary_report') in {'artifacts/apple-system-info-native-progress.json','artifacts/security-yield-progress.json'}:
    print('Verified MobileAsset checkpoint; preserved the newer AppleSystemInfo work state.')
    raise SystemExit(0)
state.update(updated_at=report['checked_at'],goal_status='active',complete=False,
    primary_report='artifacts/mobileasset-source-progress.json',
    latest_staged_coreml_and_metal_blocker='Seven source runtime components plus complete source MobileAsset pass original xcodebuild -version. All five DVT Pallas clients have source implementations and real transport tests. Original -showsdks now exits 255 at ASI_GetCurrentCPUDescriptionWithFormat in AppleSystemInfo. SDK listing/project build/archive/signing remain incomplete.',
    latest_implementation_form=report['implementation_form'])
state['next_work']=[
    'Continue original xcodebuild at ASI_GetCurrentCPUDescriptionWithFormat in AppleSystemInfo. DVT imports seven ASI operations; inspect complete native formatter, bundle/localization resources and actual hardware-query backends. Do not return a fabricated CPU description or treat the existing generic ASI stubs as implemented.',
    'Resolve the old libxpc lookup/activation race when a named service disappears between bootstrap lookup and activation. Pallas peer teardown/retry-success and two-attempt failure-limit have real positive execution tests; the initial activation race remains.'
]+[s for s in state['next_work'] if not s.startswith(('Implement actual MobileAsset Pallas','Complete the four remaining DVT MobileAsset','Resolve the old libxpc','Continue original xcodebuild at ASI_'))]
state['last_verification'].append('All five DVT Pallas clients plus default/internal aliases are implemented in complete source MobileAsset (14 files, 75 old exports retained, 82 total). Two Foundation profiles passed 348 actual cross-process requests including 256 concurrent requests, signed 64-bit errors, normalized 8-bit setter inputs, UTF-8 string ownership/lifetime, NSURL validation and nil reset. Actual peer teardown/retry-success and two-attempt limit passed. Original -version passes; -showsdks now reaches ASI_GetCurrentCPUDescriptionWithFormat.')
state['source_components'].update(mobileasset=build_path,mobileasset_pallas_execution=execution_path,
    mobileasset_native_protocol=analysis_path,mobileasset_DVT_callers=callers_path,
    source_mobileasset_xcode_probe=probe_path,mobileasset_progress='artifacts/mobileasset-source-progress.json')
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+reports+['artifacts/mobileasset-source-progress.json']))
state['known_scope_limits']=[s for s in state['known_scope_limits'] if not s.startswith('Source MobileAsset currently implements')]
state['known_scope_limits'].append('Source MobileAsset implements five DVT Pallas clients and selected default/internal aliases; other APIs remain generic legacy stubs. No asset catalog/download/install daemon or positive original Apple daemon proof. Initial lookup/activation race remains; peer-teardown retry and limit are tested.')
state['last_verification']=list(dict.fromkeys(state['last_verification']))
state['known_scope_limits']=list(dict.fromkeys(state['known_scope_limits']))
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Verified real source MobileAsset Pallas transport and genuine Xcode progression; full goal remains active/incomplete.')
