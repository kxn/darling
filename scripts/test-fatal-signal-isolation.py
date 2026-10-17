#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent;parser=argparse.ArgumentParser();parser.add_argument('--fixed',action='store_true');args=parser.parse_args();label='fixed' if args.fixed else 'baseline'
m=runpy.run_path(str(root/('scripts/fatal-signal-runtime-profile.py' if args.fixed else 'scripts/icu-data-runtime-profile.py')));p=m['profile']();folder=root/'runtime/fatal-signal-tests';folder.mkdir(exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';source='fixtures/hello/fatal-signal-isolation.c';obj=folder/(label+'.o');binary=folder/label
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))];command[3]='80';a=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=a.stdout+a.stderr;log='logs/fatal-signal-isolation-'+label+'.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();verified=a.returncode==0 and 'NATIVE_EIGHT_REAL_FATAL_CHILD_EXITS_PARENT_AND_SIBLING_SURVIVE_WITHOUT_GROUP_SIGNALS_OK' in text
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),command=command,source_runtime=p['source_runtime'],source_fatal_signal=p.get('source_fatal_signal'),log=log,log_sha256=digest(log),exit_status=a.returncode,verified=verified,test_process_group_is_private=True,actual_fatal_child_exits=8,full_xcode_build_ready=False)
(root/('artifacts/fatal-signal-isolation-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(text,flush=True)
assert verified if args.fixed else a.returncode==2 and 'NATIVE_FATAL_SIGNAL_CHILDREN=8' in text
