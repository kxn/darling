#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/cryptokit-15-profile.py'));p=m['profile']();checks=[]
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
for item in p['native_cryptokit_15']['images']:
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/runtime/device-identity-native/load',item['provider']]
    r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr;log='logs/cryptokit-15-'+Path(item['provider']).name+'-load.log';(root/log).write_text(text)
    passed=r.returncode==0 and 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in text
    checks.append(dict(provider=item['provider'],command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),native_dlopen_verified=passed));print(item['provider'],r.returncode,text,flush=True)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],corecrypto=p['source_corecrypto_hkdf'],stage=p['native_cryptokit_15'],checks=checks,all_selected_images_load=all(c['native_dlopen_verified'] for c in checks),software_crypto_verified=False,SecureEnclave_verified=False)
(root/'artifacts/cryptokit-15-load.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['all_selected_images_load'] else 1)
