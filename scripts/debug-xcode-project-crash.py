#!/usr/bin/env python3
"""Attach before the genuine project-build fault and retain the actual registers."""
from pathlib import Path
import argparse,json, posixpath, subprocess, time
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--log-pack',action='store_true');args=parser.parse_args()
stem='xcode-project-pack-crash' if args.log_pack else 'xcode-project-crash'
script='scripts/capture-darling-stacks.py'
probe=subprocess.Popen(['python3','scripts/probe-xcode-service-runtime.py',*(['--log-pack'] if args.log_pack else []),'build'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
deadline=time.monotonic()+45
capture=None
while probe.poll() is None and time.monotonic()<deadline:
    rows=subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()
    matches=[row.split()[0] for row in rows if len(row.split(maxsplit=1))==2 and posixpath.normpath(row.split(maxsplit=1)[1].split()[0])=='/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild']
    if matches:
        assert len(matches)==1
        with (root/('logs/'+stem+'-capture-driver.log')).open('w') as log:
            capture=subprocess.run(['python3',script,'--wait-segv','--stem',stem],cwd=root,stdout=log,stderr=subprocess.STDOUT)
        break
    time.sleep(0.02)
result=probe.wait(timeout=70)
record={'project_probe_exit_status':result,'capture_exit_status':capture.returncode if capture else None,'capture_driver_log':'logs/'+stem+'-capture-driver.log','full_xcode_build_ready':False}
(root/('artifacts/'+stem+'-capture.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record));raise SystemExit(0 if capture and capture.returncode==0 else 1)
