#!/usr/bin/env python3
"""Verify real event delivery on a small stack and the existing flush regression."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/log-pack-profile.py'));p=m['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/fsevents-heap-source/tests';build.mkdir(exist_ok=True)
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest();checks=[]
for name,source,marker in [('small-stack','fixtures/hello/fsevents-small-stack.m','SOURCE_FSEVENTS_REAL_START_AND_SYNC_FLUSH_ON_64K_STACK_OK'),('flush','fixtures/hello/fsevents-flush.m','SOURCE_FSEVENTS_FLUSH_ALL_CHECKED_SEMANTICS_OK')]:
    obj=build/(name+'.o');binary=build/name
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-DEXPECTED_FSEVENTS_PATH="/runtime/fsevents-heap-source/frameworks/"','-Wno-deprecated-declarations','-c',source,'-o',str(obj)],cwd=root,check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-framework','CoreServices','-lobjc','-lSystem',str(obj),'-o',str(binary)],cwd=root,check=True)
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
    log='logs/fsevents-heap-'+name+'.log'
    with (root/log).open('w') as stream:result=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(name,result.returncode,text[-4000:],flush=True)
    checks.append(dict(name=name,source=source,source_sha256=digest(source),binary=str(binary.relative_to(root)),binary_sha256=digest(str(binary.relative_to(root))),command=command,exit_status=result.returncode,log=log,log_sha256=digest(log),verified=result.returncode==0 and marker in text))
    if not checks[-1]['verified']:break
record={**p,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'runtime_execution_verified':len(checks)==2 and all(c['verified'] for c in checks),'full_xcode_build_ready':False,'recursive_or_persistent_events_verified':False}
(root/'artifacts/fsevents-heap-test.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['runtime_execution_verified'] else 1)
