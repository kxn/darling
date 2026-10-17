#!/usr/bin/env python3
"""Execute original parameter handling/compiler and expose the stock stub control."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
m=runpy.run_path(str(root/('scripts/coreservices-directories-profile.py' if args.baseline else 'scripts/sandbox-compiler-native-profile.py')));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';build=root/'runtime/sandbox-compiler-native-tests';build.mkdir(exist_ok=True);source='fixtures/hello/sandbox-compiler-native.c';obj=build/'test.o';binary=build/'test'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr
stem='sandbox-compiler-'+('baseline' if args.baseline else 'native')+'-probe';log='logs/'+stem+'.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,exit_status=r.returncode,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),log=log,log_sha256=digest(log),native_sandbox_compiler=p.get('native_sandbox_compiler'),probe_returned='SANDBOX_COMPILER_PROBE_RETURNED' in text,policy_applied=False,baseline=args.baseline)
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(r.returncode,text)
