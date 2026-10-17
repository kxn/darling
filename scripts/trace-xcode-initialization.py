#!/usr/bin/env python3
"""Read real processes, pipe owners and wait states in one Darling namespace."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parent.parent
command=['python3','scripts/probe-xcode-service-runtime.py','build','--mobileasset-query','--core-volume-diagnostic','--cfprefsd-daemon','--filecoordination','--timeout-seconds','360']
log='logs/xcode-initialization-process-driver.log';snapshots=[];captures=[];last=0;captured=False
with (root/log).open('w') as output:
 proc=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT);started=time.monotonic()
 while proc.poll() is None:
  now=time.monotonic()
  if now-last<3:time.sleep(.15);continue
  last=now;server=[]
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    if (p/'comm').read_text().strip()=='darlingserver':server.append(p)
   except OSError:pass
  if len(server)!=1:continue
  namespace=os.readlink(server[0]/'ns/pid');rows=[]
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    if os.readlink(p/'ns/pid')!=namespace:continue
    row=dict(host_pid=int(p.name),argv=[s.decode(errors='replace') for s in (p/'cmdline').read_bytes().split(b'\0') if s],comm=(p/'comm').read_text().strip(),status=(p/'status').read_text(),stat=(p/'stat').read_text())
    row['fds']={}
    for fd in (p/'fd').iterdir():
     try:row['fds'][fd.name]=dict(target=os.readlink(fd),info=(p/'fdinfo'/fd.name).read_text())
     except OSError:pass
    row['threads']=[]
    for t in (p/'task').iterdir():
     item=dict(host_tid=int(t.name))
     for n in ['stat','wchan','syscall','children']:
      try:item[n]=(t/n).read_text()
      except OSError:pass
     row['threads'].append(item)
    rows.append(row)
   except OSError:pass
  snapshot=dict(checked_at=datetime.now(timezone.utc).isoformat(),elapsed=now-started,pid_namespace=namespace,processes=rows);snapshots.append(snapshot)
  (root/'artifacts/xcode-initialization-live-processes.json').write_text(json.dumps(dict(command=command,snapshots=snapshots),indent=2)+'\n')
  xcode=[r for r in rows if r['argv'] and r['argv'][0]=='/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild']
  children=[r for r in rows if r['argv'] and any(word in r['argv'][0].lower() for word in ['xcrun','swift','securityd','coresimulatorservice'])]
  if xcode and children and now-started>50 and not captured:
   for index,row in enumerate([*xcode,*children]):
    stem='xcode-init-live-'+str(index);r=subprocess.run(['python3','scripts/capture-darling-stacks.py','--stem',stem,'--match',row['argv'][0]],cwd=root,stdout=output,stderr=subprocess.STDOUT)
    captures.append(dict(stem=stem,argv=row['argv'],host_pid=row['host_pid'],capture_exit_status=r.returncode))
   subprocess.run(['python3','scripts/capture-server-microthreads.py','--stem','xcode-init-server-live'],cwd=root,stdout=output,stderr=subprocess.STDOUT)
   captured=True
 status=proc.wait()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,wrapper_exit_status=status,process_snapshots='artifacts/xcode-initialization-live-processes.json',process_snapshots_sha256=digest('artifacts/xcode-initialization-live-processes.json'),captures=captures,log=log,log_sha256=digest(log),direct_cause_proven=False,full_xcode_build_ready=False)
(root/'artifacts/xcode-initialization-process-trace.json').write_text(json.dumps(report,indent=2)+'\n');print('Original build wrapper',status,'snapshots',len(snapshots),'captures',len(captures))
