#!/usr/bin/env python3
"""Record real file-mutation query paths; no SBPL attachment claim."""
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();evidence={}
if read('artifacts/current-work-state.json').get('latest_unrestricted_sandbox_fsevents_progress'):
    print('Preserving the newer unrestricted Sandbox and FSEvents checkpoint')
    raise SystemExit(0)
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
    d=read(name);add(name);walk(d if fields is None else {key:d[key] for key in fields});return d
m=runpy.run_path(str(root/'scripts/sandbox-fs-runtime-profile.py'));p=m['profile']();capture_p=m['profile'](capture=True)
for name in ['artifacts/sandbox-fs-mutations-source-stage.json','artifacts/sandbox-fs-mutations-capture-stage.json']:
    stage=report(name);build=report(stage['kernel_build']);assert build['full_libsystem_kernel_source_build'] and build['complete_source_files']==878
    assert bool(build.get('test_only_source_overrides'))==stage['test_only']
    assert build['baseline_exports_preserved']>0 and build['source_exports']>=build['baseline_exports_preserved']
    if stage['test_only']:
        assert len(build['test_only_source_overrides'])==1
        for item in build['sources']:
            if 'test_override_for' in item:add(item['test_override_for'],item['production_source_sha256'])
prod_kernel=p['source_runtime']['LINUXCODE_LIBSYSTEM_KERNEL'];test_kernel=capture_p['source_runtime']['LINUXCODE_LIBSYSTEM_KERNEL']
assert prod_kernel['sha256']!=test_kernel['sha256']
for key,item in p['source_runtime'].items():
    if key!='LINUXCODE_LIBSYSTEM_KERNEL':assert item['sha256']==capture_p['source_runtime'][key]['sha256']
symbols=subprocess.check_output(['llvm-nm','-an',str(root/prod_kernel['path'])],text=True)
assert 'sandbox_fs_test_rpc' not in symbols and '_sandbox_fs_authorize' in symbols
real=report('artifacts/sandbox-fs-mutations-real-test.json');controlled=report('artifacts/sandbox-fs-mutations-capture-test.json')
assert real['runtime_execution_verified'] and real['checks']==338 and not real['test_only_query_injection']
assert controlled['runtime_execution_verified'] and controlled['checks']==251 and controlled['pinned_parent_replacement_checked']
rows=controlled['captured_queries'];assert len(rows)==60
assert sum(row['decision']=='1' for row in rows)==39 and sum(row['error']=='5' for row in rows)==2
assert sum(row['transport']=='-11' for row in rows)==1 and all('/alias/' not in row['path'] for row in rows)
assert real['source_sandbox_fs']==p['source_sandbox_fs'] and controlled['source_sandbox_fs']==capture_p['source_sandbox_fs']
regression=report('artifacts/sandbox-fs-regression.json');assert regression['runtime_execution_verified'] and len(regression['checks'])==6
assert all(row['verified'] and row['exit_status']==0 for row in regression['checks'])
quarantine=next(row for row in regression['checks'] if row['name']=='quarantine')
assert 'QUARANTINE_VFS_REAL_PERSISTED_LABELS_KERNEL_PAIRING_FORK_EXEC_AND_UNCONFINED_CONTROL_OK' in (root/quarantine['log']).read_text()
labels=regression['physical_quarantine_labels'];assert labels['new'].startswith('0082;') and labels['directory'].startswith('0086;00000000;')
names=list((root/'artifacts').glob('xcode-service-runtime-sandbox-fs-launchd-sandbox-*showsdks.json'));assert len(names)==1
service=report(str(names[0].relative_to(root)),['jobs','service_logs','original_preference_service','source_sandbox_fs'])
assert service['exit_status']==0 and service['UTI_preflight_verified'] and service['xcode_process_returned']
assert service['source_sandbox_fs']==p['source_sandbox_fs']
for key in ['log','script']:add(service[key],service[key+'_sha256'])
assert 'SERVICE_RUNTIME_XCODE_STATUS 0' in (root/service['log']).read_text() and 'iOS SDKs:' in (root/service['log']).read_text()
scripts=['scripts/'+n for n in ['build-libsystem-kernel-source.py','stage-sandbox-fs-runtime.py','sandbox-fs-runtime-profile.py',
         'test-sandbox-fs-mutations.py','test-sandbox-fs-regression.py','record-sandbox-fs-progress.py',
         'probe-xcode-service-runtime.py','workqueue-stack-runtime-profile.py','validate-native-sandbox-policy-checkpoint.py',
         'record-launchd-sandbox-progress.py']]
for name in scripts:ast.parse((root/name).read_text());add(name)
for name in ['fixtures/hello/sandbox-fs-mutations.c','fixtures/hello/sandbox-fs-query-capture.c',
             'artifacts/xnu-sandbox-fs-mutations-source.patch','logs/sandbox-fs-mutations-kernel-build.log',
             'logs/sandbox-fs-mutations-capture-kernel-build.log']:add(name)
history_name='artifacts/sandbox-before-fs-mutations-history/manifest.json';history=read(history_name);add(history_name)
for item in history.values():add(item['archived'],item['sha256'])
subprocess.run(['git','-C',str(root/'vendor/darling/src/external/xnu'),'apply','--reverse','--check',str(root/'artifacts/xnu-sandbox-fs-mutations-source.patch')],check=True)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert (root/'runtime/sandbox-fs-query-enable').read_text()=='0'
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,
            complete_kernel_source_files=878,mutation_entrypoints=['mkdirat','unlinkat','rmdir','renameat'],
            real_filesystem_checks=338,controlled_filesystem_checks=251,controlled_query_events=60,
            controlled_denials=39,controlled_Darwin_errors=2,controlled_Linux_transport_errors=1,
            controlled_negative_decisions_injected=True,pinned_parent_path_replacement_checked=True,
            alias_parent_resolves_to_actual_guest_path=True,negative_mutations_have_no_file_side_effects=True,
            invalid_pointer_and_oversized_path_errors_checked=True,repeated_failure_descriptor_balance_checked=True,
            original_Quarantine_labels_fork_exec_and_exec_rejection_preserved=True,
            original_xcode_version_passed=True,original_xcode_SDK_listing_with_services_passed=True,strict_UTI_preflight_passed=True,
            regression_checks=6,source_runtime=p['source_runtime'],source_sandbox_fs=p['source_sandbox_fs'],
            test_capture_not_selected_for_production=True,profile_application_implemented=False,
            native_kernel_authorization_parity_verified=False,full_filesystem_policy_enforcement_implemented=False,
            original_coreservicesd_retested=False,new_full_xcode_build_attempted=False,full_xcode_build_ready=False,
            signing_ready=False,default_entry_promoted=False,evidence=evidence,
            scope='Four mutation entrypoints query before changing files and use pinned parent directories; rename checks source unlink, target create and existing-target unlink. The production runtime forwards real Sandbox queries and currently remains unconfined. Negative/transport/race cases use a test-only translation-unit override. This is not complete file/Mach enforcement, native-kernel parity, or successful SBPL attachment.',
            next_work=['Add open/create/truncate, descriptor read/write, mmap/exec, metadata/xattr/link and other actual operation hooks; enforce original policy decisions with process-state inheritance only after required paths cannot bypass checks.',
                       'Connect process policy evaluation to query operation 2, fill actual vnode/process context, and complete Mach/XPC-name handling. Keep application failing while coverage or semantics are incomplete.',
                       'Start the unchanged original CoreServices daemon with genuine policy application, restore shared volume references and FileCoordination, then resume actual project compilation through Unity/CocoaPods, archive, signing and export.'])
(root/'artifacts/sandbox-fs-progress.json').write_text(json.dumps(record,indent=2)+'\n');print('Recorded',len(evidence),'file-mutation evidence hashes; full policy application and compilation remain incomplete')
