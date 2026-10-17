#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/crypto-quarantine-runtime-profile.py'));p=m['profile'](False)
build=root/'runtime/crypto-quarantine-runtime';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/quarantine-proc-native.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];log='logs/quarantine-proc-native-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-4000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
success=r.returncode==0 and 'NATIVE_QUARANTINE_PROC_OBJECT_FLAGS_METADATA_CLONE_AND_UNSUPPORTED_POLICY_ERRORS_OK' in text
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'source':source,'source_sha256':digest(source),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'log':log,'log_sha256':digest(log),'exit_status':r.returncode,'native_proc_value_execution_verified':success,'policy_application_verified':False,'full_xcode_build_ready':False}
(root/'artifacts/quarantine-proc-native-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
