#!/usr/bin/env python3
"""Record actual unrestricted application, raw device events, and daemon limits."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
resolve=runpy.run_path(str(root/'scripts/resolve-evidence-history.py'))['resolve']
evidence={}
if read('artifacts/current-work-state.json').get('latest_diskarbitration_progress'):
    print('Preserving the newer DiskArbitration and source log composition checkpoint')
    raise SystemExit(0)
def add(name,sha=None):
    name=str(name);selected=resolve(name,sha) if sha else name
    evidence[selected]=digest(selected)
    if sha:assert evidence[selected]==sha,name
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for pkey in ['source','path','file']:
                    if pkey+'_sha256' not in value and isinstance(value.get(pkey),str) and (root/value[pkey]).is_file():add(value[pkey],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(dict,list)):walk(item)
def report(name):
    value=read(name);add(name);walk(value);return value
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
proof=report('artifacts/unrestricted-sandbox-proof-test.json')
assert proof['all_passed'] and [r['cases'] for r in proof['checks']]==[228,6034,6488]
native=report('artifacts/unrestricted-sandbox-native-test.json')
assert native['runtime_execution_verified'] and native['checks']==238 and native['exit_status']==0
host=report('artifacts/fsevents-device-linux-test.json');abi=report('artifacts/fsevents-device-native-test.json')
assert host['real_linux_events'] and host['asan_ubsan'] and host['checks']==337
assert abi['runtime_execution_verified'] and abi['checks']==113
regression=report('artifacts/fsevents-device-sandbox-regression.json')
assert regression['runtime_execution_verified'] and regression['checks']==238
for name in ['artifacts/unrestricted-sandbox-server-build.json','artifacts/unrestricted-sandbox-libxpc-build.json',
             'artifacts/unrestricted-sandbox-runtime-stage.json','artifacts/coreservices-unrestricted-diagnostic-stage.json',
             'artifacts/fsevents-device-server-build.json','artifacts/fsevents-device-kernel-build.json',
             'artifacts/fsevents-device-runtime-stage.json','artifacts/fsevents-device-diagnostic-stage.json']:
    report(name)
xpc=read('artifacts/unrestricted-sandbox-libxpc-build.json')
for key in ['source_files','modified_files']:
    for name,sha in xpc[key].items():add('vendor/darling/src/external/libxpc/'+name,sha)
before='fileidtree-service-unrestricted-diagnostic-sandbox-resources-source-dirs-dirhelper-trace-abort-correct-libc-slide'
after='fileidtree-service-fsevents-device-unrestricted-diagnostic-sandbox-resources-source-dirs-dirhelper-trace-first-device-run'
latest='fileidtree-service-fsevents-device-unrestricted-diagnostic-sandbox-resources-source-dirs-dirhelper-trace-disk-arbitration'
for stem in [before,after,latest]:
    d=report('artifacts/'+stem+'.json');assert d['exit_status']==0 and d['diagnostic_policy']
    report('artifacts/'+stem+'-images.json');add('logs/'+stem+'.resolved.log')
old=(root/('logs/'+before+'.gdb.log')).read_text()
assert 'CORESERVICES_TRACE libc_abort' in old
trace=(root/('logs/'+latest+'.gdb.log')).read_text();log=(root/('logs/'+latest+'.log')).read_text()
for marker in ['native_sandbox_apply_return  rax=0x0','bootstrap_checkin_return  rax=0x0',
               'fsevents_clone_return  rax=0x0','fmod_watching_return  rax=0x0',
               'disk_arbitration_session_return  rax=0x0','disk_arbitration_schedule_return  rax=-0x24']:
    assert marker in trace,marker
assert 'CORESERVICES_TRACE libc_abort' not in trace
assert log.count('FILEIDTREE_MOUNT_POINTS status=0 count=0')==3
assert log.count('NATIVE_VOLUMES_FOUNDATION count=0 nil=1')==3
core_snapshots=re.findall(r'\+ launchctl list com.apple.coreservicesd\n(\{.*?\n\};)',log,re.S)
assert core_snapshots and '"LastExitStatus" = 0;' in core_snapshots[-1]
assert re.search(r'"PID" = \d+;',core_snapshots[-1])
steady=report('artifacts/fileidtree-service-fsevents-device-unrestricted-diagnostic-sandbox-resources-source-dirs-dirhelper-probe-steady.json')
assert steady['exit_status']==0 and steady['client_samples']==3
assert all('DYLD_INSERT_LIBRARIES' not in job['job']['EnvironmentVariables'] for job in steady['jobs'])
steady_log=(root/steady['log']).read_text()
steady_core=re.findall(r'\+ launchctl list com.apple.coreservicesd\n(\{.*?\n\};)',steady_log,re.S)[-1]
assert '"LastExitStatus" = 0;' in steady_core and re.search(r'"PID" = \d+;',steady_core)
assert steady_log.count('FILEIDTREE_MOUNT_POINTS status=0 count=0')==3
assert steady_log.count('NATIVE_VOLUMES_FOUNDATION count=0 nil=1')==3
regressions={}
for mode in ['version','showsdks']:
    names=list((root/'artifacts').glob('xcode-service-runtime-fsevents-device-'+mode+'-*.json'));assert len(names)==1,names
    name=str(names[0].relative_to(root));d=report(name);text=(root/d['log']).read_text()
    assert d['exit_status']==0 and 'SERVICE_RUNTIME_XCODE_STATUS 0' in text
    assert d['UTI_preflight_verified'] and 'SERVICE_RUNTIME_UTI_PREFLIGHT_OK' in text
    regressions[mode]=name
for name in ['logs/native-xpc_runtime_process_has_entered_sandbox-disassembly.log',
             'logs/source-xpc-runtime-sandbox-notification-disassembly.log',
             'runtime/unrestricted-sandbox-tests/native-sbpl-policy-finalizer.scm',
             'runtime/unrestricted-sandbox-tests/explicit-profile.bin',
             'logs/fileidtree-sk-service-abort-disassembly.log']:
    add(name)
# Build reviewable incremental patches against the exact pre-device inputs.
initial=read('artifacts/fsevents-device-initial-history/manifest.json')
for repository,paths,new_paths,out in [
    ('vendor/darlingserver',['CMakeLists.txt','src/call.cpp','scripts/generate-rpc-wrappers.py'],
     ['src/fsevents-device.cpp','internal-include/darlingserver/fsevents-device.hpp'],'artifacts/darlingserver-fsevents-device.patch'),
    ('vendor/darling/src/external/xnu',[
        'darling/src/libsystem_kernel/emulation/'+n for n in ['CMakeLists.txt','src/xnu_syscall/bsd/impl/fcntl/openat.c','src/xnu_syscall/bsd/impl/ioctl/ioctl.c','src/xnu_syscall/bsd/impl/unistd/read.c']],
     ['darling/src/libsystem_kernel/emulation/'+n for n in ['src/xnu_syscall/bsd/helper/misc/fsevents.c','include/xnu_syscall/bsd/helper/misc/fsevents.h']],
     'artifacts/xnu-fsevents-device.patch')]:
    patch=''
    for name in paths+new_paths:
        full=repository+'/'+name;old=[] if name in new_paths else (root/initial[full]['archived']).read_text().splitlines(True)
        patch+=''.join(difflib.unified_diff(old,(root/full).read_text().splitlines(True),fromfile='/dev/null' if name in new_paths else 'a/'+name,tofile='b/'+name))
    (root/out).write_text(patch)
    subprocess.run(['git','-C',str(root/repository),'apply','--reverse','--check',str(root/out)],check=True);add(out)
scripts=['build-unrestricted-sandbox-server.py','stage-unrestricted-sandbox-runtime.py','unrestricted-sandbox-runtime-profile.py',
         'test-unrestricted-sandbox-proof.py','test-unrestricted-sandbox-native.py','stage-coreservices-unrestricted-diagnostic.py',
         'coreservices-unrestricted-diagnostic-profile.py','build-fsevents-device-server.py','stage-fsevents-device-runtime.py',
         'fsevents-device-runtime-profile.py','test-fsevents-sandbox-regression.py','test-fsevents-device-linux.py','test-fsevents-device-native.py','probe-fileidtree-service.py',
         'probe-xcode-service-runtime.py','resolve-evidence-history.py','record-unrestricted-sandbox-fsevents-progress.py',
         'verify-historical-source.py','sandbox-fs-runtime-profile.py','sandbox-policy-vm-server-profile.py','xpc-sent-message-runtime-profile.py']
for name in scripts:ast.parse((root/'scripts'/name).read_text());add('scripts/'+name)
for name in ['sandbox-unrestricted-proof.cpp','sandbox-unrestricted-native.c','fsevents-device-linux.cpp','fsevents-device-native.c']:add('fixtures/hello/'+name)
for manifest in ['artifacts/sandbox-before-unrestricted-profile-history/manifest.json','artifacts/fsevents-device-initial-history/manifest.json']:
    add(manifest)
    for item in read(manifest).values():add(item['archived'],item['sha256'])
p=runpy.run_path(str(root/'scripts/fsevents-device-runtime-profile.py'))['profile']()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
            previous_goal_turn_classification='no_progress',current_goal_turn_classification='progress',
            previous_turn_note='Implementation-form clarification only; resumed the verified post-bootstrap crash this turn.',
            source_runtime=p['source_runtime'],source_fsevents_device=p['source_fsevents_device'],
            unrestricted_proof_cases=228,existing_policy_semantic_cases=6034,existing_policy_parser_cases=6488,
            unrestricted_native_API_checks=238,real_linux_device_checks=337,native_device_ABI_checks=113,
            unrestricted_profile_attachment_verified=True,restrictive_profile_attachment_verified=False,
            original_coreservicesd_binary_modified=False,diagnostic_original_policy_replaced=True,
            diagnostic_coreservicesd_bootstrap_and_session_verified=True,diagnostic_fsevents_startup_abort_resolved=True,
            diagnostic_client_samples=3,diagnostic_without_debugger_samples=3,new_runtime_sandbox_regression_checks=238,diagnostic_mount_count=0,diagnostic_foundation_volume_array_nil=True,
            next_observed_diagnostic_failure='Original DASessionCreate returns null; _FSScheduleFileVolumeOperations returns -36. Repeated volume enumeration remains empty.',
            raw_device_event_types=['delete','rename'],raw_device_scope='virtual-root-tree, Linux pseudo filesystems excluded',
            external_SystemRoot_events_verified=False,originating_event_PID_available=False,
            hardlink_flags_and_native_kernel_event_parity_verified=False,all_filesystem_event_types_supported=False,
            default_entry_promoted=False,original_xcode_regressions=regressions,evidence=evidence,
            next_work=['Restore actual DiskArbitration session connection and volume-reference assignment; retest original mounted-volume APIs and FileCoordination.',
                       'Complete restrictive original Sandbox policy enforcement and external SystemRoot/raw-event coverage; the permissive-policy root is diagnostic only.',
                       'Resume unchanged original Xcode project compilation, Unity/CocoaPods, archive, signing and export; retain the original CI command.'])
(root/'artifacts/unrestricted-sandbox-fsevents-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'hashes; genuine daemon passes FSEvents initialization; volume enumeration remains incomplete')
