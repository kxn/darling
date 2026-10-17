#!/usr/bin/env python3
"""Validate source/runtime evidence without promoting diagnostic execution to CI success."""

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
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
state_path=root/'artifacts/current-work-state.json'
if state_path.exists() and json.loads(state_path.read_text()).get('primary_report')=='artifacts/coreutils-quarantine-progress.json':
    print('Preserving the newer CoreUtils/Quarantine checkpoint');raise SystemExit(0)
p=runpy.run_path(str(root/'scripts/pid-generation-source-profile.py'))['profile']()
runtime=p['source_runtime']
for item in runtime.values():assert digest(item['path'])==item['sha256']
assert digest('runtime/darlingserver-source-build/darlingserver/darlingserver')=='ae78babd377dd542788f321752b11e9dea6413ee49d1009f00df825fdd9efd6b'
assert p['source_expected_access']['original_direct_exports_preserved']==103
assert len(p['source_expected_access']['added_exports'])==4 and not p['source_expected_access']['full_libcxx_build']
assert p['source_sandbox_checks']['complete_source_files']==3
assert p['source_sandbox_policy']['audit_PID_version_uses_fork_exec_counter']
assert not p['source_sandbox_policy']['profile_application_implemented']
assert not p['source_sandbox_policy']['sandbox_approval_grants_implemented']
evidence=[]
def add(n):
    assert (root/n).is_file(),n
    evidence.append(n)
def checked_test(name,marker):
    data=read(name);assert data['source_runtime']==runtime
    assert data['exit_status']==0
    for key in ['source','binary','log']:assert digest(data[key])==data[key+'_sha256'];add(data[key])
    assert marker in (root/data['log']).read_text()
    add(name);return data
generation=checked_test('artifacts/process-generation-source-test.json','checks=106 iterations=4')
assert generation['libproc_and_audit_fork_exec_generation_verified']
sandbox=checked_test('artifacts/sandbox-policy-generation-source-test.json','checks=95')
assert sandbox['registered_unconfined_query_execution_verified'] and not sandbox['profile_application_verified']
cpp=read('artifacts/pid-generation-cpp-regression.json');add('artifacts/pid-generation-cpp-regression.json')
assert cpp['source_runtime']==runtime and [row['exit_status'] for row in cpp['checks']]==[0,0,0,0]
for name,sha in cpp['sources'].items():assert digest(name)==sha;add(name)
for row in cpp['checks']:
    for key in ['binary','log']:assert digest(row[key])==row[key+'_sha256'];add(row[key])
assert 'checks=3215 iterations=128' in (root/cpp['checks'][0]['log']).read_text()
assert 'checks=251' in (root/cpp['checks'][1]['log']).read_text()
assert 'checks=331' in (root/cpp['checks'][2]['log']).read_text()
assert cpp['roundtrip_buffer_and_reference_comparison_verified'] and cpp['finite_cases']==11427
assert digest(cpp['reference_log'])==cpp['reference_log_sha256'];add(cpp['reference_log'])
chained=read('artifacts/pid-generation-cpp-chained-replacements-failure.json')
assert chained['exit_status']==1 and not chained['resolved']
for key in ['binary','log']:assert digest(chained[key])==chained[key+'_sha256'];add(chained[key])
add('artifacts/pid-generation-cpp-chained-replacements-failure.json')
for n in ['artifacts/expected-access-source-build.json','artifacts/expected-access-source-test.json','artifacts/expected-access-old-headers-compile.json','config/expected-access-native-abi.json','artifacts/sandbox-check-source-build.json','artifacts/sandbox-policy-source-build.json','artifacts/pid-generation-kernel-source-build.json','artifacts/pid-generation-source-stage.json','artifacts/mount-path-kernel-frozen-source-build.json']:add(n)
frozen=read('artifacts/mount-path-kernel-frozen-source-build.json')['frozen_baseline_source_provenance']
assert digest(frozen['original_report'])==frozen['original_report_sha256'];add(frozen['original_report'])
for item in frozen['inputs'].values():assert digest(item['path'])==item['sha256'];add(item['path'])
history=read('artifacts/sandbox-check-history/manifest.json')
for item in history.values():assert digest(item['archived'])==item['sha256']
add('artifacts/sandbox-check-history/manifest.json')
patches=[('vendor/darlingserver','artifacts/darling-sandbox-policy-server-source.patch'),('vendor/darling/src/external/xnu','artifacts/darling-pid-generation-kernel-source.patch'),('vendor/darling','artifacts/darling-sandbox-query-policy-source.patch'),('vendor/darling/src/external/libcxx','artifacts/darling-libcxx-expected-source.patch')]
for folder,name in patches:
    subprocess.run(['git','apply','--reverse','--check',str(root/name)],cwd=root/folder,check=True);add(name)
names=[
 'artifacts/xcode-service-runtime-generation-policy-expected-sandbox-typed-cloud-base-version.json',
 'artifacts/xcode-service-runtime-extended-generation-policy-expected-sandbox-typed-cloud-base-version.json',
 'artifacts/xcode-service-runtime-generation-policy-expected-sandbox-typed-cloud-base-trace-version.json',
 'artifacts/xcode-service-runtime-generation-policy-expected-sandbox-typed-cloud-diagnostic-build.json',
 'artifacts/xcode-service-runtime-expected-sandbox-typed-cloud-base-version.json',
 'artifacts/xcode-service-runtime-generation-policy-expected-sandbox-typed-cloud-base-prefs-daemon-version.json',
 'artifacts/xcode-service-runtime-mobile-generation-policy-expected-sandbox-typed-cloud-prefs-daemon-diagnostic-build.json',
]
probes={}
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
original_sha=digest(original)
assert original_sha==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
assert original_sha=='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
for name in names:
    data=read(name)
    assert data['original_xcodebuild_sha256']==original_sha
    for key in ['log','script']:assert digest(data[key])==data[key+'_sha256'];add(data[key])
    for n,sha in data['service_logs'].items():assert digest(n)==sha;add(n)
    for job in data['jobs']:assert digest(job['path'])==job['sha256'];add(job['path'])
    assert digest('scripts/runtime-ns.sh')==data['runtime_namespace_script_sha256']
    add(name)
    text=(root/data['log']).read_text();missing=re.search(r'Symbol not found: (\S+)',text)
    probes[name]={'exit_status':data['exit_status'],'UTI_preflight_verified':data['UTI_preflight_verified'],'diagnostic_without_UTI_preflight':data['diagnostic_without_UTI_preflight'],'xcode_process_started':data['xcode_process_started'],'loader_symbol':missing[1] if missing else None}
diagnostic=read(names[3]);assert diagnostic['xcode_process_started'] and diagnostic['diagnostic_without_UTI_preflight']
assert diagnostic['exit_status']==255 and probes[names[3]]['loader_symbol']=='_AMDeviceCreateWithRemoteDeviceWithError'
assert '__ZTINSt3__119bad_expected_accessIvEE' not in (root/diagnostic['log']).read_text()
preferences=read(names[-2]);service=preferences['original_preference_service']
assert digest(service['original'])==service['sha256']==digest(service['selected'])
assert not service['binary_modified']
pref_log=next(n for n in preferences['service_logs'] if n.endswith('-cfprefsd-daemon.log'))
assert 'Symbol not found: __qtn_proc_alloc' in (root/pref_log).read_text()
mobile=read(names[-1]);selection=mobile['native_mobile_device_selection']
assert selection['selected'] and not selection['binary_modified']
assert digest(selection['image'])==selection['sha256']
assert mobile['xcode_process_started'] and mobile['diagnostic_without_UTI_preflight']
assert probes[names[-1]]['loader_symbol']!='_AMDeviceCreateWithRemoteDeviceWithError'
add('artifacts/mobile-device-queue-timeout.json')
for stem in ['pid-generation-lsd-hang','pid-generation-uti-hang']:
    for suffix in ['gdb.log','maps.log','annotated.log']:add('logs/'+stem+'.'+suffix)
assert '_CFPREFERENCES_IS_WAITING_FOR_SYSTEM_CFPREFSD' in (root/'logs/pid-generation-lsd-hang.annotated.log').read_text()
scripts=['scripts/'+n for n in ['build-expected-access-source.py','expected-access-source-profile.py','test-expected-access-source.py','build-sandbox-policy-source.py','sandbox-policy-source-profile.py','test-sandbox-policy-source.py','stage-pid-generation-source.py','pid-generation-source-profile.py','test-process-generation-source.py','test-pid-generation-cpp-regression.py','mobile-device-native-profile.py','probe-xcode-service-runtime.py','record-expected-sandbox-runtime-progress.py']]
last=probes[names[-1]]
next_work=[
 'Run the genuine cfpreference service and restore strict UTI preflight: the native daemon now reaches missing internal Quarantine __qtn_proc_alloc. Do not alias Darling\'s current placeholder qtn_proc object or invent policy application success. Live lsd waits for this system service while its UTI client waits for lsd.',
 'Continue the unchanged original xcodebuild project with the genuine MobileDevice package selected. The AMDeviceCreateWithRemoteDeviceWithError gap is resolved by selecting the existing original payload; its actual next missing import is CoreUtils kCryptoHashDescriptor_SHA512. Implement the genuine descriptor/hash ABI or compatible native provider without dummy cryptography.',
 'Implement the retained chained-fixup strong replacement/weak coalescing case in the real Darling loader; the macOS 15.4 fixture currently fails and is preserved separately from comparable macOS 11 allocator regressions.',
 'Complete the original Unity/CocoaPods compile/archive/sign/export workflow and default launcher integration only after the full runtime is proven. Sandbox profile enforcement, production Security NSXPC, signing/trust and other earlier limits are still incomplete.'
]
record={'checked_at':datetime.now(timezone.utc).isoformat(),'previous_report':'artifacts/sandbox-check-progress.json','previous_evidence_archive':'artifacts/sandbox-check-history/manifest.json','previous_goal_turn_classification':'no_progress: source/status clarification only; active state revalidated before this implementation','current_goal_turn_classification':'progress','source_runtime':runtime,'source_kernel_complete_files':875,'expected_access_runtime_checks':3215,'allocator_checks':251,'replacement_checks':331,'finite_formatting_cases':11427,'native_long_double_narrowing_cases':15,'process_generation_checks':106,'registered_unconfined_Sandbox_checks':95,'original_xcodebuild_sha256':original_sha,'probe_results':probes,'latest_diagnostic_loader_blocker':last['loader_symbol'],'strict_UTI_preflight_verified':probes[names[-2]]['UTI_preflight_verified'],'Sandbox_profiles_enforced':False,'Sandbox_approval_grants_verified':False,'chained_replacement_case_resolved':False,'default_launcher_changed':False,'full_xcode_build_ready':False,'signing_ready':False,'complete':False,'goal_status':'active','next_work':next_work,'evidence':{n:digest(n) for n in dict.fromkeys(evidence)},'scripts':{n:digest(n) for n in scripts}}
destination='artifacts/expected-sandbox-runtime-progress.json'
pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=runtime,latest_xcode_loader_blocker=last['loader_symbol'],latest_staged_coreml_and_metal_blocker=last['loader_symbol']+' (diagnostic without UTI preflight)',latest_xcode_failure_kind='native_service_and_loader_runtime_incomplete',latest_xcode_runtime_failure='Strict UTI waits for cfprefsd, whose original daemon lacks __qtn_proc_alloc. Diagnostic original project now loads the genuine MobileDevice payload and reaches missing CoreUtils kCryptoHashDescriptor_SHA512 (255). Full build remains unproven.',latest_implementation_form='Darling source changes and private compiled components; complete Sandbox/kernel source builds, actual source server and added libc++ runtime class. Original Xcode unchanged. No test capture backend in real queries.',active_build={'task':'source-expected-Sandbox-PID-runtime','running':False,'report':destination})
state['next_work']=next_work
state.setdefault('source_components',{}).update(expected_runtime='artifacts/expected-access-source-build.json',Sandbox_query_server='artifacts/sandbox-policy-source-build.json',process_identity_kernel='artifacts/pid-generation-kernel-source-build.json',expected_Sandbox_progress=destination)
state['latest_validation_reports']=list(dict.fromkeys(state.get('latest_validation_reports',[])+list(record['evidence'])+[destination]))
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded actual source runtime, passing focused regressions, retained failures and unchanged Xcode; full goal remains active')
