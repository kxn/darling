#!/usr/bin/env python3
"""Repeat the real queue/run-loop/lifecycle test after the lock-order fixes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/fsevents-flush-profile.py'));p=m['profile']();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();checks=[]
for i in range(3):
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/fsevents-flush'];log='logs/fsevents-flush-repeat-'+str(i)+'.log'
 with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
 verified=r.returncode==0 and 'SOURCE_FSEVENTS_FLUSH_ALL_CHECKED_SEMANTICS_OK checks=88' in (root/log).read_text();checks.append(dict(command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),verified=verified));print('repeat',i,r.returncode,verified,flush=True)
 if not verified:break
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'binary_sha256':digest('artifacts/fsevents-flush'),'source_sha256':digest('fixtures/hello/fsevents-flush.m'),'all_three_repeats_verified':len(checks)==3 and all(c['verified'] for c in checks),'initial_expanded_test_timeout_log':'logs/fsevents-flush-first-sync-timeout.log','initial_expanded_test_timeout_log_sha256':digest('logs/fsevents-flush-first-sync-timeout.log'),'scope':'Earlier timed-run-loop clients hung after the foreign flusher logged completion. The final foreign-thread flush test explicitly stops its servicing run loop on completion. The unresolved complex timed-run-loop behavior is preserved separately; these repetitions do not establish that it is fixed.'}
(root/'artifacts/fsevents-flush-repeats.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['all_three_repeats_verified'] else 1)
