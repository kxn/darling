#!/usr/bin/env python3
"""Verify modern Security reply ABI, real typed operators and original Xcode."""

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
from pathlib import Path as _sandbox_Path
import json as _sandbox_json
_sandbox_state = _sandbox_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _sandbox_state.exists() and _sandbox_json.loads(_sandbox_state.read_text()).get('primary_report') in {'artifacts/sandbox-check-progress.json','artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving newer Sandbox source/policy-gap checkpoint; historical recorder skipped')
    raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/typed-new-delete-profile.py'))['profile']()
security=p['source_security_cloud_rpc'];build=security['build'];cpp=p['source_typed_new_delete']
assert build['four_upstream_function_bodies_unchanged'] and build['modern_current_item_protocol_matches_upstream'] and build['result_class_matches_upstream']
assert not build['cloud_backend_implemented'] and not build['full_Security_build']
assert len(build['public_RPCs'])==4 and len(build['public_value_class_exports'])==2
assert security['export_changes']['original_instructions_and_other_bytes_preserved']
assert read('config/security-current-item-native-layout.json')==build['native_result_layout']
assert build['native_result_layout']['instance_size']==24
assert [(v['name'],v['offset']) for v in build['native_result_layout']['ivars']]==[('_persistentRef',8),('_currentItemPointerModificationTime',16)]
for name,sha in build['upstream_source_sha256'].items():
    raw=subprocess.check_output(['git','-C',str(root/'vendor/apple-security'),'show',build['upstream_commit']+':'+name]);assert hashlib.sha256(raw).hexdigest()==sha
assert cpp['original_direct_exports_preserved']==99 and len(cpp['exports'])==4
assert cpp['baseline_relink_only_UUID_differs'] and not cpp['type_partition_isolation_implemented']
old=(root/cpp['base']).read_bytes();control=(root/cpp['baseline_relink']).read_bytes();begin,end=cpp['baseline_UUID_range']
assert len(old)==len(control) and all(a==b or begin<=i<end for i,(a,b) in enumerate(zip(old,control)))
normalizer=runpy.run_path(str(root/'scripts/normalize-macho-weak-bind.py'))
fresh,normalization=normalizer['normalize']((root/cpp['unsorted_control']).read_bytes())
assert fresh==(root/cpp['library']).read_bytes() and normalization==cpp['weak_bind_normalization']
assert normalization['all_symbol_flags_and_bindings_preserved'] and normalization['following_linkedit_payload_preserved_byte_for_byte']
assert normalization['instructions_and_other_payloads_unchanged']
assert normalization['symbol_count']==normalization['binding_count']==9
assert normalization['original_symbol_order']!=sorted(normalization['original_symbol_order'])
assert normalization['normalized_symbol_order']==sorted(normalization['original_symbol_order'])
tests=read('artifacts/security-current-item-test.json');typed=read('artifacts/typed-new-delete-test.json');formatting=read('artifacts/typed-new-delete-to-chars-test.json')
for result in [tests,typed,formatting]:
    assert result['source_runtime']==p['source_runtime'] and result['source_security_cloud_rpc']==security and result['source_typed_new_delete']==cpp
    for key in ['source','binary','log','reference_log']:
        if key in result:assert digest(result[key])==result[key+'_sha256']
    for name,sha in result.get('sources',{}).items():assert digest(name)==sha
    for row in result.get('checks',[]):
        assert digest(row['log'])==row['log_sha256']
        if 'binary' in row:assert digest(row['binary'])==row['binary_sha256']
assert [c['exit_status'] for c in tests['checks']]==[0,0,1,2]
assert 'CONFIGURATION_OK checks=21' in (root/tests['checks'][0]['log']).read_text()
assert 'LOCAL_ARGUMENTS_ERRORS_OK checks=127' in (root/tests['checks'][1]['log']).read_text()
assert 'dispatch_semaphore_wait' in (root/tests['checks'][2]['log']).read_text()
assert 'NSCocoaErrorDomain Code=4099' in (root/tests['checks'][3]['log']).read_text()
assert [c['exit_status'] for c in typed['checks']]==[1,0,1,0]
assert '__ZnwmSt19__type_descriptor_t' in (root/typed['checks'][0]['log']).read_text()
assert 'OWNERSHIP_OK checks=251' in (root/typed['checks'][1]['log']).read_text()
assert 'REPLACEMENT_COUNTS 80 0 40 0' in (root/typed['checks'][2]['log']).read_text()
assert 'REPLACEMENT_COUNTS 40 40 40 40' in (root/typed['checks'][3]['log']).read_text()
assert 'EXCEPTION_OK checks=331' in (root/typed['checks'][3]['log']).read_text()
assert formatting['exit_status']==0 and formatting['finite_cases']==11427 and formatting['native_long_double_narrowing_cases']==15 and formatting['roundtrip_buffer_and_reference_comparison_verified']
names={'project':'typed-cloud-build','version':'typed-cloud-base-version','sdk':'typed-cloud-base-showsdks'}
reports={name:read('artifacts/xcode-service-runtime-'+suffix+'.json') for name,suffix in names.items()}
for name,result in reports.items():
    assert result['source_security_cloud_rpc']==security and result['source_typed_new_delete']==cpp and result['source_runtime']==p['source_runtime']
    assert result['UTI_preflight_verified']
    for key in ['log','script']:assert digest(result[key])==result[key+'_sha256']
    assert '/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild "$@"' in (root/result['script']).read_text()
    assert digest('scripts/runtime-ns.sh')==result['runtime_namespace_script_sha256']
    for job in result['jobs']:assert digest(job['path'])==job['sha256']
    for path,sha in result['service_logs'].items():assert digest(path)==sha
assert reports['project']['exit_status']==255 and reports['project']['use_original_developer_overlay']
assert reports['version']['exit_status']==reports['sdk']['exit_status']==0
assert not reports['version']['use_original_developer_overlay'] and not reports['sdk']['use_original_developer_overlay']
blocker='_SANDBOX_CHECK_ALLOW_APPROVAL';project_text=(root/reports['project']['log']).read_text()
assert 'Symbol not found: '+blocker in project_text and '** BUILD SUCCEEDED **' not in project_text
assert 'Xcode 26.6\nBuild version 17F113' in (root/reports['version']['log']).read_text()
for marker in ['iOS SDKs:','macOS SDKs:','DriverKit SDKs:','visionOS SDKs:','watchOS SDKs:']:assert marker in (root/reports['sdk']['log']).read_text()
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==reports['project']['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
audit=read('artifacts/security-current-item-import-audit.json')
assert digest(audit['consumer'])==audit['consumer_sha256'] and digest(audit['provider'])==audit['provider_sha256']
assert len(audit['security_imports'])==72 and not audit['missing_named_exports'] and not audit['runtime_closure_verified']
history=read('artifacts/security-cloud-rpc-history/manifest.json')
for name,item in history.items():assert digest(item['archived'])==item['sha256']
patches=['artifacts/darling-security-current-item-source.patch','artifacts/darling-libcxx-typed-new-delete-source.patch']
for repo,patch in zip(['vendor/darling/src/external/security','vendor/darling/src/external/libcxx'],patches):
    subprocess.run(['git','apply','--reverse','--check',str(root/patch)],cwd=root/repo,check=True)
    subprocess.run(['git','diff','--check'],cwd=root/repo,check=True)
next_work=[
    'Restore the original SANDBOX_CHECK_ALLOW_APPROVAL flag (native uint32 0x08000000) required by DiskImages2, after identifying the actual selected sandbox_check provider and its behavior for approval requests. Restoring the constant must not be represented as implementing or approving a sandbox policy.',
    'Resolve actual NSXPC/securityd transport: four production Security callbacks still fail to arrive and anonymous listener roundtrip returns 4099. Trace bootstrap, activation and Mach/serialization/interface behavior using controlled service tests; the local value/result tests are not cloud execution.',
    'Continue the unchanged original project through remaining genuine loader/runtime failures, then execute the original Unity/CocoaPods compile/archive/sign/export workflow and integrate the default launcher only after validation.',
]
evidence=patches+['artifacts/security-cloud-rpc-history/manifest.json','artifacts/security-current-item-final-verification.json','artifacts/security-cloud-rpc-build.json','artifacts/security-cloud-rpc-stage.json','artifacts/security-current-item-test.json','artifacts/typed-new-delete-source-build.json','artifacts/typed-new-delete-test.json','artifacts/typed-new-delete-to-chars-test.json','artifacts/security-current-item-import-audit.json','artifacts/security-current-item-next-sandbox-analysis.json','config/security-current-item-native-layout.json']
evidence += ['artifacts/xcode-service-runtime-'+suffix+'.json' for suffix in names.values()]
for result in [tests,typed,formatting,*reports.values()]:
    if 'log' in result:evidence.append(result['log'])
    if 'reference_log' in result:evidence.append(result['reference_log'])
    evidence += [row['log'] for row in result.get('checks',[])]+list(result.get('service_logs',{}))
    if 'script' in result:evidence.append(result['script'])
scripts=['scripts/'+name for name in ['record-security-current-item-progress.py','build-security-cloud-rpc.py','stage-security-cloud-rpc.py','security-cloud-rpc-profile.py','test-security-cloud-rpc.py','build-typed-new-delete.py','typed-new-delete-profile.py','normalize-macho-weak-bind.py','test-typed-new-delete.py','test-typed-new-delete-to-chars.py','probe-xcode-service-runtime.py']]
record={'checked_at':datetime.now(timezone.utc).isoformat(),'previous_report':'artifacts/security-cloud-rpc-progress.json','previous_evidence_archive':'artifacts/security-cloud-rpc-history/manifest.json','previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','source_runtime':p['source_runtime'],'source_security_cloud_rpc':security,'source_typed_new_delete':cpp,'modern_reply_ABI_and_result_class_execution_verified':True,'protocol_layout_and_reexport_checks':21,'local_argument_result_ownership_error_and_legacy_reply_checks':127,'typed_allocation_new_handler_and_exception_checks':251,'replacement_operator_checks':331,'weak_binding_order_negative_control_verified':True,'formatting_finite_cases':11427,'formatting_long_double_cases':15,'service_error_callback_verified':False,'anonymous_NSXPC_fixture_roundtrip_verified':False,'cloud_backend_execution_verified':False,'type_partition_isolation_implemented':False,'original_project_exit':255,'original_project_blocker':blocker,'baseline_version_exit':0,'baseline_sdk_exit':0,'original_xcodebuild_sha256':digest(original),'default_launcher_changed':False,'full_xcode_build_ready':False,'signing_ready':False,'complete':False,'goal_status':'active','next_work':next_work,'evidence':{n:digest(n) for n in dict.fromkeys(evidence)},'scripts':{n:digest(n) for n in scripts},'limits':[
    'Four upstream Security frontend function bodies and the new result class are source-verified. The local fixture tests source behavior with deliberately known test replies/errors; no real cloud/keychain backend or authorization is implemented by these tests. Four production callbacks still time out and anonymous NSXPC transport returns 4099.',
    'The current result uses the real modern three-value reply ABI; the source legacy CF API still replies with two public values. Its legacy server source adapter preserves all existing checks/errors and returns nil for the optional timestamp that backend does not provide. Full Security/server builds and real server execution are not verified. The original older binary endpoint/API remain unchanged in the private component combination.',
    'Four typed C++ operators delegate to the actual replacement-capable legacy allocator, with genuine errors/exceptions. Type partition isolation is absent. The libc++ wrapper is relinked from nine unchanged verified object inputs plus the new component; full libc++ is not rebuilt. Baseline output differs only in the linker-generated UUID.',
    'Weak bind sorting preserves all nine exact bindings and symbol flags, moves the remaining LINKEDIT data byte-for-byte, and changes no instructions or bind target. The unsorted negative control fails replacement counts; normalized output succeeds. The normalization tool handles the tested classic x86_64 Mach-O command set and rejects unsupported layouts/signatures.',
    'Original project initialization advances to a missing sandbox approval flag in DiskImages2. No project compilation, archive, signing or export succeeded. Version/SDK checks exclude optional original package mounts. Earlier notification, eager LoggingSupport binding, Swift disk behavior, sandbox/trust and full-default-launcher gaps remain.',
]}
destination='artifacts/security-current-item-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=p['source_runtime'],latest_xcode_loader_blocker=blocker,latest_staged_coreml_and_metal_blocker=blocker,latest_xcode_runtime_failure='DiskImages2 misses sandbox approval flag; actual Security callbacks time out and anonymous NSXPC returns 4099',latest_xcode_failure_kind='sandbox_flag_and_NSXPC_transport',latest_implementation_form='Source modern Security result/client and compatible three-value protocol; source four typed C++ operators; nine existing wrapper objects retained with exact weak binding table canonicalization. Xcode and default launcher unchanged.',active_build={'task':'modern-current-item-source-ABI-and-typed-C++-allocation','running':False,'report':destination})
old=[x for x in state['next_work'] if not x.startswith(('Implement the genuine SecItemFetchCurrentItemDataAcrossAllDevices','Trace the failed real securityd service/error path'))]
state['next_work']=list(dict.fromkeys(next_work+old))
verification='Modern Security source result ABI: 21 protocol/layout/reexport checks and 127 real frontend/local-fixture checks. Source typed C++ operators: 251 allocator/new_handler/exception checks and 331 replacement checks; unsorted weak-table control fails and normalized table passes. Existing formatting retains 11427 finite and 15 long-double cases. Original project moves to sandbox approval flag (255); baseline version/SDK 0. Production NSXPC failures retained; full goal incomplete.'
state['last_verification']=list(dict.fromkeys(state['last_verification']+[verification]))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]))
state['source_components'].update(security_current_item_progress=destination,typed_new_delete='artifacts/typed-new-delete-source-build.json',typed_new_delete_execution='artifacts/typed-new-delete-test.json',typed_new_delete_formatting='artifacts/typed-new-delete-to-chars-test.json',security_current_item_execution='artifacts/security-current-item-test.json')
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded verified modern Security ABI, source typed allocators, exact weak binding repair, and actual next Xcode gap; goal active')
