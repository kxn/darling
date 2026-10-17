#!/usr/bin/env python3
"""Exercise real endpoint check-in/replies in one task, exposing double moves."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/diskmanagement-nserror-runtime-profile.py' if args.baseline else 'scripts/xpc-sent-message-runtime-profile.py')));p=m['profile'](False)
folder=root/'runtime/xpc-loopback-sent-test';folder.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source=root/'fixtures/hello/xpc-loopback-sent.c';obj=folder/'test.o';binary=folder/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-c',str(source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(root/'runtime/rootfs/usr/libexec/darling'),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];stem='xpc-loopback-sent-'+('baseline' if args.baseline else 'fixed');log=root/('logs/'+stem+'.log')
with log.open('w') as stream:result=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=log.read_text();print(result.returncode,text[-4000:],flush=True);marker='XPC_REAL_16_LOOPBACK_CHECKINS_256_REPLY_PAYLOADS_AND_CANCELLATION_OK'
assert 'XPC_REAL_LOOPBACK_CHECKIN_BEGIN' in text
if args.baseline:assert result.returncode!=0 and marker not in text
else:assert result.returncode==0 and marker in text
digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),baseline=args.baseline,exit_status=result.returncode,source_runtime=p['source_runtime'],source=str(source.relative_to(root)),source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=str(log.relative_to(root)),log_sha256=digest(log),command=command,expected_result_verified=True)
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n')
