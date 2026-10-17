#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['load','version','architecture','device']);parser.add_argument('--source-dyld',action='store_true');args=parser.parse_args()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-c','fixtures/hello/mobilegestalt-native.m','-o','artifacts/mobilegestalt-native.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-lobjc','-lSystem','artifacts/mobilegestalt-native.o','-o','artifacts/mobilegestalt-native'],cwd=root,check=True)
m=runpy.run_path(str(root/('scripts/runnable-archs-profile.py' if args.source_dyld else 'scripts/mobilegestalt-native-profile.py')));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/mobilegestalt-native',args.mode]
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);stem='mobilegestalt-native-'+('source-dyld-' if args.source_dyld else '')+args.mode;log='logs/'+stem+'.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='')
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/mobilegestalt-native.m'),'binary_sha256':digest('artifacts/mobilegestalt-native'),'runtime_execution_verified':r.returncode==0,'all_device_metadata_verified':False}
(root/('artifacts/'+stem+'-probe.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
