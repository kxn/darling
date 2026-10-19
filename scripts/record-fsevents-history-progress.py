#!/usr/bin/env python3
"""Record source FSEvents progress without claiming global IDs or a passing build."""
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve']
digest=lambda name:hashlib.sha256((root/name).read_bytes()).hexdigest()
evidence={}
def add(name,sha=None):
    name=resolve(str(name),sha) if sha else str(name)
    evidence[name]=digest(name)
    if sha:assert evidence[name]==sha,name
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for field in ['source','path','file']:
                    if field+'_sha256' not in value and isinstance(value.get(field),str) and (root/value[field]).is_file():add(value[field],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(dict,list)):walk(item)
def report(name):
    add(name);d=json.loads((root/name).read_text());walk(d);return d
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
baseline=report('artifacts/fsevents-recursive-baseline.json');test=report('artifacts/fsevents-recursive-test.json')
build=report('artifacts/fsevents-history-source-build.json');audit=report('artifacts/stat-cache-fsevents-consumer-audit.json')
corpse=report('artifacts/corpse-map-native-errors.json')
corpse_build=report('artifacts/corpse-map-server-build.json');corpse_stage=report('artifacts/corpse-map-stage.json')
assert corpse['verified'] and corpse['checks']==[1808]
server_failure='logs/fsevents-history-before-corpse-fix-server.log';add(server_failure)
assert 'stub (unsafe): task_map_corpse_info_64' in (root/server_failure).read_text()
assert baseline['verified'] and baseline['checks'][0]['exit_status']==2
assert test['verified'] and len(test['checks'])==3 and all(c['verified'] for c in test['checks'])
assert test['checks'][1]['check_counts']==[88] and build['complete_source_files']==2
assert audit['native_history_done_stops_current_CFRunLoop_verified'] and not audit['global_ids_implemented']
regressions={};all_attempts={}
for mode in ['version','showsdks','build']:
    paths=list((root/'artifacts').glob('xcode-service-runtime-corpse-map-'+('diagnostic-' if mode=='build' else '')+mode+'-*.json'))
    attempts=[];selected=[]
    for path in paths:
        name=str(path.relative_to(root));d=report(name)
        attempts.append(dict(report=name,sha256=digest(name),exit_status=d['exit_status'],xcode_process_returned=d['xcode_process_returned'],timeout_seconds=d['probe_configuration']['timeout_seconds']))
        if d['exit_status']==(65 if mode=='build' else 0) and d['source_recursive_history_fsevents']==build:selected.append((d['checked_at'],name,d))
    assert selected,(mode,attempts)
    _,name,d=max(selected);text=(root/d['log']).read_text()
    assert d['UTI_preflight_verified'] and d['xcode_process_returned']
    if mode=='build':
        assert d['exit_status']==65 and 'Symbol not found: _FSEventsGetCurrentEventId' in text
        assert not re.search(r'^CompileC |^SwiftCompile ',text,re.M)
    else:assert d['exit_status']==0 and 'SERVICE_RUNTIME_XCODE_STATUS 0' in text
    regressions[mode]=dict(report=name,sha256=digest(name),exit_status=d['exit_status'],UTI_preflight_verified=True,timeout_seconds=d['probe_configuration']['timeout_seconds'])
    all_attempts[mode]=attempts
previous_projects=[]
for path in sorted((root/'artifacts').glob('xcode-service-runtime-fsevents-history-diagnostic-build-*.json')):
    name=str(path.relative_to(root));d=report(name)
    previous_projects.append(dict(report=name,sha256=digest(name),exit_status=d['exit_status'],xcode_process_returned=d['xcode_process_returned']))
assert sorted(d['exit_status'] for d in previous_projects)==[-9,65]
histories=[]
for path in sorted((root/'artifacts/xcode-service-probe-history').glob('*/manifest.json')):
    d=json.loads(path.read_text())
    if not any('fsevents-history-' in name or 'corpse-map-' in name for name in d):continue
    add(str(path.relative_to(root)))
    for entry in d.values():add(entry['archived'],entry['sha256'])
    histories.append(str(path.relative_to(root)))
assert histories,'Preserve the first SDK-listing shutdown failure instead of hiding it'
files=['src/frameworks/CoreServices/src/FSEvents/'+n for n in ['FSEvents.m','FSEventsImpl.m','FSEventsImpl.h','CMakeLists.txt']]+['src/frameworks/CoreServices/include/FSEvents/FSEvents.h']
patch='artifacts/darling-fsevents-recursive-history-source.patch'
(root/patch).write_bytes(subprocess.check_output(['git','-C',str(root/'vendor/darling'),'diff','HEAD','--',*files]))
subprocess.run(['git','-C',str(root/'vendor/darling'),'apply','--reverse','--check',str(root/patch)],check=True)
add(patch)
for name in ['scripts/fsevents-history-profile.py','scripts/test-fsevents-history.py','scripts/analyze-stat-cache-fsevents.py','scripts/record-fsevents-history-progress.py','scripts/probe-xcode-service-runtime.py','scripts/fsevents-flush-profile.py','scripts/resolve-evidence-history.py','fixtures/hello/fsevents-history.m','artifacts/fsevents-history-initial-history/manifest.json']:
    add(name)
    if name.endswith('.py'):ast.parse((root/name).read_text())
for name in ['scripts/build-corpse-map-server.py','scripts/stage-corpse-map-runtime.py','scripts/corpse-map-runtime-profile.py','scripts/test-corpse-map-errors.py','scripts/s2c-lifecycle-runtime-profile.py','fixtures/hello/corpse-map-errors.c','vendor/darlingserver/duct-tape/src/task.c','logs/fsevents-history-fault-driver.log','logs/fsevents-history-xcode-first-fault.gdb.log']:
    add(name)
    if name.endswith('.py'):ast.parse((root/name).read_text())
server_patch='artifacts/darlingserver-corpse-map-errors-source.patch'
(root/server_patch).write_bytes(subprocess.check_output(['git','-C',str(root/'vendor/darlingserver'),'diff','HEAD','--','duct-tape/src/task.c']))
subprocess.run(['git','-C',str(root/'vendor/darlingserver'),'apply','--reverse','--check',str(root/server_patch)],check=True);add(server_patch)
p=runpy.run_path(str(root/'scripts/corpse-map-runtime-profile.py'))['profile']()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,
    previous_goal_turn_classification='progress',current_goal_turn_classification='progress',
    source_runtime=p['source_runtime'],source_fsevents=build,source_patch=patch,
    complete_source_files=2,native_recursive_history_checks=test['checks'][0]['check_counts'][-1],
    source_corpse_map_errors=corpse_stage,source_server_build=corpse_build,
    corpse_map_live_task_invalid_argument_errors=512,corpse_map_concurrent_threads=8,
    corpse_map_native_checks=1808,corpse_map_real_VM_cycles=256,
    corpse_map_unreachable_on_invalid_live_tasks_fixed=True,
    real_corpse_generation_implemented=False,real_corpse_kcdata_mapping_implemented=False,
    first_original_project_server_death_preserved=previous_projects,
    traced_followup_returned_original_missing_symbol_failure=True,first_fault_not_reproduced_under_debugger=True,
    existing_native_flush_checks=88,native_64KiB_stack_real_events=2,
    finite_sinceWhen_no_longer_ignored=True,historical_gap_requires_real_rescan=True,
    historical_boundary_delivered_once_per_stream=True,main_queue_CFRunLoop_history_consumer_terminates=True,
    initial_recursive_directory_watches_verified=True,new_directory_watch_race_reported_as_gap=True,
    subtree_rename_path_remap_verified=True,moved_out_subtree_unwatched=True,symlink_cycles_not_followed=True,
    source_watch_limit=65536,original_consumer_audit=audit,original_xcode_regressions=regressions,all_original_xcode_attempts=all_attempts,
    first_showsdks_cleanup_failed_but_Xcode_returned_zero=True,first_showsdks_failure_histories=histories,
    showsdks_serial_retry_completed_cleanly=True,shutdown_race_root_cause_resolved=False,
    prior_server_candidate_showsdks_40_second_wrapper_timeout_preserved=True,
    successful_showsdks_probe_time_limit_seconds=regressions['showsdks']['timeout_seconds'],
    normal_version_and_SDK_listing_and_strict_UTI_passed=True,
    original_project_build_succeeded=False,actual_project_compilation_started=False,
    global_event_ids_implemented=False,durable_historical_journal_implemented=False,
    relative_device_streams_implemented=False,all_stream_flags_verified=False,
    full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,
    original_project_uses_explicit_permissive_coreservices_policy=True,
    current_observed_failure='The original project still fails in clang-stat-cache because FSEventsGetCurrentEventId is absent. Recursive monitoring and honest unavailable-history completion are now implemented and natively verified, but stream IDs remain local counters. A genuine shared event source/global ID namespace is still required; no fake global ID or cache bypass was added.',
    evidence=evidence,next_work=[
        'Implement a genuine shared filesystem event source and global ID namespace. Connect current-ID queries and stream delivery to it; preserve explicit MustScanSubDirs/UserDropped when history or recursive coverage is unavailable. Current per-stream counters do not satisfy this API.',
        'Retest the unchanged original clang-stat-cache on initial generation and cache reuse after real SDK mutations, then continue the original xcodebuild project through CompileC/SwiftCompile and linking. Audit the observed one-off shutdown failure if it recurs; a subsequent SDK-listing run exited cleanly.',
        'Continue complete Unity/CocoaPods, iOS/macOS archives, signing and export; strict Sandbox enforcement and other original runtime/service gaps remain incomplete.'
    ])
(root/'artifacts/fsevents-history-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'hashes; real recursive/history checks:',record['native_recursive_history_checks'],'global ID and complete original build remain unimplemented')
