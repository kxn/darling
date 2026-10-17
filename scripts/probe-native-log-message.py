#!/usr/bin/env python3
"""Exercise the previously staged original formatter without changing libSystem."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--through-system',action='store_true');args=parser.parse_args();stem='native-log-message-system' if args.through_system else 'native-log-message'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c','fixtures/hello/native-log-message.c','-o','artifacts/native-log-message.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-lSystem','artifacts/native-log-message.o','-o','artifacts/native-log-message'],cwd=root,check=True)
m=runpy.run_path(str(root/('scripts/'+('native-log-message' if args.through_system else 'log-enablement')+'-profile.py')));p=m['profile']();c=p['command'][:-2]+['/Volumes/SystemRoot/workspace/artifacts/native-log-message']+(['through-system'] if args.through_system else [])
r=subprocess.run(c,cwd=root,env=m['environment'](p),capture_output=True,text=True);log='logs/'+stem+'.log';(root/log).write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='')
digest=lambda s:hashlib.sha256((root/s).read_bytes()).hexdigest()
provider='runtime/state/prefix/usr/lib/libDarlingMetrics.dylib';reconstruction=json.loads((root/'runtime/rebuilt-native-trace/reconstruction.json').read_text());assert digest(provider)==reconstruction['staged_image_sha256']
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':c,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/native-log-message.c'),'binary_sha256':digest('artifacts/native-log-message'),'provider':provider,'provider_sha256':digest(provider),'reconstruction_sha256':digest('runtime/rebuilt-native-trace/reconstruction.json'),'runtime_execution_verified':r.returncode==0}
(root/('artifacts/'+stem+'-probe.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(r.returncode)
