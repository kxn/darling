#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--source-fsevents',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-c','fixtures/hello/fsevents-baseline.m','-o','artifacts/fsevents-baseline.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-framework','CoreServices','-lobjc','-lSystem','artifacts/fsevents-baseline.o','-o','artifacts/fsevents-baseline'],cwd=root,check=True)
m=runpy.run_path(str(root/('scripts/fsevents-source-profile.py' if args.source_fsevents else 'scripts/combine-native-profile.py')));p=m['profile']();command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/fsevents-baseline',*(['source'] if args.source_fsevents else [])];r=subprocess.run(command,cwd=root,env=m['environment'](p),capture_output=True,text=True);stem='fsevents-source-burst' if args.source_fsevents else 'fsevents-baseline';log='logs/'+stem+'.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='');digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/fsevents-baseline.m'),'binary_sha256':digest('artifacts/fsevents-baseline'),'complete_delivery_verified':r.returncode==0,'source_implementation_changed':args.source_fsevents}
(root/('artifacts/'+stem+'-probe.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
