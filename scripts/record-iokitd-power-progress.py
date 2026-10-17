#!/usr/bin/env python3
"""Record source IOPower registration and the next unchanged disk-daemon failure."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/iokitd-matching-progress.json').exists():
    print('Preserving the newer iokitd matching and notifyd checkpoint')
    raise SystemExit(0)
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve'];evidence={}
def add(name,sha=None):
    path=resolve(str(name),sha) if sha else str(name);evidence[path]=digest(path)
    if sha:assert evidence[path]==sha,name
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
previous=report('artifacts/diskarbitration-log-compose-progress.json')
build=report('artifacts/iokitd-power-build.json');assert build['complete_source_files']==22 and build['full_iokitd_source_build']
server=report('artifacts/iokitd-power-server-build.json');assert server['baseline_build_output_restored']
report('artifacts/iokitd-power-stage.json')
# The unmodified fixed-commit daemon build and its original-job baseline remain
# independently usable via the preserved exact source inputs.
report('artifacts/iokitd-power-baseline-build.json');report('artifacts/iokitd-power-baseline-stage.json')
report('artifacts/diskarbitration-service-no-daemon-original-job-baseline.json')
test=report('artifacts/iokit-power-service-test.json');assert test['runtime_execution_verified'] and test['connection_subscription_cycles']==128
assert test['physical_ool_cases']==7 and not test['physical_host_suspend_verified']
clock=report('artifacts/linux-resume-clock-test.json');assert clock['passed'] and clock['checks']==1016
assert clock['synthetic_clock_samples'] and clock['address_and_undefined_sanitizers']
daemon=report('artifacts/diskarbitration-service-power-domain-final.json');assert not daemon['daemon_binary_modified'] and daemon['exit_status']==0
trace='logs/diskarbitration-service-power-domain-final.gdb.log';add(trace);add('logs/diskarbitration-service-power-domain-final.maps.log')
text=(root/trace).read_text();power=re.search(r'DAEMON_TRACE system_power_return.*rax=(0x[0-9a-f]+)',text)
assert power and int(power[1],16)!=0
assert 'could not create "media disappeared" notification.' in text and 'DAEMON_TRACE exit rdi=0x46' in text
regressions=[]
for mode in ['version','showsdks']:
    paths=[p for p in sorted((root/'artifacts').glob('xcode-service-runtime-iokitd-power-'+mode+'-*.json')) if read(str(p.relative_to(root)))['exit_status']==0];assert len(paths)==1
    name=str(paths[0].relative_to(root));d=report(name);assert d['exit_status']==0
    regressions.append(dict(report=name,sha256=digest(name),mode=mode,exit_status=0))
repo=root/'vendor/darling/src/external/iokitd'
patch=subprocess.check_output(['git','-C',str(repo),'diff','HEAD'],text=True)
for name in subprocess.check_output(['git','-C',str(repo),'ls-files','--others','--exclude-standard'],text=True).splitlines():
    patch+=''.join(difflib.unified_diff([], (repo/name).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+name))
(root/'artifacts/iokitd-power-source.patch').write_text(patch);add('artifacts/iokitd-power-source.patch')
subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(root/'artifacts/iokitd-power-source.patch')],check=True)
name='vendor/darlingserver/duct-tape/xnu/osfmk/ipc/ipc_kmsg.c';entry=read('runtime/source-input-history/manifest.json')[name]
old=root/entry['snapshot']
patch=''.join(difflib.unified_diff(old.read_text().splitlines(True),(root/name).read_text().splitlines(True),fromfile='a/duct-tape/xnu/osfmk/ipc/ipc_kmsg.c',tofile='b/duct-tape/xnu/osfmk/ipc/ipc_kmsg.c'))
(root/'artifacts/iokitd-power-ipc-source.patch').write_text(patch);add('artifacts/iokitd-power-ipc-source.patch')
for name in ['scripts/build-iokitd-source.py','scripts/build-iokitd-power-server.py','scripts/stage-iokitd-power-runtime.py','scripts/iokitd-power-runtime-profile.py','scripts/test-iokit-power-service.py','scripts/test-linux-resume-clock.py','scripts/probe-diskarbitration-service.py','scripts/probe-xcode-service-runtime.py','scripts/record-iokitd-power-progress.py','scripts/resolve-evidence-history.py','fixtures/hello/iokit-power-service.c','fixtures/hello/linux-resume-clock.cpp']:
    add(name)
    if name.endswith('.py'):ast.parse((root/name).read_text())
p=runpy.run_path(str(root/'scripts/iokitd-power-runtime-profile.py'))['profile']()
next_work=[
    'Implement genuine IOKit matching subscriptions/iterator rearming and Linux media discovery; original diskarbitrationd now passes IORegisterForSystemPower and next exits 70 creating the media-disappeared notification. Do not fabricate media or ignore its error.',
    'Verify resume messages through the actual native callback path and complete Linux pre-suspend/acknowledgement behavior; current clock observer does not implement a suspend barrier or power-control selectors.',
    'Restore original DiskArbitration disk descriptions and volume references, FileIDTree/CF mounted-volume enumeration and FileCoordination; then unchanged Xcode project compilation, Unity/CocoaPods, archive, signing and export.',
    'Complete original restrictive Sandbox enforcement and external SystemRoot event coverage; retain original binaries and CI commands.'
]
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
            previous_goal_turn_classification='no_progress',current_goal_turn_classification='progress',source_runtime=p['source_runtime'],
            source_iokitd_power=p['source_iokitd_power'],source_iokitd_files=22,source_iokitd_commit=build['source_commit'],
            native_power_service_checks=test['checks'],native_connection_subscription_cycles=128,
            daemon_receive_ports_before_cycles=12,daemon_receive_ports_after_cycles=12,
            mixed_port_physical_ool_cases=7,resume_clock_model_checks=1016,resume_clock_model_sanitizers=True,
            root_domain_registered=True,native_IORegisterForSystemPower_verified=True,actual_power_connection_and_notifier_Mach_ports=True,
            native_property_buffer_copy_verified=True,cross_task_open_rejection_verified=True,
            original_diskarbitrationd_system_power_registration_succeeded=True,original_diskarbitrationd_binary_modified=False,
            original_diskarbitrationd_exit_status=70,original_DiskArbitration_client_session_created=False,
            next_original_daemon_failure='could not create "media disappeared" notification.',
            next_source_gap='IOKit service matching notification RPCs and real Linux media registry',
            resume_observer_backend='Linux x86_64 CLOCK_BOOTTIME minus CLOCK_MONOTONIC; timer observation with scheduling brackets',
            native_resume_notification_delivery_verified=False,physical_host_suspend_verified=False,
            pre_suspend_permission_barrier_implemented=False,power_control_selectors_implemented=False,
            production_Sandbox_policy_resources_modified=False,default_entry_promoted=False,
            original_xcode_regressions=regressions,evidence=evidence,next_work=next_work)
(root/'artifacts/iokitd-power-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'hashes; native power registration/lifetime verified; disk matching notifications remain')
