#!/usr/bin/env python3
"""Reproduce genuine Security translocation/CFBundle checks for CoreTypes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--wait',action='store_true');args=parser.parse_args()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
commands=[['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c','fixtures/hello/coretypes-translocation.m','-o','artifacts/coretypes-translocation.o'],['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-F',str(guest/'System/Library/Frameworks'),'-framework','Foundation','-framework','Security','-framework','CoreFoundation','-lobjc','-lSystem','artifacts/coretypes-translocation.o','-o','artifacts/coretypes-translocation']]
for c in commands:subprocess.run(c,cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/metadata-kernel-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/coretypes-translocation']+(['--wait'] if args.wait else [])
if args.wait:c[3]='180'
c.insert(c.index('/usr/bin/env')+1,'DARLING_OS_LOG_STDERR=1');log='logs/coretypes-translocation'+('-debug' if args.wait else '')+'.log'
with (root/log).open('w') as f:
 process=subprocess.Popen(c,cwd=root,env=m['environment'](p),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 for line in process.stdout:f.write(line);f.flush();print(line,end='',flush=True)
 status=process.wait()
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=c,source_runtime=p['source_runtime'],exit_status=status,log=log,log_sha256=digest(log),source_sha256=digest('fixtures/hello/coretypes-translocation.m'),binary_sha256=digest('artifacts/coretypes-translocation'),runtime_execution_verified=status==0)
(root/('artifacts/coretypes-translocation'+('-debug' if args.wait else '')+'.json')).write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(status)
