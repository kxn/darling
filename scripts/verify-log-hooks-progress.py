#!/usr/bin/env python3
"""Run serial Darling regressions and collect the genuine Xcode loader status.

A recorded SDK loader failure is not a passing build or goal completion.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent
checks=[
 ('log-hooks',['scripts/test-log-hooks.py'],[0]),
 ('container-persona',['scripts/test-container-persona.py'],[0]),
 ('libtrace-hooks-regression',['scripts/test-libtrace-source.py','--hooks'],[0]),
 ('container-persona-xcode-version',['scripts/probe-native-layer-xcode.py','--container-persona','version'],[0]),
 ('container-persona-xcode-showsdks',['scripts/probe-native-layer-xcode.py','--container-persona','showsdks'],[0,255]),
 ('native-lsd-container-persona',['scripts/probe-native-lsd.py','--source-libtrace','--user-local-dir-export','--rootless-datavault-export','--sandbox-container','--with-dirhelper','--native-sysdir','--metadata-kernel','--native-container-manager','--mount-path-kernel','--layer-log','--native-message','--latest-profile','container-persona'],[0])]
results=[]
for name,args,allowed in checks:
 log='logs/'+name+'-driver.log'
 with (root/log).open('w') as stream:r=subprocess.run(['python3',*args],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
 results.append(dict(name=name,command=['python3',*args],exit_status=r.returncode,log=log,log_sha256=hashlib.sha256((root/log).read_bytes()).hexdigest()))
 print(name,'exit_status='+str(r.returncode),flush=True)
 if r.returncode not in allowed:raise SystemExit(r.returncode or 1)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),checks=results,all_execution_regressions_passed=True,sdk_listing_succeeded=results[4]['exit_status']==0,full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/log-hooks-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print('Collected source callback/ASL/persona/LaunchServices regressions and genuine Xcode status',flush=True)
