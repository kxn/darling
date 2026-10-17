#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/pid-generation-source-profile.py'));p=m['profile'](False)
build=root/'runtime/pid-generation-kernel-source'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/process-generation-source.c';obj=build/'test-generation.o';binary=build/'test-generation'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];log='logs/process-generation-source-test.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-5000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
success=r.returncode==0 and 'PROCESS_GENERATION_LIBPROC_AUDIT_FORK_EXEC_FAILED_EXEC_STALE_TOKEN_AND_SIZE_OK' in text
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'source':source,'source_sha256':digest(source),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'log':log,'log_sha256':digest(log),'exit_status':r.returncode,'libproc_and_audit_fork_exec_generation_verified':success,'executable_UUID_implemented':False,'full_xcode_build_ready':False}
(root/'artifacts/process-generation-source-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if success else 1)
