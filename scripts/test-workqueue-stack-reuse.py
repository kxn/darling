#!/usr/bin/env python3
"""Exercise real pthread workqueue reuse and its idle termination path."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/cryptex-native-profile.py' if args.baseline else 'scripts/workqueue-stack-runtime-profile.py')));p=m['profile'](False)
folder=root/'runtime/workqueue-stack-test';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
source=root/'fixtures/hello/workqueue-stack-reuse.c';obj=folder/'test.o';binary=folder/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(root/'runtime/rootfs/usr/libexec/darling'),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
stem='workqueue-stack-'+('baseline' if args.baseline else 'fixed');log=root/('logs/'+stem+'.log')
with log.open('w') as stream:result=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=log.read_text();print(result.returncode,text,flush=True)
expected=42 if args.baseline else 0
assert result.returncode==expected
assert ('WORKQUEUE_REUSE_STACK_GROWTH' if args.baseline else 'WORKQUEUE_REAL_IDLE_TIMEOUT_PTHREAD_DESTRUCTOR_OK') in text
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),baseline=args.baseline,exit_status=result.returncode,source_runtime=p['source_runtime'],source=str(source.relative_to(root)),source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=str(log.relative_to(root)),log_sha256=digest(log),command=command,expected_result_verified=True)
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n')
