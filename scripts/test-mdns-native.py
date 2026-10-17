#!/usr/bin/env python3
"""Execute actual restored mdns TLV code with independent wire-format checks."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/mdns-native-profile.py'));p=m['profile'](include_system_resources=False)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/mdns-native/tests';build.mkdir(exist_ok=True)
obj=build/'mdns.o';binary=build/'mdns';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c','fixtures/hello/mdns-native.c','-o',str(obj)],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lobjc','-lSystem',str(obj),'-o',str(binary)],cwd=root,check=True)
checks=[]
for mode in ['lazy','eager','remote']:
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),*([mode] if mode!='lazy' else [])]
    log='logs/mdns-native-'+mode+'.log'
    with (root/log).open('w') as stream:result=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(mode,result.returncode,text[-3500:],flush=True)
    marker='ORIGINAL_REMOTE_XPC_AND_RSD_REAL_CLASS_REGISTRATION_OK' if mode=='remote' else 'ORIGINAL_MDNS_TLV16_BYTES_BOUNDS_AND_ERRORS_OK'
    checks.append(dict(mode=mode,command=command,exit_status=result.returncode,log=log,log_sha256=digest(log),verified=result.returncode==0 and marker in text))
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'source':'fixtures/hello/mdns-native.c','source_sha256':digest('fixtures/hello/mdns-native.c'),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'selected_TLV_execution_verified':checks[0]['verified'],'eager_library_bind_verified':checks[1]['verified'],'remote_class_registration_verified':checks[2]['verified'],'network_or_discovery_execution_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/mdns-native-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if all(c['verified'] for c in checks) else 1)
