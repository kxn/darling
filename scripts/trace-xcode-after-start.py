#!/usr/bin/env python3
"""Attach Linux process/socket tracing only after original Xcode has started."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,time
root=Path(__file__).resolve().parent.parent
command=['python3','scripts/probe-xcode-service-runtime.py','build','--mobileasset-query','--core-volume-diagnostic','--cfprefsd-daemon','--filecoordination','--timeout-seconds','480']
log='logs/xcode-after-start-driver.log';tracer=None;selected=[];captures=[]
with (root/log).open('w') as output:
 proc=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT)
 while proc.poll() is None:
  xcodes=[]
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    argv=(p/'cmdline').read_bytes().split(b'\0')
    if argv[0]==b'/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild':xcodes.append(int(p.name))
   except OSError:pass
  if len(xcodes)==1:break
  time.sleep(.1)
 if proc.poll() is None and xcodes:
  subprocess.run(['python3','scripts/capture-darling-process-tree.py','--stem','xcode-after-start-initial'],cwd=root,stdout=output,stderr=subprocess.STDOUT)
  tree=json.loads((root/'artifacts/xcode-after-start-initial-process-tree.json').read_text());rows=tree['snapshots'][-1]['processes']
  selected=[r['host_pid'] for r in rows if r['argv'] and (r['argv'][0]=='/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild' or (r['argv'][0]=='/bin/bash' and len(r['argv'])>1 and 'xcode-service-runtime-' in r['argv'][1]))]
  # The per-command shellspawn worker is the guest bash's direct Linux parent.
  for row in rows:
   if row['host_pid'] in selected and row['argv'][0]=='/bin/bash':selected.append(row['host_parent'])
  # Observe the Linux CLI's control-socket read, without tracing the server.
  server=next(r for r in rows if r['comm']=='darlingserver');namespace=server['pid_namespace']
  import os
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    if (p/'comm').read_text().strip()=='darling' and os.readlink(p/'ns/pid')==namespace:selected.append(int(p.name))
   except OSError:pass
  selected=sorted(set(selected));trace=[str(root/'runtime/tools/strace-package/unpacked/usr/bin/strace'),'-ff','-tt','-s','160','-e','trace=process,read,close,shutdown,poll','-e','signal=all','-o',str(root/'logs/xcode-after-start.strace')]
  for pid in selected:trace+=['-p',str(pid)]
  tracer=subprocess.Popen(trace,cwd=root,stdout=output,stderr=subprocess.STDOUT)
  a=subprocess.run(['python3','scripts/capture-darling-process-tree.py','--stem','xcode-after-start-children','--wait-xcrun','45'],cwd=root,stdout=output,stderr=subprocess.STDOUT);captures.append(a.returncode)
 status=proc.wait()
 if tracer:
  try:trace_status=tracer.wait(timeout=10)
  except subprocess.TimeoutExpired:tracer.terminate();trace_status=tracer.wait()
 else:trace_status=None
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,wrapper_exit_status=status,attached_host_pids=selected,tracer_exit_status=trace_status,capture_statuses=captures,log=log,log_sha256=digest(log))
(root/'artifacts/xcode-after-start-trace.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
