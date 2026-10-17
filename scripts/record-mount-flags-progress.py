#!/usr/bin/env python3
"""Record native mount semantics and real mount notifications without claiming a build."""
from pathlib import Path
from datetime import datetime,timezone
import ast,difflib,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
if (root/'artifacts/s2c-lifecycle-progress.json').exists():
 print('Preserving the newer source S2C lifecycle checkpoint');raise SystemExit(0)
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
report('artifacts/iokitd-matching-progress.json')
kernel=report('artifacts/mount-paths-kernel-build.json');assert kernel['complete_source_files']==879 and kernel['full_libsystem_kernel_source_build']
notify=report('artifacts/notifyd-mounts-build.json');assert notify['complete_source_files']==7 and notify['full_notifyd_source_build']
assert not notify['XPC_matching_publisher_implemented']
stage=report('artifacts/mount-flags-stage.json')
flags=report('artifacts/mount-flags-native-test.json');assert flags['runtime_execution_verified'] and flags['checks']==79
parser=report('artifacts/mountwatch-state-test.json');assert parser['checks']==137
events=report('artifacts/real-mount-notifications-test.json');assert events['runtime_execution_verified'] and events['checks']==34
assert events['actual_tmpfs_mount_remount_unmount'] and not events['notify_post_used_to_fabricate_events']
assert events['private_user_and_mount_namespaces_verified'] and not events['host_namespace_changed']
daemon=report('artifacts/diskarbitration-service-real-mount-events.json');assert daemon['exit_status']==0 and not daemon['daemon_binary_modified']
text=(root/daemon['log']).read_text()
for path in ['/','/Volumes/SystemRoot','/Volumes/SystemRoot/']:
 assert re.search(r'MOUNT_DA_VOLUME path='+re.escape(path)+r' disk=0x[1-9a-f][0-9a-f]* description=0x[1-9a-f][0-9a-f]*',text)
assert '"LastExitStatus" = 0' in text.split('+ launchctl list com.apple.diskarbitrationd')[-1]
volumes=report('artifacts/mount-volumes-native-probe.json');assert volumes['probe_returned'] and volumes['fileidtree_volume_count']==0
regressions=report('artifacts/mount-runtime-regressions.json');assert regressions['runtime_execution_verified']
xcode={}
for mode in ['version','showsdks','build']:
 paths=list((root/'artifacts').glob('xcode-service-runtime-mount-flags-'+mode+'-*.json'));assert len(paths)==1
 name=str(paths[0].relative_to(root));d=report(name);assert d['UTI_preflight_verified']
 if mode!='build':assert d['exit_status']==0 and d['xcode_process_returned']
 xcode[mode]=dict(report=name,sha256=digest(name),exit_status=d['exit_status'],xcode_process_returned=d['xcode_process_returned'])
diagnostic=None
if (root/'artifacts/real-mount-core-diagnostic.json').exists():
 diagnostic=report('artifacts/real-mount-core-diagnostic.json')
 report('artifacts/mount-volumes-diagnostic-stage.json');report('artifacts/diskarbitration-service-real-mount-core-diagnostic.json')
for repo,name in [('xnu','artifacts/xnu-mount-flags-source.patch'),('libnotify','artifacts/notifyd-mounts-source.patch')]:
 directory=root/'vendor/darling/src/external'/repo
 patch=subprocess.check_output(['git','-C',str(directory),'diff','HEAD'],text=True)
 for path in subprocess.check_output(['git','-C',str(directory),'ls-files','--others','--exclude-standard'],text=True).splitlines():
  patch+=''.join(difflib.unified_diff([],(directory/path).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+path))
 (root/name).write_text(patch);add(name)
 subprocess.run(['git','-C',str(directory),'apply','--reverse','--check',str(root/name)],check=True)
scripts=['scripts/build-notifyd-mounts-source.py','scripts/stage-mount-flags-runtime.py','scripts/mount-flags-runtime-profile.py','scripts/test-mount-flags-native.py','scripts/test-mountwatch-state.py','scripts/test-real-mount-notifications.py','scripts/probe-mount-volumes.py','scripts/test-mount-runtime-regressions.py','scripts/stage-mount-volumes-diagnostic.py','scripts/mount-volumes-diagnostic-profile.py','scripts/probe-mount-core-diagnostic.py','scripts/probe-diskarbitration-service.py','scripts/probe-xcode-service-runtime.py','scripts/fsevents-device-runtime-profile.py','scripts/workqueue-stack-runtime-profile.py','scripts/record-mount-flags-progress.py','scripts/resolve-evidence-history.py']
for name in scripts:
 add(name);ast.parse((root/name).read_text())
for name in ['fixtures/hello/mount-flags.c','fixtures/hello/mount-notification.c','fixtures/hello/mountwatch-state.c','logs/diskarbitration-client-original-disassembly.log','logs/diskarbitration-daemon-original-disassembly.log','logs/real-mount-namespace-diagnostics.json']:
 add(name)
apple='vendor/apple-DiskArbitration';commit=subprocess.check_output(['git','-C',str(root/apple),'rev-parse','HEAD'],text=True).strip()
assert commit=='a542bda934211dc3c301bfdcc7f21349c4164a85'
for n in ['DiskArbitration/DADisk.c','diskarbitrationd/DAInternal.c','diskarbitrationd/DAMain.c','diskarbitrationd/DAServer.c']:add(apple+'/'+n)
p=runpy.run_path(str(root/'scripts/mount-flags-runtime-profile.py'))['profile']()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,
 previous_goal_turn_classification='no_progress',current_goal_turn_classification='progress',source_runtime=p['source_runtime'],source_mount_flags=stage,
 source_kernel_files=879,source_notifyd_files=7,native_mount_flags_checks=79,mountinfo_parser_checks=137,
 real_mount_notifications_checks=34,actual_original_DA_appeared=events['actual_original_DA_appeared'],
 actual_tmpfs_mount_remount_unmount_verified=True,fabricated_mount_events=False,initial_snapshot_posted_as_event=False,
 initial_existing_volume_discovery_verified=False,mount_event_backend='Linux mountinfo snapshots at 250ms; transient changes between samples may be missed',
 original_root_and_SystemRoot_descriptions_after_real_mount_verified=True,original_DiskArbitration_binary_modified=False,
 original_configd_and_diskarbitrationd_alive_after_client=True,canonical_SystemRoot_mount_path_verified=True,
 original_FileIDTree_volume_count=volumes['fileidtree_volume_count'],original_CF_volume_enumeration_verified=False,
 original_xcode_probes=xcode,actual_project_compilation_started=False,diagnostic_core_services=diagnostic,
 strict_Sandbox_enforcement_verified=False,actual_Linux_block_media_discovery_implemented=False,notifyd_XPC_matching_publisher_implemented=False,
 current_observed_failure='Original FileIDTree still returns zero volumes and original CF enumerator reports Cocoa 256. Strict original project build does not reach compilation; native DiskArbitration root/SystemRoot descriptions now work after a genuine mount event.',
 evidence=evidence,next_work=[
 'Restore real startup mounted-volume discovery and native legacy volume references in CoreServices/FileIDTree; root and SystemRoot descriptions currently verified only after actual mount activity.',
 'Finish genuine restrictive Sandbox enforcement and original CoreServices/FileCoordination services, then retry unchanged Xcode project compilation and Unity/CocoaPods, archive, signing and export.',
 'Complete Linux media discovery/hotplug, XPC event publishing and remaining FSEvents/power behavior. Mount polling is verified for actual tmpfs mount/remount/unmount, not every transient filesystem event.'
 ])
(root/'artifacts/mount-flags-progress.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded',len(evidence),'hashes; native root/SystemRoot descriptions recovered; full Xcode build remains incomplete')
