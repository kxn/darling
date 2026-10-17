#!/usr/bin/env python3
"""Record the genuine query ABI and its explicitly failing integration gate."""

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
if state_path.exists() and json.loads(state_path.read_text()).get('primary_report') in {'artifacts/expected-sandbox-runtime-progress.json','artifacts/coreutils-quarantine-progress.json'}:
    print('Preserving the newer source expected/Sandbox runtime checkpoint');raise SystemExit(0)
p=runpy.run_path(str(root/'scripts/sandbox-check-source-profile.py'))['profile']()
stage=p['source_sandbox_checks'];assert stage['full_sandbox_library_source_build'] and stage['complete_source_files']==3
assert stage['original_exports_preserved']==49 and len(stage['added_exports'])==6
assert stage['query_MAC_operation']==2 and not stage['MAC_policy_implemented'] and not stage['approval_grants_implemented']
for key,item in stage['source_runtime'].items():
    assert digest(item['path'])==item['sha256']
    if key=='LINUXCODE_SANDBOX':assert item['sha256']!=stage['previous_source_runtime'][key]['sha256']
    else:assert item['sha256']==stage['previous_source_runtime'][key]['sha256']
tests=read('artifacts/sandbox-check-source-test.json')
assert tests['source_runtime']==stage['source_runtime'] and tests['source_sandbox_checks']==stage
assert tests['capture_is_test_only'] and not tests['approval_policy_execution_verified']
for name,sha in tests['sources'].items():assert digest(name)==sha
for key in ['native','capture_helper']:assert digest(tests[key])==tests[key+'_sha256']
assert [row['exit_status'] for row in tests['checks']]==[0,0]
for row in tests['checks']:
    for key in ['log','binary']:assert digest(row[key])==row[key+'_sha256']
assert 'cases=12814 checks=281689' in (root/tests['checks'][0]['log']).read_text()
assert 'cases=2560 checks=5141' in (root/tests['checks'][1]['log']).read_text()
real_deps=subprocess.check_output(['llvm-objdump-19','--macho','--dylibs-used',str(root/tests['checks'][1]['binary'])],text=True)
assert 'SandboxCheckCapture' not in real_deps
assert all('capture-libraries' not in arg for arg in tests['checks'][1]['command'])
previous=read('artifacts/xcode-service-runtime-typed-cloud-base-version.json')
assert previous['source_runtime']==stage['previous_source_runtime'] and previous['exit_status']==0 and previous['UTI_preflight_verified']
for key in ['log','script']:assert digest(previous[key])==previous[key+'_sha256']
names={'build':'build','version':'base-version','sdk':'base-showsdks','diagnostic':'diagnostic-build'}
reports={name:read('artifacts/xcode-service-runtime-sandbox-typed-cloud-'+suffix+'.json') for name,suffix in names.items()}
for name,data in reports.items():
    assert data['source_runtime']==stage['source_runtime'] and data['source_sandbox_checks']==stage
    for key in ['log','script']:assert digest(data[key])==data[key+'_sha256']
    assert digest('scripts/runtime-ns.sh')==data['runtime_namespace_script_sha256']
    for job in data['jobs']:assert digest(job['path'])==job['sha256']
    for path,sha in data['service_logs'].items():assert digest(path)==sha
    assert not data['UTI_preflight_verified']
    assert all('capture-libraries' not in arg and 'SandboxCheckCapture' not in arg for arg in data['command'])
    if name!='diagnostic':
        assert data['exit_status']==1 and not data['xcode_process_started']
        text=(root/data['log']).read_text();assert 'Precondition failed' in text and 'uniform-type-identifiers-native.swift:27:' in text
        assert 'NATIVE_UTI_IDENTIFIERS_PREFERRED_EXTENSIONS_AND_URL_EXTENSIONS_OK' in text
        assert 'SERVICE_RUNTIME_XCODE_STATUS ' not in text
diagnostic=reports['diagnostic'];text=(root/diagnostic['log']).read_text()
assert diagnostic['diagnostic_without_UTI_preflight'] and diagnostic['xcode_process_started'] and diagnostic['exit_status']==255
assert 'SERVICE_RUNTIME_UTI_PREFLIGHT_SKIPPED_DIAGNOSTIC_ONLY' in text
blocker='__ZTINSt3__119bad_expected_accessIvEE'
assert 'Symbol not found: '+blocker in text and 'Symbol not found: _SANDBOX_CHECK_ALLOW_APPROVAL' not in text
assert '** BUILD SUCCEEDED **' not in text
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==diagnostic['original_xcodebuild_sha256']==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
analysis=read('artifacts/sandbox-check-policy-gap-analysis.json')
assert digest(analysis['query_trace_log'])==analysis['query_trace_log_sha256']
assert digest(analysis['server_source'])==analysis['server_source_sha256']
assert any('operation=file-read-data filter=0x60000001 policy_flags=0x40000003 status=-1 decision=0 errno=103' in row for row in analysis['observed_query_traces'])
history=read('artifacts/security-current-item-history/manifest.json')
for name,item in history.items():assert digest(item['archived'])==item['sha256']
patch='artifacts/darling-sandbox-check-source.patch'
subprocess.run(['git','apply','--reverse','--check',str(root/patch)],cwd=root/'vendor/darling',check=True)
subprocess.run(['git','diff','--check','--','src/sandbox'],cwd=root/'vendor/darling',check=True)
source=(root/'vendor/darling/src/sandbox/check.c').read_text();assert '__mac_syscall("Sandbox",2,args)' in source
legacy=(root/'vendor/darling/src/sandbox/sandbox.c').read_text();assert 'int sandbox_check(' not in legacy and 'int sandbox_check_by_audit_token(' not in legacy
evidence=[patch,'artifacts/sandbox-provider-probe.json','logs/sandbox-provider-probe.log','runtime/sandbox-provider-probe.c','artifacts/sandbox-check-source-build.json','artifacts/sandbox-check-source-test.json','artifacts/sandbox-check-final-verification.json','artifacts/sandbox-check-policy-gap-analysis.json','artifacts/security-current-item-history/manifest.json','artifacts/xcode-service-runtime-typed-cloud-base-version.json',previous['log'],previous['script']]
evidence += ['artifacts/xcode-service-runtime-sandbox-typed-cloud-'+suffix+'.json' for suffix in names.values()]
evidence += [row['log'] for row in tests['checks']]
for data in reports.values():evidence += [data['log'],data['script']]+list(data['service_logs'])+[job['path'] for job in data['jobs']]
scripts=['scripts/'+name for name in ['build-sandbox-check-source.py','sandbox-check-source-profile.py','test-sandbox-check-source.py','build-sandbox-source.py','probe-xcode-service-runtime.py','record-sandbox-check-progress.py']]
record={'checked_at':datetime.now(timezone.utc).isoformat(),'previous_report':'artifacts/security-current-item-progress.json','previous_evidence_archive':'artifacts/security-current-item-history/manifest.json','previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress','source_runtime':stage['source_runtime'],'source_sandbox_checks':stage,'native_ABI_differential_cases':12814,'native_ABI_checks':281689,'real_missing_policy_cases':2560,'real_missing_policy_checks':5141,'query_legacy_universal_allow_removed':True,'seven_native_flags_verified':True,'MAC_policy_implemented':False,'approval_grants_verified':False,'strict_UTI_conformance_verified':False,'strict_probe_exits':{'build':1,'version':1,'showsdks':1},'xcode_started_in_strict_probes':False,'previous_runtime_control_version_exit':0,'previous_runtime_control_UTI_verified':True,'diagnostic_without_preflight_project_exit':255,'diagnostic_loader_blocker':blocker,'normal_integrated_build_ready':False,'original_xcodebuild_sha256':digest(original),'default_launcher_changed':False,'full_xcode_build_ready':False,'signing_ready':False,'goal_status':'active','complete':False,'next_work':analysis['next_work'],'evidence':{n:digest(n) for n in dict.fromkeys(evidence)},'scripts':{n:digest(n) for n in scripts},'limits':[
    'The complete three-file user-space Sandbox library is rebuilt. Its two check functions now issue the real MAC operation 2 rather than returning unconditional allow. Seven original uint32 flags, all twenty filter encodings, six flag bits, pid/audit argument layouts, alias and result/error conversion are compared against original native code. All 49 prior exports remain.',
    'Positive and denied decision cases are supplied by an explicitly test-only interposition fixture to inspect original and source ABI. The separate real-query executable does not link that fixture and preserves ENOPOLICY. No actual policy approval, confinement, extension grant or authorization was proven.',
    'New-source integration regresses the strict UTI conformance preflight: tag identifiers/extensions work but .conforms(to:.data) fails. Build/version/SDK scripts stop before invoking Xcode. The previous seven-component runtime is freshly controlled and still passes UTI plus original version. Only the Sandbox binary hash differs; the exact failing LaunchServices branch needs tracing.',
    'A separate diagnostic omits the UTI fixture explicitly, runs the unchanged original project command, and reaches missing libc++ bad_expected_access<void> RTTI after resolving the Sandbox flag. This is not a clean preflight or build success. No compilation, archive, signing or export completed.',
    'darlingserver currently provides Quarantine MAC handling but no Sandbox policy. lsd makes a real file-read-data query with NO_REPORT/CANONICAL, receives ENOPOLICY, and the selected environment lacks confinement state/query semantics. Other legacy sandbox_init/rootless stubs and earlier notification, NSXPC, graphics, Swift disk, signing/trust limitations remain. Default entry points are unchanged.',
]}
destination='artifacts/sandbox-check-progress.json';pending=root/(destination+'.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(root/destination)
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=stage['source_runtime'],latest_xcode_loader_blocker=blocker+' (diagnostic without UTI preflight)',latest_staged_coreml_and_metal_blocker=blocker+' (diagnostic only)',latest_xcode_runtime_failure='Strict UTI conformance preflight fails; Sandbox MAC backend is missing. Strict probes never start Xcode. Separate direct diagnostic exits 255 on libc++ RTTI.',latest_xcode_failure_kind='Sandbox_MAC_backend_and_UTI_conformance',latest_sdk_listing_succeeded=False,latest_sdk_listing_attempted=False,previous_runtime_version_control_succeeded=True,latest_implementation_form='Direct complete three-file Darling Sandbox source build; real MAC query ABI and seven constants, selected in a private matching seven-component root. No production per-function hook. Test-only ABI capture is excluded from actual queries and Xcode.',active_build={'task':'source-Sandbox-query-ABI-and-missing-policy-integration','running':False,'report':destination})
old=[x for x in state['next_work'] if not x.startswith('Restore the original SANDBOX_CHECK_ALLOW_APPROVAL')]
state['next_work']=list(dict.fromkeys(analysis['next_work']+old))
verification='Complete source Sandbox query port retains 49 exports and adds six flags; 12814 native ABI comparison cases (281689 checks) and 2560 actual ENOPOLICY cases (5141 checks) pass. Strict UTI conformance regresses and prevents Xcode invocation; previous runtime control still passes UTI/version. Explicit diagnostic without preflight resolves flag and reaches missing bad_expected_access<void> RTTI (255). Policy/backend and full goal remain incomplete.'
state['last_verification']=list(dict.fromkeys(state['last_verification']+[verification]))
state['latest_validation_reports']=list(dict.fromkeys(state['latest_validation_reports']+evidence+[destination]))
state['source_components'].update(sandbox='artifacts/sandbox-check-source-build.json',sandbox_query_execution='artifacts/sandbox-check-source-test.json',sandbox_query_progress=destination)
pending=root/'artifacts/current-work-state.json.pending';pending.write_text(json.dumps(state,indent=2)+'\n');pending.replace(root/'artifacts/current-work-state.json')
print('Recorded genuine Sandbox query source, strict UTI regression, real absent-policy errors and diagnostic loader gap; goal active')
