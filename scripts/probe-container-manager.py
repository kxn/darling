#!/usr/bin/env python3
"""Exercise the original CM APIs or original clients in the CM/metadata profile."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mount-path-kernel',action='store_true');parser.add_argument('mode',choices=['lifecycle','version','showsdks','foundation','translocation']);args=parser.parse_args()
m=runpy.run_path(str(root/'scripts/container-manager-profile.py'));kernel=runpy.run_path(str(root/'scripts/mount-path-kernel-profile.py'))['profile']() if args.mount_path_kernel else None;p=m['profile'](kernel_profile=kernel);prefix='/Volumes/SystemRoot/workspace/'
if args.mode=='lifecycle':
 sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
 for c in [['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c','fixtures/hello/container-manager.c','-o','artifacts/container-manager.o'],['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-lSystem','artifacts/container-manager.o','-o','artifacts/container-manager']]:subprocess.run(c,cwd=root,check=True)
 c=p['command'][:-2]+[prefix+'artifacts/container-manager',prefix+p['container_manager']['library'],prefix+p['container_manager']['provider'],prefix+p['container_manager']['helper']]
elif args.mode in ['version','showsdks']:c=p['command'][:-1]+['-'+args.mode]
else:c=p['command'][:-2]+[prefix+('artifacts/coretypes-resource-values' if args.mode=='foundation' else 'artifacts/coretypes-translocation')]
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True)
label=('mount-path-' if args.mount_path_kernel else '')+'container-manager-';log='logs/'+label+args.mode+'-probe.log';(root/log).write_text(r.stdout+r.stderr);digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'diagnostic':r.stdout+r.stderr,'runtime_execution_verified':r.returncode==0,'full_xcode_build_ready':False,'signing_ready':False}
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
assert digest(original)==digest('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild')
record['original_xcodebuild_sha256']=digest(original)
if args.mode=='foundation':record.update(source_sha256=digest('fixtures/hello/coretypes-resource-values.m'),binary_sha256=digest('artifacts/coretypes-resource-values'))
if args.mode=='translocation':record.update(source_sha256=digest('fixtures/hello/coretypes-translocation.m'),binary_sha256=digest('artifacts/coretypes-translocation'))
if args.mode=='lifecycle':record.update(source_sha256=digest('fixtures/hello/container-manager.c'),binary_sha256=digest('artifacts/container-manager'),positive_container_service_query_verified=False)
(root/('artifacts/'+label+args.mode+'-probe.json')).write_text(json.dumps(record,indent=2)+'\n');print(r.stdout+r.stderr,end='');raise SystemExit(r.returncode)
