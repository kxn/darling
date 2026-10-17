#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--tag',default='baseline');parser.add_argument('--xpc-activation',action='store_true');args=parser.parse_args();assert args.tag.isalnum()
m=runpy.run_path(str(root/('scripts/xpc-activation-runtime-profile.py' if args.xpc_activation else 'scripts/s2c-lifecycle-runtime-profile.py')));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';folder=root/'runtime/xpc-missing-service-tests';folder.mkdir(exist_ok=True)
source='fixtures/hello/xpc-missing-service.c';obj=folder/'native.o';binary=folder/'native'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-fblocks','-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];command[3]='35'
a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/xpc-missing-service-'+args.tag+'.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
d=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),command=command,exit_status=a.returncode,log=log,log_sha256=digest(log),source_runtime=p['source_runtime'],verified=a.returncode==0 and 'XPC_MISSING_RESULT verified=1 events=2 async=1 sync=1 timeouts=0' in text,full_xcode_build_ready=False)
(root/('artifacts/xpc-missing-service-'+args.tag+'.json')).write_text(json.dumps(d,indent=2)+'\n');print(text)
