#!/usr/bin/env python3
"""Exercise the new launchd with real XPC, native profile uploads and Xcode."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy, subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/launchd-sandbox-source-profile.py'));p=m['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
guest='/Volumes/SystemRoot/workspace/'
loop=json.loads((root/'artifacts/xpc-loopback-sent-fixed.json').read_text())
upload=json.loads((root/'artifacts/native-sandbox-policy-upload-test.json').read_text())
for record in [loop,upload]:assert digest(record['binary'])==record['binary_sha256']
policies=json.loads((root/'artifacts/native-sandbox-policy-corpus.json').read_text())
for item in policies['policies'].values():assert digest(item['binary'])==item['sha256']
cases=[('xpc-loopback',[guest+loop['binary']],'XPC_REAL_16_LOOPBACK_CHECKINS_256_REPLY_PAYLOADS_AND_CANCELLATION_OK'),
       ('native-policy-upload',[guest+upload['binary'],*[guest+v['binary'] for v in policies['policies'].values()]],'SANDBOX_UPLOAD_NATIVE_ABI_AND_ATOMIC_FAILURE_OK checks=216 uploads=29'),
       ('xcode-version',['/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild','-version'],'Xcode 26.6'),
       ('xcode-showsdks',[],'SERVICE_RUNTIME_XCODE_STATUS 0')]
results=[]
for name,argv,marker in cases:
    if name=='xcode-showsdks':
        # SDK discovery uses the real preference and LaunchServices services.
        # The direct call without service setup is retained as a failed
        # control in artifacts/launchd-sandbox-direct-query-control-history.
        command=['python3',str(root/'scripts/probe-xcode-service-runtime.py'),
                 '--launchd-sandbox','--cfprefsd-daemon','--timeout-seconds','40','showsdks']
        r=subprocess.run(command,capture_output=True,text=True)
    else:
        command=p['command'][:-2]+argv;command[3]='40'
        r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True)
    text=r.stdout+r.stderr;log='logs/launchd-sandbox-regression-'+name+'.log';(root/log).write_text(text)
    verified=r.returncode==0 and marker in text
    results.append(dict(name=name,command=command,exit_status=r.returncode,marker=marker,verified=verified,log=log,log_sha256=digest(log)))
    print(name,r.returncode,'verified',verified,text[-1800:],flush=True)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),checks=results,
            source_launchd_sandbox=p['source_launchd_sandbox'],source_runtime=p['source_runtime'],
            runtime_execution_verified=all(row['verified'] for row in results),
            original_policy_application_still_unsupported=True,full_xcode_build_ready=False)
(root/'artifacts/launchd-sandbox-regression.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['runtime_execution_verified']
