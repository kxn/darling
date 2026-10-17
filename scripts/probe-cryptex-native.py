#!/usr/bin/env python3
"""Execute real dlopen for the selected original Cryptex dependency closure."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--workqueue-stack',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/workqueue-stack-runtime-profile.py' if args.workqueue_stack else 'scripts/cryptex-native-profile.py')));p=m['profile'](False);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();rows=[]
prefix='workqueue-cryptex-native' if args.workqueue_stack else 'cryptex-native'
for name,path in [('crypto42','/usr/lib/libcrypto.42.dylib'),('authinstall','/usr/lib/libauthinstall.dylib'),('interface','/usr/lib/libcryptex_interface.dylib'),('core','/usr/lib/libcryptex_core.dylib'),('cryptex','/usr/lib/libcryptex.dylib'),('trust','/System/Library/PrivateFrameworks/TrustEvaluationAgent.framework/Versions/A/TrustEvaluationAgent'),('swift-foundation','/usr/lib/swift/libswiftSystem_Foundation.dylib')]:
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/runtime/device-identity-native/load',path];log='logs/'+prefix+'-'+name+'-load.log'
 with (root/log).open('w') as out:r=subprocess.run(command,env=m['environment'](p),stdout=out,stderr=subprocess.STDOUT)
 text=(root/log).read_text();print(name,r.returncode,text[-2500:],flush=True);rows.append(dict(name=name,image=path,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),native_dlopen_verified=r.returncode==0 and 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in text))
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],stage='artifacts/cryptex-native-stage.json',stage_sha256=digest('artifacts/cryptex-native-stage.json'),checks=rows,all_selected_images_load=all(r['native_dlopen_verified'] for r in rows),trust_protocol_verified=False,cryptex_mounting_verified=False)
(root/('artifacts/'+prefix+'-load.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['all_selected_images_load'] else 1)
