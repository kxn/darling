#!/usr/bin/env python3
"""Use genuine Mach-O clients against the shared server event source."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--vchroot-links',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
suffix='-vchroot-links' if args.vchroot_links else ''
module=runpy.run_path(str(root/('scripts/vchroot-links-runtime-profile.py' if args.vchroot_links else 'scripts/global-fsevents-runtime-profile.py')));p=module['profile']()
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
build=root/'runtime/global-fsevents-tests';build.mkdir(exist_ok=True)
digest=lambda path:hashlib.sha256((root/path).read_bytes()).hexdigest();cases=[]
for name,source,marker in [('history','fixtures/hello/fsevents-global-history.m','FSEVENTS_RECURSIVE_HISTORY_CHECKS_OK'),('flush','fixtures/hello/fsevents-global-flush.m','SOURCE_FSEVENTS_FLUSH_ALL_CHECKED_SEMANTICS_OK'),('small-stack','fixtures/hello/fsevents-small-stack.m','SOURCE_FSEVENTS_REAL_START_AND_SYNC_FLUSH_ON_64K_STACK_OK')]:
    obj=build/(name+'.o');binary=build/name
    source_path=root/source
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-fblocks','-O2','-Wno-deprecated-declarations','-DEXPECTED_FSEVENTS_PATH="/runtime/global-fsevents-source/frameworks/"','-c',str(source_path),'-o',str(obj)],check=True)
    subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-framework','Foundation','-framework','CoreFoundation','-framework','CoreServices','-lobjc','-lSystem',str(obj),'-o',str(binary)],check=True)
    command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root))]
    command[3]='120'
    log='logs/global-fsevents-native-'+name+suffix+'.log'
    with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=module['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
    text=(root/log).read_text();print(name,r.returncode,text[-3500:],flush=True)
    passed=r.returncode==0 and marker in text
    cases.append(dict(name=name,source=str(source_path.relative_to(root)),source_sha256=digest(source_path),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),command=command,log=log,log_sha256=digest(log),exit_status=r.returncode,verified=passed,checks=[int(value) for value in re.findall(r'checks=(\d+)',text)]))
    if not passed:break
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),cases=cases,verified=len(cases)==3 and all(c['verified'] for c in cases),source_runtime=p['source_runtime'],source_global_fsevents=p['source_global_fsevents'],source_fsevents=p['source_global_fsevents_framework'],full_xcode_build_ready=False)
(root/('artifacts/global-fsevents-native-test'+suffix+'.json')).write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['verified'] else 1)
