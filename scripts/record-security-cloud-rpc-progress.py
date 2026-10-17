#!/usr/bin/env python3
"""Record actual Security client source progress and retained transport failures."""

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
from pathlib import Path as _current_Path
import json as _current_json
_current_state = _current_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _current_state.exists() and _current_json.loads(_current_state.read_text()).get('primary_report') in {'artifacts/security-current-item-progress.json','artifacts/sandbox-check-progress.json','artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving newer current-item/typed-operator checkpoint; historical recorder skipped')
    raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
p=runpy.run_path(str(root/'scripts/security-cloud-rpc-profile.py'))['profile']()
stage=p['source_security_cloud_rpc'];build=stage['build']
assert build['three_upstream_function_bodies_unchanged'] and build['three_upstream_protocol_declarations_unchanged']
assert build['source_client_endpoint_build'] and not build['full_Security_build'] and not build['cloud_backend_implemented']
assert not build['OCTAGON_backend_enabled'] and build['native_secd_xpc_server_offset']==0x288
for name,sha in build['upstream_source_sha256'].items():
    raw=subprocess.check_output(['git','-C',str(root/'vendor/apple-security'),'show',build['upstream_commit']+':'+name])
    assert hashlib.sha256(raw).hexdigest()==sha
assert stage['export_changes']['original_instructions_and_other_bytes_preserved']
assert stage['export_changes']['added_names']==build['public_RPCs']
undefined=subprocess.check_output(['llvm-nm-19',str(root/build['library'])],text=True)
assert re.search(r'\bU _gSecurityd$',undefined,re.M) # no replacement global
assert 'sec/Security/SecItemCloudRPC.m' in (root/'vendor/darling/src/external/security/OSX/CMakeLists.txt').read_text()
for name in build['public_RPCs']:assert name in (root/'vendor/darling/src/external/security/Security.exp-in').read_text().splitlines()
tests=read('artifacts/security-cloud-rpc-test.json')
assert tests['source_security_cloud_rpc']==stage and tests['source_runtime']==p['source_runtime']
for key in ['source','binary']:assert digest(tests[key])==tests[key+'_sha256']
assert [c['mode'] for c in tests['checks']]==['configuration','local','unavailable','roundtrip']
assert [c['exit_status'] for c in tests['checks']]==[0,0,1,2]
logs=[]
for row in tests['checks']:
    assert digest(row['log'])==row['log_sha256'];logs.append((root/row['log']).read_text())
assert 'SECURITY_CLOUD_RPC_CONFIGURATION_OK checks=14' in logs[0]
assert 'SECURITY_CLOUD_RPC_LOCAL_ARGUMENTS_ERRORS_OK checks=45' in logs[1]
assert 'dispatch_semaphore_wait' in logs[2] and 'FAIL line=' in logs[2]
assert 'NSCocoaErrorDomain Code=4099' in logs[3] and 'TRANSPORT_ERROR' in logs[3]
reports={name:read('artifacts/xcode-service-runtime-cloud-'+suffix+'.json') for name,suffix in [('build','build'),('version','base-version'),('sdk','base-showsdks')]}
for name,data in reports.items():
    assert data['source_security_cloud_rpc']==stage and data['source_runtime']==p['source_runtime']
    assert data['UTI_preflight_verified']
    for key in ['log','script']:assert digest(data[key])==data[key+'_sha256']
    assert '/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild "$@"' in (root/data['script']).read_text()
    assert digest('scripts/runtime-ns.sh')==data['runtime_namespace_script_sha256']
    for job in data['jobs']:assert digest(job['path'])==job['sha256']
    for path,sha in data['service_logs'].items():assert digest(path)==sha
assert reports['version']['exit_status']==reports['sdk']['exit_status']==0
assert not reports['version']['use_original_developer_overlay'] and not reports['sdk']['use_original_developer_overlay']
assert 'Xcode 26.6\nBuild version 17F113' in (root/reports['version']['log']).read_text()
sdk=(root/reports['sdk']['log']).read_text()
for marker in ['iOS SDKs:','macOS SDKs:','DriverKit SDKs:','visionOS SDKs:','watchOS SDKs:']:assert marker in sdk
project=reports['build'];text=(root/project['log']).read_text()
assert project['exit_status']==255 and project['use_original_developer_overlay']
blocker='_SecItemFetchCurrentItemDataAcrossAllDevices'
assert 'Symbol not found: '+blocker in text
assert 'Symbol not found: _SecItemUnsetCurrentItemsAcrossAllDevices' not in text
assert '** BUILD SUCCEEDED **' not in text
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==project['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
patch='artifacts/darling-security-cloud-rpc-source.patch'
subprocess.run(['git','apply','--reverse','--check',str(root/patch)],cwd=root/'vendor/darling/src/external/security',check=True)
subprocess.run(['git','diff','--check'],cwd=root/'vendor/darling/src/external/security',check=True)
evidence=['artifacts/mdns-source-progress.json','artifacts/security-cloud-rpc-build.json','artifacts/security-cloud-rpc-stage.json','artifacts/security-cloud-rpc-test.json',patch]
evidence += ['artifacts/xcode-service-runtime-cloud-'+suffix+'.json' for suffix in ['build','base-version','base-showsdks']]
evidence += [c['log'] for c in tests['checks']]
for data in reports.values():evidence += [data['log'],data['script']]+list(data['service_logs'])+[j['path'] for j in data['jobs']]
scripts=['scripts/'+name for name in ['build-security-cloud-rpc.py','stage-security-cloud-rpc.py','security-cloud-rpc-profile.py','test-security-cloud-rpc.py','probe-xcode-service-runtime.py','record-security-cloud-rpc-progress.py']]
next_work=[
    'Implement the genuine SecItemFetchCurrentItemDataAcrossAllDevices client and SecItemCurrentItemData result class from the pinned Apple source. Update its three-argument reply protocol and allowed error index together; the old legacy method has only two reply arguments. Preserve the existing public legacy API contract when integrating full Security.',
    'Trace the failed real securityd service/error path and anonymous NSXPC fixture. Current production API callback test times out; anonymous NSXPC returns actual error 4099. Determine bootstrap, activation, Mach transport, serialization and interface causes before changing semantics. The libxpc activation error_out path currently releases ports without completing activation or delivering an event; this is a source candidate, not yet a verified cause.',
    'Continue the unchanged original Xcode project after the next genuine loader/runtime fix, then Unity/CocoaPods compilation, archive, signing and export. No success output, receipts, cloud policy or trust result may be fabricated.',
]
record={'checked_at':datetime.now(timezone.utc).isoformat(),'previous_report':'artifacts/mdns-source-progress.json','previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','source_runtime':p['source_runtime'],'source_security_cloud_rpc':stage,'upstream_function_bodies_unchanged':True,'protocol_configuration_checks':14,'local_argument_result_and_error_checks':45,'service_error_callback_verified':False,'anonymous_NSXPC_fixture_roundtrip_verified':False,'cloud_backend_execution_verified':False,'original_project_exit':255,'original_project_blocker':blocker,'baseline_version_exit':0,'baseline_sdk_exit':0,'default_launcher_changed':False,'original_xcodebuild_sha256':digest(original),'full_xcode_build_ready':False,'signing_ready':False,'goal_status':'active','complete':False,'next_work':next_work,'evidence':{n:digest(n) for n in dict.fromkeys(evidence)},'scripts':{n:digest(n) for n in scripts},'limits':[
    'Three actual Apple client function bodies and declarations are unchanged, with modern class allowlists in Darling source. The endpoint component is independently compiled with namespaced class/protocol/helper names to coexist with the original legacy endpoint; it shares the genuine native gSecurityd and uses real NSXPC. It does not interpose the existing endpoint or implement a cloud/keychain backend.',
    'The local fixture deliberately implements only test methods with known test results/errors. It proves frontend argument/result/error forwarding and native global ABI selection, not cloud service execution or authorization. Protocol and named reexport checks execute; actual service callback and anonymous transport tests fail and are retained.',
    'Original project initialization moves beyond the three missing exports and stops on another genuine Security API. Compilation, archive, signing and export remain incomplete. Version and SDK checks use the library-only profile without the optional original package mounts.',
    'Full Darling/Security integration is not built or verified. The 12-image and source-runtime work from the previous checkpoint remains a dependency with its recorded limits, including eager LoggingSupport binding, notifications, Swift disk operations, sandbox and trust gaps.',
]}
destination='artifacts/security-cloud-rpc-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=p['source_runtime'],latest_xcode_loader_blocker=blocker,latest_staged_coreml_and_metal_blocker=blocker,latest_xcode_runtime_failure='Original project missing '+blocker+'; production Security callback probe times out and anonymous NSXPC fixture invalidates (4099)',latest_xcode_failure_kind='Security_client_API_and_NSXPC_transport',latest_implementation_form=record['limits'][0],active_build={'task':'source-Security-cloud-RPC-client-and-protocol','running':False,'report':destination})
old=[x for x in state['next_work'] if not x.startswith('Integrate genuine modern Security client RPC functions')]
state['next_work']=list(dict.fromkeys(next_work+old))
verification='Three unchanged Apple Security RPC frontend bodies, updated source protocol and class allowlists built with the real source NSXPC client. Protocol/reexport/native-global checks 14 and local forwarding checks 45 pass. Actual service error callback times out; anonymous fixture fails with 4099. Original project moves to missing SecItemFetchCurrentItemDataAcrossAllDevices (255); baseline version/SDK remain 0. No complete build or signing.'
state['last_verification']=list(dict.fromkeys(state['last_verification']+[verification]))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]))
state['source_components'].update(security_cloud_rpc='artifacts/security-cloud-rpc-build.json',security_cloud_rpc_execution='artifacts/security-cloud-rpc-test.json',security_cloud_rpc_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded source RPC client/protocol progress, real transport failures and next original project API gap; goal active')
