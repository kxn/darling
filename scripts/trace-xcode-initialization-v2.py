#!/usr/bin/env python3
"""Capture the original build's nested-namespace descendants and pipe waits."""
from pathlib import Path
import hashlib,json,subprocess,time
root=Path(__file__).resolve().parent.parent
command=['python3','scripts/probe-xcode-service-runtime.py','build','--mobileasset-query','--core-volume-diagnostic','--cfprefsd-daemon','--filecoordination','--timeout-seconds','420']
log='logs/xcode-initialization-v2-driver.log';captures=[]
with (root/log).open('w') as output:
 proc=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT)
 while proc.poll() is None:
  live=False
  for path in Path('/proc').iterdir():
   if not path.name.isdigit():continue
   try:
    if (path/'comm').read_text().strip()=='darlingserver':live=True;break
   except OSError:pass
  if live:break
  time.sleep(.2)
 if proc.poll() is None:
  a=subprocess.run(['python3','scripts/capture-darling-process-tree.py','--stem','xcode-init-v2-descendants','--wait-xcrun','180','--stacks'],cwd=root,stdout=output,stderr=subprocess.STDOUT);captures.append(a.returncode)
  end=time.monotonic()+20
  while proc.poll() is None and time.monotonic()<end:time.sleep(.2)
  if proc.poll() is None:
   a=subprocess.run(['python3','scripts/capture-darling-process-tree.py','--stem','xcode-init-v2-descendants-later','--stacks'],cwd=root,stdout=output,stderr=subprocess.STDOUT);captures.append(a.returncode)
 status=proc.wait()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
(root/'artifacts/xcode-initialization-v2-trace.json').write_text(json.dumps(dict(command=command,wrapper_exit_status=status,capture_statuses=captures,log=log,log_sha256=digest(log)),indent=2)+'\n');print('Original wrapper',status,'capture statuses',captures)
