#!/usr/bin/env python3
"""Verify enabled launchd query paths without claiming attached SBPL policies."""
from pathlib import Path as _fs_Path
import json as _fs_json
_fs_state=_fs_Path(__file__).resolve().parent.parent/'artifacts/current-work-state.json'
if _fs_state.exists() and _fs_json.loads(_fs_state.read_text()).get('latest_sandbox_fs_progress')=='artifacts/sandbox-fs-progress.json':
    print('Preserving the newer file-mutation Sandbox checkpoint');raise SystemExit(0)
from pathlib import Path
from datetime import datetime, timezone
import ast, fcntl, hashlib, json, re, runpy, subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
evidence={}
def add(name,sha=None):
    actual=digest(name)
    if sha is not None:assert actual==sha,name
    evidence[name]=actual
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for pkey in ['source','path']:
                    if pkey+'_sha256' not in value and isinstance(value.get(pkey),str) and (root/value[pkey]).is_file():add(value[pkey],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(dict,list)):walk(item)
def report(name,fields=None):
    data=read(name);add(name);walk(data if fields is None else {key:data[key] for key in fields});return data
p=runpy.run_path(str(root/'scripts/launchd-sandbox-source-profile.py'))['profile']()
build=report('artifacts/launchd-sandbox-source-build.json')
assert build==p['source_launchd_sandbox'] and build['full_launchd_source_build'] and build['complete_source_files']==16
assert build['sandbox_queries_enabled'] and build['queries_use_Mach_caller_audit_token'] and build['nonzero_query_results_deny']
assert '#define HAVE_SANDBOX 1' in (root/build['config_macros']).read_text()
assert 'U _sandbox_check_by_audit_token' in (root/build['symbols']).read_text()
core=(root/'vendor/darling/src/launchd/src/core.c').read_text()
calls=[line for line in core.splitlines() if 'sandbox_check_by_audit_token(' in line]
assert len(calls)==11 and all('*runtime_get_caller_token()' in line and ') != 0)' in line for line in calls)
real=report('artifacts/launchd-sandbox-real-test.json')
capture=report('artifacts/launchd-sandbox-capture-test.json')
baseline=report('artifacts/launchd-sandbox-capture-baseline-test.json')
assert real['runtime_execution_verified'] and real['checks']==144 and not real['negative_decisions_test_injected']
assert capture['runtime_execution_verified'] and capture['checks']==104 and capture['negative_decisions_test_injected']
assert baseline['expected_result_verified'] and baseline['exit_status']==1 and not baseline['runtime_execution_verified']
assert not baseline['captured_queries'] and 'status=0 expected=1100' in (root/baseline['log']).read_text()
rows=capture['captured_queries'];assert len(rows)==34
assert sum(r['decision']=='1' for r in rows)==6
assert sum(r['status']=='-1' and r['errno']=='5' for r in rows)==6
for d in [real,capture,baseline]:assert d['source_launchd_sandbox']==build
regression=report('artifacts/launchd-sandbox-regression.json')
assert regression['runtime_execution_verified'] and len(regression['checks'])==4
assert all(row['exit_status']==0 and row['verified'] for row in regression['checks'])
names=list((root/'artifacts').glob('xcode-service-runtime-launchd-sandbox-*showsdks.json'));assert len(names)==1
service_name=str(names[0].relative_to(root));service=report(service_name,['jobs','service_logs','original_preference_service','source_launchd_sandbox'])
for key in ['log','script']:add(service[key],service[key+'_sha256'])
assert service['exit_status']==0 and service['UTI_preflight_verified'] and service['source_launchd_sandbox']==build
assert service['xcode_process_returned'] and service['xcode_process_started']
log=(root/service['log']).read_text()
assert 'SERVICE_RUNTIME_XCODE_STATUS 0' in log and 'iOS SDKs:' in log
for name,sha in service['service_logs'].items():add(name,sha)
scripts=['scripts/'+n for n in ['build-launchd-sandbox-source.py','launchd-sandbox-source-profile.py',
         'build-launchd-sandbox-capture.py','launchd-sandbox-capture-profile.py',
         'stage-launchd-sandbox-capture-baseline.py','test-launchd-sandbox.py',
         'test-launchd-sandbox-regression.py','probe-xcode-service-runtime.py',
         'record-launchd-sandbox-progress.py','validate-native-sandbox-policy-checkpoint.py',
         'record-native-sandbox-policy-progress.py']]
for name in scripts:ast.parse((root/name).read_text());add(name)
for name in ['fixtures/hello/launchd-sandbox.c','fixtures/hello/launchd-sandbox-query-capture.c',
             'artifacts/darling-launchd-sandbox-audit-source.patch']:add(name)
histories={}
for name in ['artifacts/sandbox-policy-before-launchd-history/manifest.json',
             'artifacts/launchd-sandbox-direct-query-control-history/manifest.json']:
    frozen=read(name);add(name)
    for item in frozen.values():add(item['archived'],item['sha256'])
    histories[name]=dict(sha256=digest(name),files=len(frozen))
control=read(read('artifacts/launchd-sandbox-direct-query-control-history/manifest.json')['artifacts/launchd-sandbox-regression.json']['archived'])
assert control['checks'][-1]['exit_status']==-9 and not control['checks'][-1]['verified']
subprocess.run(['git','-C',str(root/'vendor/darling'),'apply','--reverse','--check',str(root/'artifacts/darling-launchd-sandbox-audit-source.patch')],check=True)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,
            full_launchd_source_files=16,enabled_audit_query_sites=11,real_Mach_checks=144,
            controlled_negative_route_checks=104,controlled_query_events=34,
            controlled_denials=6,controlled_query_errors=6,negative_decisions_test_injected=True,
            real_Mach_message_transfer_verified=True,actual_caller_PID_and_exec_generation_verified=True,
            older_launchd_skips_queries_and_accepts_test_denial=True,
            original_xcode_version_passed=True,original_xcode_SDK_listing_with_services_passed=True,
            strict_UTI_preflight_passed=True,XPC_16_connections_256_replies_passed=True,
            original_profile_29_uploads_and_216_checks_passed=True,
            direct_SDK_query_without_required_services_timed_out=True,
            source_runtime=p['source_runtime'],source_launchd_sandbox=build,
            test_capture_not_selected_for_production=True,source_patch='artifacts/darling-launchd-sandbox-audit-source.patch',
            profile_application_implemented=False,full_Mach_policy_enforcement_implemented=False,
            XPC_domain_lookup_exemption_still_present=True,original_coreservicesd_retested=False,
            new_full_xcode_build_attempted=False,full_xcode_build_ready=False,signing_ready=False,
            default_entry_promoted=False,histories=histories,evidence=evidence,
            scope='The 11 existing launchd query sites are now compiled and check the actual Mach caller audit token; nonzero/error results deny. Global/per-PID registration, unknown-service check-in, lookup, receive/send rights and fork/exec are exercised. Injected negative transport tests do not prove SBPL attachment or policy decisions.',
            next_work=['Connect per-process original policy decisions to Sandbox query operation 2 and real operation hooks, with fork/exec inheritance; keep native profile application failing until restrictions are actually enforced.',
                       'Complete Mach coverage, including correct XPC-domain service-name context and the currently skipped XPC lookup branch; keep query errors from becoming grants.',
                       'Add actual file/descriptor/mmap/exec, POSIX IPC, process and sysctl checks with real guest identity. Then start original CoreServices, restore shared volume references and FileCoordination, and resume original project compilation through Unity/CocoaPods, archive, signing and export.'])
(root/'artifacts/launchd-sandbox-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'launchd evidence hashes; original policy attachment and full compilation remain incomplete')
