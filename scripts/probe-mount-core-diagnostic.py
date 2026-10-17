#!/usr/bin/env python3
"""Mount/remount/unmount tmpfs only inside this invocation's private namespace."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,time
root=Path(__file__).resolve().parent.parent
command=['python3',str(root/'scripts/probe-diskarbitration-service.py'),'--iokitd-runtime','mounts','--configd','--mount-client','--coreservices','--unrestricted-diagnostic','--volume-probe','--tag','real-mount-core-diagnostic']
output=root/'logs/real-mount-core-driver.log';log=root/'logs/diskarbitration-service-real-mount-core-diagnostic.log';actions=[]
log.write_text('')
with output.open('w') as stream:
 proc=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT)
 def wait_for(marker):
  deadline=time.monotonic()+35
  while True:
   text=log.read_text() if log.exists() else ''
   if marker in text:return text
   if proc.poll() is not None:raise RuntimeError('Probe terminated before '+marker+'; '+output.read_text()[-1500:])
   if time.monotonic()>deadline:raise RuntimeError('Timeout waiting for '+marker)
   time.sleep(.05)
 text=wait_for('MOUNT_NOTIFY_READY path=');path=re.search(r'MOUNT_NOTIFY_READY path=(/private/tmp/LinuxMountProbe-\d+)',text)[1]
 pids=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdigit():continue
  try:
   args=(entry/'cmdline').read_bytes().split(b'\0')
   if args[0]==b'/Volumes/SystemRoot/workspace/runtime/diskarbitration-service/mount-client':pids.append(entry.name)
  except OSError:pass
 assert len(pids)==1,pids
 pid=pids[0];user=str(Path('/proc/'+pid+'/ns/user').readlink());mount=str(Path('/proc/'+pid+'/ns/mnt').readlink())
 assert user!=str(Path('/proc/self/ns/user').readlink()) and mount!=str(Path('/proc/self/ns/mnt').readlink())
 target=re.search(r'MOUNT_NOTIFY_READY path=\S+ linux_path=(\S+)',text)[1]
 assert target.endswith(path),target
 enter=['nsenter','--target',pid,'--user','--preserve-credentials','--mount','--root','--wd=/']
 diagnostics=dict(pid=pid,target=target,root=str(Path('/proc/'+pid+'/root').readlink()),cwd=str(Path('/proc/'+pid+'/cwd').readlink()),mountinfo=Path('/proc/'+pid+'/mountinfo').read_text())
 (root/'logs/real-mount-core-namespace-diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
 def execute(args):
  a=subprocess.run(enter+args,capture_output=True,text=True,timeout=10);actions.append(dict(command=enter+args,exit_status=a.returncode,output=a.stdout+a.stderr));assert a.returncode==0,actions[-1]
 try:
  execute(['/bin/mount','-t','tmpfs','-o','size=1m,nosuid,nodev','tmpfs',target]);wait_for('MOUNT_NOTIFY_ADD')
  execute(['/bin/mount','-o','remount,ro,nosuid,nodev',target]);wait_for('MOUNT_NOTIFY_UPDATE')
  execute(['/bin/umount',target]);wait_for('MOUNT_NOTIFY_REMOVE')
 finally:
  # Unmounting an already unmounted test target is harmless; never address a host path.
  subprocess.run(enter+['/bin/umount',target],capture_output=True,text=True,timeout=10)
 status=proc.wait(timeout=45)
text=log.read_text();match=re.search(r'NATIVE_REAL_LINUX_MOUNT_UPDATE_UNMOUNT_NOTIFICATIONS_OK checks=(\d+) appeared=(\d+)',text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),driver_command=command,driver_exit_status=status,source='fixtures/hello/mount-notification.c',source_sha256=digest('fixtures/hello/mount-notification.c'),log=str(log.relative_to(root)),log_sha256=digest(log),actions=actions,namespace_user=user,namespace_mount=mount,private_user_and_mount_namespaces_verified=True,host_namespace_changed=False,actual_tmpfs_mount_remount_unmount=True,notify_post_used_to_fabricate_events=False,checks=int(match[1]) if match else 0,actual_original_DA_appeared=int(match[2]) if match else 0,runtime_execution_verified=status==0 and match is not None,test_only_permissive_coreservices_policy=True,native_fileidtree_volumes=int(re.search(r'FILEIDTREE_MOUNT_POINTS status=0 count=(\d+)',text)[1]),native_fileidtree_cached_port=int(re.search(r'cached_port=(\d+)',text)[1]),full_xcode_build_ready=False)
(root/'artifacts/real-mount-core-diagnostic.json').write_text(json.dumps(d,indent=2)+'\n');print(text[-5000:]);assert d['runtime_execution_verified']
