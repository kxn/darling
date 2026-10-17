#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/mobileasset-query-runtime-profile.py'));p=m['profile']();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();prior=json.loads((root/'artifacts/mobileasset-download-attributes-test.json').read_text());rows=[]
for check in prior['checks']:
 binary=check['binary'];assert digest(binary)==check['binary_sha256'];label=Path(binary).name
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+binary,'/Volumes/SystemRoot/workspace/'+p['source_mobileasset_query']['framework']];command[3]='100'
 a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/mobileasset-query-regression-'+label+'.log';(root/log).write_text(text)
 marker='MOBILEASSET_PALLAS_REAL_EIGHT_THREADS_64_INDEPENDENT_XPC_REQUEST_REPLY_CYCLES_OK' if label=='mobileasset-pallas' else 'PALLAS_REAL_XPC_PEER_TEARDOWN_ONE_RETRY_SUCCESS_AND_TWO_ATTEMPT_LIMIT_OK'
 rows.append(dict(binary=binary,binary_sha256=digest(binary),command=command,exit_status=a.returncode,log=log,log_sha256=digest(log),verified=a.returncode==0 and marker in text));print(label,a.returncode,text[-1500:],flush=True);assert rows[-1]['verified']
(root/'artifacts/mobileasset-query-regressions.json').write_text(json.dumps(dict(checked_at=datetime.now(timezone.utc).isoformat(),source_mobileasset_query=p['source_mobileasset_query'],source_runtime=p['source_runtime'],prior_report='artifacts/mobileasset-download-attributes-test.json',prior_report_sha256=digest('artifacts/mobileasset-download-attributes-test.json'),results=rows,verified=True,actual_Apple_daemon=False),indent=2)+'\n')
