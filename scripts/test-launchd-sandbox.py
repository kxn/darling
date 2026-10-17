#!/usr/bin/env python3
"""Run real Mach registration/lookup and, optionally, controlled negative decisions."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, runpy, subprocess
root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(); parser.add_argument('--capture', action='store_true'); parser.add_argument('--baseline',action='store_true'); args=parser.parse_args()
if args.baseline:args.capture=True
mode = 'capture-baseline' if args.baseline else 'capture' if args.capture else 'real'
m = runpy.run_path(str(root / ('scripts/launchd-sandbox-capture-profile.py' if args.capture else 'scripts/launchd-sandbox-source-profile.py')))
p = m['profile'](baseline=True) if args.baseline else m['profile'](); digest=lambda n: hashlib.sha256((root / n).read_bytes()).hexdigest()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/launchd-sandbox-tests'; build.mkdir(exist_ok=True)
source='fixtures/hello/launchd-sandbox.c'; obj=build/'test.o'; binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-Wno-deprecated-declarations','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
live_events='logs/launchd-sandbox-capture-events.log'; events='logs/launchd-sandbox-'+mode+'-events.log'
if args.capture: (root/live_events).write_text('')
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),'capture' if args.capture else 'real']
r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True)
text=r.stdout+r.stderr; log='logs/launchd-sandbox-'+mode+'.log'; (root/log).write_text(text)
match=re.search(r'LAUNCHD_SANDBOX_REGISTRATION_LOOKUP_MESSAGE_AND_EXEC_OK checks=(\d+) capture=(\d+)',text)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),mode=mode,command=command,exit_status=r.returncode,
            source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary.relative_to(root)),
            log=log,log_sha256=digest(log),checks=int(match[1]) if match else 0,
            source_launchd_sandbox=p['source_launchd_sandbox'],runtime_execution_verified=r.returncode==0 and match is not None,
            negative_decisions_test_injected=args.capture,profile_application_implemented=False,full_xcode_build_ready=False)
verified=record['runtime_execution_verified']
if args.capture:
    event_text=(root/live_events).read_text(); (root/events).write_text(event_text)
    rows=[dict(zip(['pid','version','operation','selector','name','status','decision','errno'],row)) for row in re.findall(r'QUERY pid=(\d+) version=(\d+) operation=(\S+) selector=(\d+) name=(\S+) status=(-?\d+) decision=(\d+) errno=(\d+)',event_text)]
    if args.baseline:
        verified=r.returncode==1 and 'deny-reg.0.' in text and 'status=0 expected=1100' in text and 'FAIL line=' in text and not match and not rows
    else:
        parent=re.search(r'LAUNCHD_SANDBOX_PARENT pid=(\d+) version=(\d+)',text)
        child=re.search(r'LAUNCHD_SANDBOX_EXEC_CHILD pid=(\d+) version=(\d+)',text)
        assert parent and child and parent[1]!=child[1] and parent[2]!=child[2]
        assert len(rows)==34 and sum(row['decision']=='1' for row in rows)==6 and sum(row['status']=='-1' and row['errno']=='5' for row in rows)==6
        assert sum(row['selector']=='6' for row in rows)==18 and sum(row['selector']=='7' for row in rows)==16
        for row in rows[:-1]:assert (row['pid'],row['version'])==parent.groups()
        assert (rows[-1]['pid'],rows[-1]['version'])==child.groups()
    record.update(events=events,events_sha256=digest(events),captured_queries=rows,test_only_capture=p['test_only_launchd_sandbox_capture'],baseline=args.baseline)
    if args.baseline:record['baseline_stage']=p['test_only_launchd_sandbox_baseline']
record['expected_result_verified']=verified
(root/('artifacts/launchd-sandbox-'+mode+'-test.json')).write_text(json.dumps(record,indent=2)+'\n')
print(r.returncode,text[-6500:]); assert verified
