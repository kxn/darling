#!/usr/bin/env python3
"""Stop the unchanged original build at its first Linux SIGSEGV."""
from pathlib import Path
import hashlib,json,subprocess,time
root=Path(__file__).resolve().parent.parent
command=['python3','scripts/probe-xcode-service-runtime.py','build','--mobileasset-query','--core-volume-diagnostic','--cfprefsd-daemon','--filecoordination','--timeout-seconds','500']
log='logs/xcode-input-fault-driver.log';capture=None
with (root/log).open('w') as output:
 proc=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT)
 while proc.poll() is None:
  found=[]
  for path in Path('/proc').iterdir():
   if not path.name.isdigit():continue
   try:
    argv=(path/'cmdline').read_bytes().split(b'\0')
    if argv[0]==b'/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild':found.append(path.name)
   except OSError:pass
  if len(found)==1:break
  time.sleep(.1)
 if proc.poll() is None:
  capture=subprocess.run(['python3','scripts/capture-darling-stacks.py','--stem','xcode-input-options-fault','--wait-signal','SIGSEGV'],cwd=root,stdout=output,stderr=subprocess.STDOUT)
 status=proc.wait()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
(root/'artifacts/xcode-input-fault-capture.json').write_text(json.dumps(dict(command=command,wrapper_exit_status=status,capture_exit_status=None if capture is None else capture.returncode,log=log,log_sha256=digest(log)),indent=2)+'\n');print('Original wrapper',status,'capture',None if capture is None else capture.returncode)
