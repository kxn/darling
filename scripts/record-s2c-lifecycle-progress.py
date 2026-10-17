#!/usr/bin/env python3
"""Preserve the real stale-thread diagnosis and subsequent native service progress."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/xpc-activation-materialize-progress.json').exists():
 print('Preserving the newer XPC activation and thread materialization checkpoint');raise SystemExit(0)
read=lambda n:json.loads((root/n).read_text());digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve'];evidence={}
def add(name,sha=None):
 selected=resolve(str(name),sha) if sha else str(name);evidence[selected]=digest(selected)
 if sha:assert evidence[selected]==sha
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
 d=read(name);add(name);walk(d);return d
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
report('artifacts/mount-flags-progress.json')
build=report('artifacts/s2c-lifecycle-server-build.json');assert build['baseline_build_output_restored']
stage=report('artifacts/s2c-lifecycle-stage.json')
for label in ['baseline','fixed']:
 d=report('artifacts/remote-vm-map-'+label+'.json');assert d['verified']
regressions=report('artifacts/s2c-runtime-regressions.json');assert regressions['verified']
native=list((root/'artifacts').glob('core-volume-trace-s2c-*-native-api-no-debugger.json'));assert len(native)==1
volume=report(str(native[0].relative_to(root)));assert volume['exit_status']==0
vtext=(root/volume['log']).read_text()
for stage_name,count,result,error in [('before',0,3,256),('after_paths',10,2,0),('after_index',10,2,0)]:
 assert f'LEGACY_MOUNT_POINTS stage={stage_name} status=0 count={count}' in vtext
 assert f'LEGACY_CF_VOLUMES stage={stage_name} count={count} result={result} error={error}' in vtext
assert len(re.findall(r'LEGACY_CATALOG .* result=0 volume=-\d+ inode=',vtext))==10
assert 'NATIVE_LEGACY_VOLUME_REFERENCE_PROBE_RETURNED' in vtext
baseline_native=list((root/'artifacts').glob('core-volume-trace-*-trace-legacy-api.json'));assert len(baseline_native)==1
report(str(baseline_native[0].relative_to(root)))
proof='logs/core-volumes-s2c-target-state.gdb.log';text=(root/proof).read_text();assert re.search(r'S2C_TARGET .* nsid 62 dead true process 52 .*reply_count -1',text)
for n in [proof,'logs/core-volumes-s2c-target-state.maps.log','logs/core-volumes-server-microthreads-unwound.gdb.log','logs/core-volumes-server-microthreads-unwound.maps.log','logs/core-volume-uti-active-stacks.resolved.log','logs/core-volume-lsd-active-stacks.resolved.log','logs/core-volume-coreservicesd-active-stacks.resolved.log','logs/s2c-fixed-xcode-project-stacks.resolved.log','logs/s2c-fixed-filecoordination-stacks.resolved.log']:
 add(n)
xcode={}
for mode in ['version','showsdks']:
 names=list((root/'artifacts').glob('xcode-service-runtime-s2c-lifecycle-'+mode+'-*.json'));assert len(names)==1
 name=str(names[0].relative_to(root));d=report(name);assert d['exit_status']==0 and d['UTI_preflight_verified'] and d['xcode_process_returned']
 xcode[mode]=dict(report=name,sha256=digest(name),exit_status=0)
names=list((root/'artifacts').glob('xcode-service-runtime-s2c-lifecycle-diagnostic-build-*.json'));assert len(names)==1
name=str(names[0].relative_to(root));project=report(name);assert project['UTI_preflight_verified'] and not project['legacy_volume_API_prewarm_used']
assert not project['xcode_process_returned']
text=(root/project['log']).read_text();assert 'Build settings from command line:' in text
assert not re.search(r'^CompileC |^SwiftCompile ',text,re.M)
claimlog=next(n for n in project['service_logs'] if n.endswith('-filecoordination.log'));claimtext=(root/claimlog).read_text()
assert 'Received claim ' in claimtext and 'Sending handshake request attempt #1 to server' in claimtext and 'Creating connection to com.apple.runningboard' in claimtext
add('runtime/source-input-history/manifest.json')
repo=root/'vendor/darlingserver';patch=subprocess.check_output(['git','-C',str(repo),'diff','HEAD','--','src/process.cpp','src/thread.cpp'],text=True)
name='artifacts/darlingserver-s2c-lifecycle-source.patch';(root/name).write_text(patch);add(name);subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(root/name)],check=True)
for name in ['scripts/build-s2c-lifecycle-server.py','scripts/stage-s2c-lifecycle-runtime.py','scripts/s2c-lifecycle-runtime-profile.py','scripts/trace-core-volumes.py','scripts/build-legacy-volume-probe.py','scripts/capture-server-microthreads.py','scripts/probe-remote-vm-map.py','scripts/test-s2c-runtime-regressions.py','scripts/probe-xcode-service-runtime.py','scripts/record-s2c-lifecycle-progress.py','scripts/fsevents-device-runtime-profile.py','scripts/resolve-evidence-history.py','fixtures/hello/legacy-volume-refs.c','fixtures/hello/remote-vm-map.c']:
 add(name)
 if name.endswith('.py'):ast.parse((root/name).read_text())
p=runpy.run_path(str(root/'scripts/s2c-lifecycle-runtime-profile.py'))['profile']()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,
 previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=p['source_runtime'],source_s2c_lifecycle=stage,
 stale_weak_thread_object_was_selected_for_remote_map=True,observed_dead_target_namespace_tid=62,observed_target_process_namespace_pid=52,
 live_thread_selection_and_dead_entry_guards_implemented=True,all_inflight_remote_call_thread_death_races_solved=False,
 native_remote_vm_multithreaded_recipient_verified=True,existing_memory_entry_32_cycles_and_32_concurrent_maps_verified=True,
 native_IOPower_checks=regressions['results']['power']['checks'],native_matching_checks=regressions['results']['matching']['checks'],
 original_CoreServices_public_FSPathMakeRef_and_catalog_verified=True,native_CF_mounted_volume_count_after_public_API_calls=10,native_CF_volume_error_after_public_API_calls=0,
 public_API_calls_used_in_Xcode_launch=False,startup_all_volume_reference_assignment_implemented=False,
 original_xcode_regressions=xcode,latest_original_project=dict(report=str(names[0].relative_to(root)),sha256=digest(str(names[0].relative_to(root))),exit_status=project['exit_status'],UTI_preflight_verified=True,xcode_process_returned=False),
 original_filecoordinationd_received_actual_Xcode_claim=True,original_filecoordinationd_granted_claim=False,
 current_observed_failure='Original filecoordinationd receives the Xcode project read claim, then waits for its real RunningBoard process-monitor handshake; com.apple.runningboard is not registered. Original project still never reaches compilation.',
 diagnostic_build_uses_explicit_permissive_coreservices_policy=True,strict_Sandbox_enforcement_verified=False,
 actual_project_compilation_started=False,evidence=evidence,next_work=[
 'Restore genuine RunningBoard process-state monitoring or its real documented failure path so original filecoordinationd can complete file-access arbitration; do not fabricate process handles or granted claims.',
 'Retry the unchanged original project and verify real coordinated reads/writes and compile/link steps, then Unity/CocoaPods, archive, signing and export.',
 'Complete startup volume discovery, restrictive Sandbox enforcement, in-flight remote-call death/cancellation races, Linux media/hotplug and other previously recorded runtime gaps.'
 ])
(root/'artifacts/s2c-lifecycle-progress.json').write_text(json.dumps(d,indent=2)+'\n');print('Recorded',len(evidence),'hashes; real stale-thread deadlock fixed; RunningBoard handshake remains')
