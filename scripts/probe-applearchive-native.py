#!/usr/bin/env python3
"""Observe real loading of complete native archive images in the selected root."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/applearchive-native-profile.py'));p=m['profile'](False);rows=[]
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
for name,path in [('C','/usr/lib/libAppleArchive.dylib'),('Swift','/usr/lib/swift/libswiftAppleArchive.dylib')]:
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/runtime/device-identity-native/load',path];log='logs/applearchive-native-'+name+'-load.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(name,r.returncode,text[-2500:],flush=True)
    rows.append(dict(image=path,command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),native_dlopen_verified=r.returncode==0 and 'NATIVE_FOUNDATION_DLOPEN_COMPLETED' in text))
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source_runtime=p['source_runtime'],stage='artifacts/applearchive-native-stage.json',stage_sha256=digest('artifacts/applearchive-native-stage.json'),checks=rows,all_selected_images_load=all(row['native_dlopen_verified'] for row in rows),crypto_stream_execution_verified=False)
(root/'artifacts/applearchive-native-load.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['all_selected_images_load'] else 1)
