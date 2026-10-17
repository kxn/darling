#!/usr/bin/env python3
"""Record real matching callbacks, source notifyd IPC and original DiskArbitration sessions."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/mount-flags-progress.json').exists():
    print('Preserving the newer source mount flags and notifications checkpoint');raise SystemExit(0)
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve'];evidence={}
def add(name,sha=None):
    selected=resolve(str(name),sha) if sha else str(name);evidence[selected]=digest(selected)
    if sha:assert evidence[selected]==sha,name
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
report('artifacts/iokitd-power-progress.json')
build=report('artifacts/iokitd-matching-build.json');assert build['complete_source_files']==23 and build['full_iokitd_source_build']
notifybuild=report('artifacts/notifyd-matching-build.json');assert notifybuild['complete_source_files']==6 and notifybuild['full_notifyd_source_build']
assert not notifybuild['XPC_matching_publisher_implemented']
report('artifacts/iokitd-matching-stage.json')
test=report('artifacts/iokitd-matching-test.json');assert test['runtime_execution_verified'] and test['callbacks']==11 and test['lifetime_cycles']==128
assert test['production_object_files_reused']==23 and test['test_only_services'] and not test['fixtures_installed_in_production']
text=(root/test['log']).read_text()
for marker in ['MATCHING_OOL_SUBSCRIPTION_AND_SNAPSHOT_LIFETIME_OK','MATCHING_XML64_AND_INVALID_REQUESTS_OK','MATCHING_FULL_QUEUE_RETRY_AND_DEREGISTRATION_OK','MATCHING_128_RETIRED_MACH_RECEIVE_PORTS_DESTROYED']:assert marker in text
notify=report('artifacts/notify-matching-service-probe.json');assert notify['runtime_execution_verified'] and notify['checks']==19
power=report('artifacts/iokitd-matching-power-regression.json');assert power['runtime_execution_verified'] and power['lifetime_cycles']==128
sessions={}
for stem in ['matching-source-notifyd','matching-no-debugger','matching-default']:
    name='artifacts/diskarbitration-service-'+stem+'.json';d=report(name)
    assert d['exit_status']==0 and d['native_session_created'] and not d['daemon_binary_modified']
    text=(root/d['log']).read_text();assert 'DA_PROBE_RETURNED session=1 appeared=0' in text
    assert re.search(r'DA_VOLUME path=/ disk=0x[1-9a-f][0-9a-f]* description=0x0',text)
    tail=text.split('+ launchctl list com.apple.diskarbitrationd')[-1]
    assert '"PID" = ' in tail and '"LastExitStatus" = 0' in tail
    sessions[stem]=dict(report=name,sha256=digest(name),session_verified=True,root_description_available=False)
store=report('artifacts/diskarbitration-service-no-daemon-matching-store.json');assert store['native_store_functional'] and store['exit_status']==0
report('artifacts/diskarbitration-service-matching-startup.json')
add('logs/diskarbitration-service-matching-source-notifyd.resolved.log');report('artifacts/diskarbitration-service-matching-source-notifyd-images.json')
regressions={}
for mode in ['version','showsdks']:
    paths=sorted((root/'artifacts').glob('xcode-service-runtime-iokitd-matching-'+mode+'-*.json'));assert len(paths)==1
    name=str(paths[0].relative_to(root));d=report(name)
    assert d['exit_status']==0 and d['UTI_preflight_verified'] and d['xcode_process_returned']
    regressions[mode]=dict(report=name,sha256=digest(name),exit_status=0)
for repository,name in [('iokitd','artifacts/iokitd-matching-source.patch'),('libnotify','artifacts/notifyd-matching-source.patch')]:
    repo=root/'vendor/darling/src/external'/repository
    patch=subprocess.check_output(['git','-C',str(repo),'diff','HEAD'],text=True)
    for path in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard'],text=True).splitlines():
        patch+=''.join(difflib.unified_diff([],(repo/path).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+path))
    (root/name).write_text(patch);add(name)
    subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(root/name)],check=True)
for name in ['scripts/build-iokitd-source.py','scripts/build-notifyd-matching-source.py','scripts/stage-iokitd-matching-runtime.py','scripts/iokitd-matching-runtime-profile.py','scripts/test-iokitd-matching.py','scripts/test-iokitd-matching-regressions.py','scripts/probe-notify-matching-service.py','scripts/probe-diskarbitration-service.py','scripts/probe-xcode-service-runtime.py','scripts/record-iokitd-matching-progress.py','scripts/resolve-evidence-history.py','fixtures/hello/iokit-matching-harness.mm','fixtures/hello/iokit-matching-client.c','fixtures/hello/notify-matching-service.c','vendor/darling/src/external/libnotify/notifyd/com.apple.notifyd.plist','vendor/darling/src/external/libnotify/notifyd/CMakeLists.txt','vendor/darling/src/external/libxpc/src/event.m']:
    add(name)
    if name.endswith('.py'):ast.parse((root/name).read_text())
p=runpy.run_path(str(root/'scripts/iokitd-matching-runtime-profile.py'))['profile']()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,
            previous_goal_turn_classification='progress',current_goal_turn_classification='progress',source_runtime=p['source_runtime'],source_iokitd_matching=p['source_iokitd_matching'],
            iokitd_source_files=23,notifyd_source_files=6,native_matching_checks=test['checks'],native_matching_callbacks=11,
            matching_release_cycles=128,all_128_notifier_receive_ports_destroyed=True,full_queue_retry_and_deregister_verified=True,
            production_objects_reused_in_test_harness=23,test_services_installed_in_production=False,initial_enumeration_rearm_coalescing_and_suppression_verified=True,
            binary_XML64_and_OOL_matching_verified=True,termination_and_snapshot_service_lifetime_verified=True,
            actual_Linux_media_discovery_implemented=False,actual_Linux_hardware_hotplug_verified=False,
            notifyd_original_boot_job_installed_privately=True,notifyd_direct_Mach_transport_verified=True,notifyd_cross_process_delivery_checks=19,
            notifyd_XPC_matching_publisher_implemented=False,kernel_mount_notification_generation_verified=False,
            native_IOPower_regression_checks=power['checks'],native_IOPower_release_cycles=128,
            original_configd_store_regression_verified=True,original_configd_and_diskarbitrationd_binaries_modified=False,
            original_DiskArbitration_session_created=True,original_disk_daemon_alive_after_client=True,
            original_disk_sessions=sessions,original_DiskArbitration_root_description_available=False,original_disk_appeared_events=0,
            mounted_volume_enumeration_verified=False,actual_project_compilation_started=False,original_xcode_regressions=regressions,
            current_observed_failure='Original native DA session succeeds; root-volume disk description remains NULL, SystemRoot disk is NULL, and no disks are announced.',
            evidence=evidence,next_work=[
                'Implement real Linux block-device/mounted-filesystem discovery and the required IOKit media/property/registry path, preserving unsupported hardware and power operations as errors. Original DiskArbitration session now works but volume descriptions remain missing.',
                'Restore real legacy volume references, FileIDTree/CF mount enumeration and original FileCoordination, then retry unchanged Xcode project compilation, Unity/CocoaPods, archive, signing and export.',
                'Complete restrictive Sandbox enforcement, external SystemRoot FSEvents coverage, XPC event publishing and actual power callback/pre-suspend behavior; current direct notifyd Mach transport does not implement XPC matching or kernel mount-event generation.'
            ])
(root/'artifacts/iokitd-matching-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'hashes; real native matching/notify IPC and original DA sessions verified; media/volumes incomplete')
