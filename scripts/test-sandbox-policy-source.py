#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--pid-generation',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/pid-generation-source-profile.py' if args.pid_generation else 'scripts/sandbox-policy-source-profile.py')));p=m['profile'](False)
build=root/'runtime/sandbox-policy-source';sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source='fixtures/hello/sandbox-policy-source.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
stem='sandbox-policy-'+('generation-' if args.pid_generation else '')+'source-test'
native='runtime/foundation-native-library-stage/libDarlingNativeSandbox.dylib';command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),'/Volumes/SystemRoot/workspace/'+native];log='logs/'+stem+'.log'
with (root/log).open('w') as stream:r=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-5000:],flush=True);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'source':source,'source_sha256':digest(source),'binary':str(binary.relative_to(root)),'binary_sha256':digest(str(binary.relative_to(root))),'log':log,'log_sha256':digest(log),'exit_status':r.returncode,'registered_unconfined_query_execution_verified':r.returncode==0 and 'SANDBOX_REGISTERED_UNCONFINED_STATE_REAL_AUDIT_LIFETIME_ERRORS_AND_UNSUPPORTED_PROFILES_OK' in text,'profile_application_verified':False,'approval_grants_verified':False,'full_xcode_build_ready':False}
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['registered_unconfined_query_execution_verified'] else 1)
