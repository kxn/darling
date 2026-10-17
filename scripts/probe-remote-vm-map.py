#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--tag',default='baseline');parser.add_argument('--s2c-lifecycle',action='store_true');args=parser.parse_args();assert args.tag.isalnum()
m=runpy.run_path(str(root/('scripts/s2c-lifecycle-runtime-profile.py' if args.s2c_lifecycle else 'scripts/mount-flags-runtime-profile.py')));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';folder=root/'runtime/remote-vm-map';folder.mkdir(exist_ok=True)
source='fixtures/hello/remote-vm-map.c';obj=folder/'native.o';binary=folder/'native'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-g','-fblocks','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];command[3]='80'
log='logs/remote-vm-map-'+args.tag+'.log'
with (root/log).open('w') as stream:result=subprocess.run(command,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),command=command,exit_status=result.returncode,log=log,log_sha256=digest(log),source_runtime=p['source_runtime'],verified='NATIVE_REMOTE_VM_MAP_MULTITHREADED_RECIPIENT_SHARING_OK' in text and result.returncode==0,full_xcode_build_ready=False)
(root/('artifacts/remote-vm-map-'+args.tag+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(text)
