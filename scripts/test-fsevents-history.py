#!/usr/bin/env python3
"""Exercise real historical completion, recursive mutations and existing flush contracts."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess,re
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
module=runpy.run_path(str(root/'scripts/fsevents-history-profile.py'));p=module['profile'](baseline=args.baseline)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/fsevents-history-tests';build.mkdir(exist_ok=True)
digest=lambda name:hashlib.sha256((root/name).read_bytes()).hexdigest()
checks=[]
for name,source,marker in [('history','fixtures/hello/fsevents-history.m','FSEVENTS_RECURSIVE_HISTORY_CHECKS_OK'),('flush','fixtures/hello/fsevents-flush.m','SOURCE_FSEVENTS_FLUSH_ALL_CHECKED_SEMANTICS_OK'),('small-stack','fixtures/hello/fsevents-small-stack.m','SOURCE_FSEVENTS_REAL_START_AND_SYNC_FLUSH_ON_64K_STACK_OK')]:
    if args.baseline and name!='history':continue
    obj=build/(name+'.o');binary=build/name
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-Wno-deprecated-declarations','-DEXPECTED_FSEVENTS_PATH="/runtime/fsevents-history-source/frameworks/"','-c',source,'-o',str(obj)],cwd=root,check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-framework','CoreServices','-lobjc','-lSystem',str(obj),'-o',str(binary)],check=True)
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]+(['baseline'] if args.baseline else [])
    log='logs/fsevents-recursive-'+('baseline-' if args.baseline else '')+name+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=module['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(name,r.returncode,text[-4000:],flush=True)
    verified=r.returncode==0 and marker in text
    if args.baseline:verified=r.returncode==2 and 'BASELINE_FINITE_SINCEWHEN_HAS_NO_HISTORY_COMPLETION' in text
    checks.append(dict(name=name,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),command=command,exit_status=r.returncode,log=log,log_sha256=digest(log),verified=verified,check_counts=[int(v) for v in re.findall(r'checks=(\d+)',text)]))
    if not verified:break
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),baseline=args.baseline,checks=checks,verified=all(c['verified'] for c in checks) and len(checks)==(1 if args.baseline else 3),source_runtime=p['source_runtime'],source_fsevents=p.get('source_recursive_history_fsevents',p['source_fsevents']),persistent_global_ids_implemented=False,durable_history_implemented=False,original_xcodebuild_build_verified=False)
(root/('artifacts/fsevents-recursive-'+('baseline' if args.baseline else 'test')+'.json')).write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['verified'] else 1)
