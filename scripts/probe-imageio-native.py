#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['load','global','properties'],nargs='?',default='load');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-c','fixtures/hello/imageio-native.m','-o','artifacts/imageio-native.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem','artifacts/imageio-native.o','-o','artifacts/imageio-native'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/imageio-native-profile.py'));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/imageio-native',args.mode];r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/imageio-native-'+args.mode+'.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='');digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/imageio-native.m'),'binary_sha256':digest('artifacts/imageio-native'),'runtime_execution_verified':r.returncode==0,'source_global_properties_verified':args.mode=='global' and r.returncode==0,'image_parsing_and_metadata_verified':args.mode=='properties' and r.returncode==0}
(root/('artifacts/imageio-native-'+args.mode+'-probe.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
