#!/usr/bin/env python3
"""Record the real configd repair and the next original disk-daemon failure."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/iokitd-power-progress.json').exists():
    print('Preserving the newer source iokitd power checkpoint')
    raise SystemExit(0)
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
build=report('artifacts/log-compose-source-build.json');assert build['complete_source_files']==9 and build['full_libtrace_source_build']
for group in ['source_files','source_headers']:
    for name,sha in build[group].items():add('vendor/darling/src/external/libtrace/'+name,sha)
for name in ['artifacts/log-compose-runtime-stage.json','artifacts/log-compose-diagnostic-stage.json']:report(name)
test=report('artifacts/log-send-compose-test.json');assert test['runtime_execution_verified'] and test['checks']==2295 and test['oracle_cases']==192
assert test['oracle_callees_replaced_by_spies'] and not test['native_full_logging_backend_executed']
regression=report('artifacts/log-compose-regressions.json');assert regression['runtime_execution_verified']
assert [c['checks'] for c in regression['checks']]==[269,1642]
stems=['no-daemon-baseline','initial','debug','trace-startup','system-services','configd-startup','configd-source-compose','disk-after-configd','no-daemon-store-notification','no-daemon-power-root']
for stem in stems:
    d=report('artifacts/diskarbitration-service-'+stem+'.json')
    assert not d['daemon_binary_modified']
    if stem in ['trace-startup','configd-startup','configd-source-compose','disk-after-configd']:
        report('artifacts/diskarbitration-service-'+stem+'-images.json');add('logs/diskarbitration-service-'+stem+'.resolved.log')
old=(root/'logs/diskarbitration-service-configd-startup.resolved.log').read_text()
assert '__os_log_send_and_compose_impl+0x1f' in old and 'SIGABRT' in old
new=(root/'logs/diskarbitration-service-configd-source-compose.resolved.log').read_text()
assert '_CFRunLoopRun' in new and '0x100002046' in new and 'SIGABRT' not in new
store=read('artifacts/diskarbitration-service-no-daemon-store-notification.json')
assert store['native_store_functional'] and store['exit_status']==0
text=(root/store['log']).read_text();assert 'NATIVE_SYSTEMCONFIGURATION_REAL_CONFIGD_STORE_AND_NOTIFICATION_OK checks=16 notifications=1' in text
assert 'foundation-native-framework-stage/SystemConfiguration.framework' in text
trace=(root/'logs/diskarbitration-service-disk-after-configd.gdb.log').read_text()
assert re.search(r'dynamic_store_create_return rdi=0x[0-9a-f]+ rax=0x[1-9a-f][0-9a-f]+',trace)
assert 'system_power_return' in trace and 'could not register for system power notifications' in trace
power=read('artifacts/diskarbitration-service-no-daemon-power-root.json');text=(root/power['log']).read_text()
assert 'IOPOWER_MASTER status=0 port=' in text and 'IOPOWER_ROOT_DOMAIN object=0' in text
assert 'IOPOWER_REGISTRATION connection=0 notifier=0 port=0x0' in text
assert 'IOPOWER_PROBE_RETURNED' in text
regressions={}
for mode in ['version','showsdks']:
    names=list((root/'artifacts').glob('xcode-service-runtime-log-compose-'+mode+'-*.json'));assert len(names)==1,names
    name=str(names[0].relative_to(root));d=report(name)
    assert d['exit_status']==0 and d['UTI_preflight_verified']
    assert 'SERVICE_RUNTIME_XCODE_STATUS 0' in (root/d['log']).read_text();regressions[mode]=name
history=read('artifacts/diskarbitration-initial-history/manifest.json');add('artifacts/diskarbitration-initial-history/manifest.json')
for item in history.values():add(item['archived'],item['sha256'])
repository='vendor/darling/src/external/libtrace';paths=['libsystem_trace/os_log.c','libsystem_trace/stubs.c','include/os/log_private.h']
patch=''
for name in paths:
    old=(root/history[repository+'/'+name]['archived']).read_text().splitlines(True)
    patch+=''.join(difflib.unified_diff(old,(root/repository/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
out='artifacts/libtrace-send-compose-source.patch';(root/out).write_text(patch)
subprocess.run(['git','-C',str(root/repository),'apply','--reverse','--check',str(root/out)],check=True);add(out)
for name in ['scripts/build-libtrace-source.py','scripts/stage-log-compose-runtime.py','scripts/log-compose-runtime-profile.py',
             'scripts/log-enablement-profile.py','scripts/test-log-send-compose.py','scripts/test-log-compose-regressions.py',
             'scripts/probe-diskarbitration-service.py','scripts/probe-xcode-service-runtime.py','scripts/resolve-evidence-history.py',
             'scripts/record-diskarbitration-progress.py','scripts/trace-compat.c',
             'fixtures/hello/log-send-compose.m','fixtures/hello/systemconfiguration-store.c','fixtures/hello/iokit-power-probe.c','fixtures/hello/diskarbitration-service.c',
             'runtime/log-compose-tests/native-compose-oracle.h','runtime/log-compose-tests/existing-pack.m',
             'logs/log-send-compose-original-full-disassembly.log','logs/diskarbitration-native-disassembly.log',
             'logs/diskarbitration-daemon-original-disassembly.log','logs/configd-original-disassembly.log',
             'vendor/darling/src/external/iokitd/src/IORegistryEntry.mm','vendor/darling/src/external/iokitd/src/main.mm',
             'vendor/darling/src/external/iokitd/src/ServiceRegistry.mm','vendor/darling/src/external/IOKitUser/pwr_mgt.subproj/IOPMLib.c']:
    add(name)
    if name.endswith('.py'):ast.parse((root/name).read_text())
commit=subprocess.check_output(['git','-C',str(root/'vendor/darling/src/external/iokitd'),'rev-parse','HEAD'],text=True).strip()
assert commit=='5549ac4cd2db923c256f016a1381b3bfb716730a'
p=runpy.run_path(str(root/'scripts/log-compose-runtime-profile.py'))['profile']()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,
            previous_goal_turn_classification='progress',current_goal_turn_classification='progress',
            source_runtime=p['source_runtime'],source_log_compose=p['source_log_compose'],full_trace_source_files=9,
            send_compose_checks=2295,original_wrapper_ABI_cases=192,wrapper_oracle_replaces_callees=True,
            full_native_log_backend_parity_verified=False,existing_pack_regression_checks=269,existing_hook_regression_checks=1642,
            original_configd_binary_modified=False,original_configd_logging_abort_resolved=True,
            native_SystemConfiguration_store_checks=16,native_SystemConfiguration_notifications=1,
            native_SystemConfiguration_provider=True,original_diskarbitrationd_dynamic_store_session_created=True,
            original_DiskArbitration_client_session_created=False,original_diskarbitrationd_exit_status=70,
            next_original_daemon_failure='IORegisterForSystemPower returns 0 because the IOPower:/IOPowerConnection/IOPMrootDomain registry service is absent.',
            real_iokit_main_port_lookup_succeeded=True,IOPMrootDomain_present=False,system_power_notifications_implemented=False,
            iokitd_source_commit=commit,production_Sandbox_policy_resources_modified=False,default_entry_promoted=False,
            original_xcode_regressions=regressions,evidence=evidence,
            next_work=['Implement the missing power-domain registry/service, real event subscription and client lifetime behavior in Darling iokitd; preserve unsupported operations as errors. Rebuild and verify actual IORegisterForSystemPower before retrying the original disk daemon.',
                       'Restore original DiskArbitration session/disk description and volume-reference assignment, then actual FileIDTree/CF mounted-volume enumeration and FileCoordination.',
                       'Complete original restrictive Sandbox enforcement and external SystemRoot event coverage; proceed through unchanged Xcode compilation, Unity/CocoaPods, archive, signing and export.'])
(root/'artifacts/diskarbitration-log-compose-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'hashes; original configd IPC works; original disk daemon requires the missing power domain')
