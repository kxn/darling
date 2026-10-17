#!/usr/bin/env python3
"""Exercise real Apple CALayer and bitmap rendering before selecting a bridge."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-support',action='store_true');args=parser.parse_args()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling'
commands=[['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-fblocks','-c','fixtures/hello/native-calayer-render.m','-o','artifacts/native-calayer-render.o'],['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-F',str(guest/'System/Library/Frameworks'),'-framework','Foundation','-framework','CoreGraphics','-framework','QuartzCore','-lobjc','-lSystem','artifacts/native-calayer-render.o','-o','artifacts/native-calayer-render']]
for c in commands:subprocess.run(c,cwd=root,check=True)
k=runpy.run_path(str(root/'scripts/mount-path-kernel-profile.py'))['profile']();m=runpy.run_path(str(root/'scripts/container-manager-profile.py'));p=m['profile'](kernel_profile=k)
if args.source_support:
 m=runpy.run_path(str(root/'scripts/native-layer-profile.py'));p=m['profile']()
c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/native-calayer-render'];label='native-calayer-render'+('-source-support' if args.source_support else '');log='logs/'+label+'-probe.log'
with (root/log).open('w') as f:
 proc=subprocess.Popen(c,cwd=root,env=m['environment'](p),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 for line in proc.stdout:f.write(line);f.flush();print(line,end='',flush=True)
 status=proc.wait()
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':status,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/native-calayer-render.m'),'binary_sha256':digest('artifacts/native-calayer-render'),'native_bitmap_layer_render_verified':status==0,'full_xcode_build_ready':False}
(root/('artifacts/'+label+'-probe.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(status)
