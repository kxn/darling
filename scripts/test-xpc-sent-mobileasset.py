#!/usr/bin/env python3
"""Regress actual Pallas IPC in the complete rebuilt MobileAsset selection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;m=runpy.run_path(str(root/'scripts/xpc-sent-message-runtime-profile.py'));p=m['profile'](False);build=p['source_mobileasset_download_attributes'];folder=root/'runtime/mobileasset-download-attributes/tests';folder.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';rows=[];digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
for name in ['mobileasset-pallas','mobileasset-pallas-operations']:
 source='fixtures/hello/'+name+'.m';obj=folder/(name+'.o');binary=folder/name
 subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c',str(root/source),'-o',str(obj)],check=True)
 subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem',str(obj),'-o',str(binary)],check=True)
 command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),'/Volumes/SystemRoot/workspace/'+build['framework']];log='logs/xpc-sent-mobileasset-'+name+'.log'
 with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
 text=(root/log).read_text();print(name,r.returncode,text[-2500:],flush=True);rows.append(dict(source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),command=command,log=log,log_sha256=digest(log),exit_status=r.returncode))
 assert r.returncode==0
 assert ('MOBILEASSET_PALLAS_REAL_EIGHT_THREADS_64_INDEPENDENT_XPC_REQUEST_REPLY_CYCLES_OK' if name=='mobileasset-pallas' else 'PALLAS_REAL_XPC_PEER_TEARDOWN_ONE_RETRY_SUCCESS_AND_TWO_ATTEMPT_LIMIT_OK') in text
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),build='artifacts/mobileasset-download-attributes-build.json',build_sha256=digest('artifacts/mobileasset-download-attributes-build.json'),source_runtime=p['source_runtime'],checks=rows,actual_Pallas_client_transport_regression_verified=True,actual_Apple_download_daemon_verified=False,asset_download_implemented=False)
(root/'artifacts/xpc-sent-mobileasset-test.json').write_text(json.dumps(record,indent=2)+'\n')
