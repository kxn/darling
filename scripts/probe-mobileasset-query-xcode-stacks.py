#!/usr/bin/env python3
"""Capture live original Xcode after the query continuation has completed."""
from pathlib import Path
import hashlib,json,subprocess,time
root=Path(__file__).resolve().parent.parent
command=['python3','scripts/probe-xcode-service-runtime.py','build','--mobileasset-query','--core-volume-diagnostic','--cfprefsd-daemon','--filecoordination','--timeout-seconds','240']
log='logs/mobileasset-query-xcode-stacks-driver.log'
with (root/log).open('w') as output:
 proc=subprocess.Popen(command,cwd=root,stdout=output,stderr=subprocess.STDOUT);started=time.monotonic();capture=None
 while proc.poll() is None:
  names=sorted((root/'logs').glob('xcode-service-runtime-mobileasset-query-diagnostic-build-*.log'))
  for name in names:
   if name.stat().st_mtime<time.time()-(time.monotonic()-started)-1:continue
   if 'Failed querying assets for assetType' in name.read_text(errors='replace') and time.monotonic()-started>35:
    capture=subprocess.run(['python3','scripts/capture-darling-stacks.py','--stem','mobileasset-query-xcode-live'],cwd=root,stdout=output,stderr=subprocess.STDOUT);break
  if capture is not None:break
  time.sleep(.2)
 if capture is not None:
  # Additional snapshot later distinguishes a transient callback from a stable wait.
  end=time.monotonic()+20
  while proc.poll() is None and time.monotonic()<end:time.sleep(.2)
  if proc.poll() is None:subprocess.run(['python3','scripts/capture-darling-stacks.py','--stem','mobileasset-query-xcode-live-later'],cwd=root,stdout=output,stderr=subprocess.STDOUT)
 status=proc.wait()
print('Original project wrapper status',status,'live capture',None if capture is None else capture.returncode)
