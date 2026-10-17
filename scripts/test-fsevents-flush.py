#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--debug-flush',action='store_true');parser.add_argument('--cf-timeout',action='store_true');parser.add_argument('--cf-timeout-signaled',action='store_true');parser.add_argument('--cf-timeout-thread',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-Wno-deprecated-declarations','-c','fixtures/hello/fsevents-flush.m','-o','artifacts/fsevents-flush.o'],cwd=root,check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-framework','CoreServices','-lobjc','-lSystem','artifacts/fsevents-flush.o','-o','artifacts/fsevents-flush'],cwd=root,check=True)
m=runpy.run_path(str(root/'scripts/fsevents-flush-profile.py'));p=m['profile']();command=p['command'][:-2]+(['DARLING_FSEVENTS_TRACE_FLUSH=1'] if args.debug_flush else [])+['/Volumes/SystemRoot/workspace/artifacts/fsevents-flush',*(['cf-timeout-thread'] if args.cf_timeout_thread else ['cf-timeout-signaled'] if args.cf_timeout_signaled else ['cf-timeout'] if args.cf_timeout else [])];stem='fsevents-native-cf-timeout-thread' if args.cf_timeout_thread else 'fsevents-native-cf-timeout-signaled' if args.cf_timeout_signaled else 'fsevents-native-cf-timeout' if args.cf_timeout else 'fsevents-flush-debug-test' if args.debug_flush else 'fsevents-flush-test';log='logs/'+stem+'.log'
if args.cf_timeout or args.cf_timeout_signaled or args.cf_timeout_thread:command[3]='10'
with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
output=(root/log).read_text();print(output,end='');digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
verified=r.returncode==0 and ('CF_RUNLOOP_NATIVE_TIMEOUT_END' in output if args.cf_timeout or args.cf_timeout_signaled or args.cf_timeout_thread else 'SOURCE_FSEVENTS_FLUSH_ALL_CHECKED_SEMANTICS_OK' in output)
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'command':command,'exit_status':r.returncode,'log':log,'log_sha256':digest(log),'source_sha256':digest('fixtures/hello/fsevents-flush.m'),'binary_sha256':digest('artifacts/fsevents-flush'),'runtime_execution_verified':verified,'persistent_or_global_ids_verified':False,'recursive_watches_verified':False}
(root/('artifacts/'+stem+'.json')).write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if verified else r.returncode or 1)
